"""Performance optimization utilities for MP3 to TXT extraction."""

import os
import sys
import logging
import threading
import multiprocessing
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import time

import torch
import whisper


class DeviceType(Enum):
    """Available computation device types."""
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"  # Apple Metal Performance Shaders
    AUTO = "auto"


@dataclass
class DeviceInfo:
    """Information about available compute devices."""
    device_type: DeviceType
    device_id: Optional[int] = None
    memory_gb: Optional[float] = None
    compute_capability: Optional[str] = None
    is_available: bool = False


class PerformanceOptimizer:
    """Optimizes performance for MP3 to TXT extraction using multi-core and GPU acceleration."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._device_cache = None
        self._optimal_workers = None

    def detect_available_devices(self) -> List[DeviceInfo]:
        """Detect all available computation devices with comprehensive fallbacks."""
        if self._device_cache is not None:
            return self._device_cache

        devices = []
        import platform

        # Always include CPU (universal fallback)
        cpu_memory = self._get_cpu_memory_gb()
        cpu_info = DeviceInfo(
            device_type=DeviceType.CPU,
            is_available=True,
            memory_gb=cpu_memory
        )
        devices.append(cpu_info)
        self.logger.info(f"CPU detected: {cpu_memory:.1f}GB memory")

        # Platform-specific detection
        system = platform.system()
        machine = platform.machine()

        self.logger.info(f"Platform: {system} {machine}")

        # Apple Silicon detection
        if system == "Darwin" and machine in ["arm64", "arm64e"]:
            self._detect_apple_silicon_devices(devices)

        # CUDA detection (Windows/Linux)
        elif system in ["Windows", "Linux"] or (system == "Darwin" and machine not in ["arm64", "arm64e"]):
            self._detect_cuda_devices(devices)

        # Generic MPS detection (for non-Apple Silicon systems that might support it)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            mps_memory = cpu_memory  # Use CPU memory as fallback
            mps_info = DeviceInfo(
                device_type=DeviceType.MPS,
                memory_gb=mps_memory,
                compute_capability=f"MPS on {system}",
                is_available=True
            )
            devices.append(mps_info)
            self.logger.info(f"MPS detected: {mps_memory:.1f}GB memory")

        self._device_cache = devices
        self.logger.info(f"Total devices detected: {len(devices)} - {[d.device_type.value for d in devices]}")
        return devices

    def _detect_apple_silicon_devices(self, devices: List[DeviceInfo]):
        """Detect Apple Silicon specific devices."""
        try:
            import platform
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                mps_memory = self._get_apple_silicon_memory_gb()

                mps_info = DeviceInfo(
                    device_type=DeviceType.MPS,
                    memory_gb=mps_memory,
                    compute_capability="Apple Silicon " + platform.machine(),
                    is_available=True
                )
                devices.append(mps_info)
                self.logger.info(f"Apple Silicon MPS detected: {mps_memory:.1f}GB unified memory")
            else:
                self.logger.info("Apple Silicon detected but MPS not available")
        except Exception as e:
            self.logger.warning(f"Failed to detect Apple Silicon devices: {e}")

    def _detect_cuda_devices(self, devices: List[DeviceInfo]):
        """Detect CUDA devices for Windows/Linux systems."""
        try:
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                self.logger.info(f"CUDA detected: {gpu_count} GPU(s)")

                for i in range(gpu_count):
                    try:
                        gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                        compute_cap = str(torch.cuda.get_device_properties(i).major) + "." + str(torch.cuda.get_device_properties(i).minor)

                        gpu_info = DeviceInfo(
                            device_type=DeviceType.CUDA,
                            device_id=i,
                            memory_gb=gpu_memory,
                            compute_capability=compute_cap,
                            is_available=True
                        )
                        devices.append(gpu_info)
                        self.logger.info(f"CUDA GPU {i}: {gpu_memory:.1f}GB, compute {compute_cap}")
                    except Exception as e:
                        self.logger.warning(f"Failed to get CUDA GPU {i} properties: {e}")
            else:
                self.logger.info("CUDA not available")
        except Exception as e:
            self.logger.warning(f"Failed to detect CUDA devices: {e}")

    def _get_cpu_memory_gb(self) -> float:
        """Get total CPU memory in GB with cross-platform fallbacks."""
        try:
            import psutil
            memory = psutil.virtual_memory().total / (1024**3)
            self.logger.debug(f"Memory from psutil: {memory:.1f}GB")
            return memory
        except ImportError:
            self.logger.debug("psutil not available, using platform-specific fallbacks")
            import platform
            system = platform.system()

            if system == "Darwin":
                return self._get_apple_silicon_memory_gb()
            elif system == "Windows":
                return self._get_windows_memory_gb()
            elif system == "Linux":
                return self._get_linux_memory_gb()
            else:
                # Conservative fallback for unknown systems
                self.logger.warning(f"Unknown system {system}, using conservative memory estimate")
                return 8.0

    def _get_windows_memory_gb(self) -> float:
        """Get Windows memory using wmic or ctypes."""
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip() and line.strip().isdigit():
                        memory_bytes = int(line.strip())
                        memory_gb = memory_bytes / (1024**3)
                        self.logger.debug(f"Windows memory from wmic: {memory_gb:.1f}GB")
                        return memory_gb
        except Exception as e:
            self.logger.debug(f"wmic failed: {e}")

        # Fallback to ctypes
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            c_ulonglong = ctypes.c_ulonglong

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", c_ulonglong),
                    ("ullAvailPhys", c_ulonglong),
                    ("ullTotalPageFile", c_ulonglong),
                    ("ullAvailPageFile", c_ulonglong),
                    ("ullTotalVirtual", c_ulonglong),
                    ("ullAvailVirtual", c_ulonglong),
                    ("ullAvailExtendedVirtual", c_ulonglong),
                ]

            memoryStatus = MEMORYSTATUSEX()
            memoryStatus.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(memoryStatus))

            memory_gb = memoryStatus.ullTotalPhys / (1024**3)
            self.logger.debug(f"Windows memory from ctypes: {memory_gb:.1f}GB")
            return memory_gb
        except Exception as e:
            self.logger.debug(f"ctypes fallback failed: {e}")

        # Conservative fallback
        return 8.0

    def _get_linux_memory_gb(self) -> float:
        """Get Linux memory from /proc/meminfo."""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        # Parse line like "MemTotal:       16777216 kB"
                        parts = line.split()
                        if len(parts) >= 3:
                            memory_kb = int(parts[1])
                            memory_gb = memory_kb / (1024**2)
                            self.logger.debug(f"Linux memory from /proc/meminfo: {memory_gb:.1f}GB")
                            return memory_gb
        except Exception as e:
            self.logger.debug(f"Failed to read /proc/meminfo: {e}")

        # Fallback to free command
        try:
            import subprocess
            result = subprocess.run(
                ["free", "-h"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Mem:'):
                        # Parse line like "Mem:           16G       2.0G       14G       0B       2.0G       14G"
                        parts = line.split()
                        if len(parts) >= 2:
                            memory_str = parts[1]
                            if memory_str.endswith('G'):
                                memory_gb = float(memory_str[:-1])
                            elif memory_str.endswith('M'):
                                memory_gb = float(memory_str[:-1]) / 1024
                            elif memory_str.endswith('K'):
                                memory_gb = float(memory_str[:-1]) / (1024**2)
                            else:
                                memory_gb = float(memory_str) / (1024**3)
                            self.logger.debug(f"Linux memory from free: {memory_gb:.1f}GB")
                            return memory_gb
        except Exception as e:
            self.logger.debug(f"free command failed: {e}")

        # Conservative fallback
        return 8.0

    def _get_apple_silicon_memory_gb(self) -> float:
        """Get Apple Silicon unified memory in GB."""
        try:
            import platform
            if platform.system() != "Darwin":
                return 0.0

            # Try to get memory from system_profiler (macOS)
            import subprocess
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType", "-json"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                hardware = data.get("SPHardwareDataType", [])
                if hardware and len(hardware) > 0:
                    hw_info = hardware[0]
                    memory_str = hw_info.get("physical_memory", "")
                    if memory_str:
                        # Parse memory string like "16 GB" or "32 GB"
                        if "GB" in memory_str:
                            return float(memory_str.replace("GB", "").strip())
                        elif "MB" in memory_str:
                            return float(memory_str.replace("MB", "").strip()) / 1024

            # Fallback: try sysctl
            try:
                result = subprocess.run(
                    ["sysctl", "hw.memsize"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Parse output like "hw.memsize: 17179869184"
                    mem_bytes = int(result.stdout.split(":")[1].strip())
                    return mem_bytes / (1024**3)
            except:
                pass

        except Exception as e:
            self.logger.debug(f"Could not detect Apple Silicon memory: {e}")

        # Conservative fallback for Apple Silicon
        return 16.0

    def get_optimal_device(self, model_size: str = "medium") -> DeviceInfo:
        """Select the optimal device for the given model size."""
        devices = self.detect_available_devices()

        # Model size to memory requirements (approximate)
        model_memory_requirements = {
            "tiny": 0.1,    # ~100MB
            "base": 0.2,    # ~200MB
            "small": 0.5,   # ~500MB
            "medium": 1.5,  # ~1.5GB
            "large": 3.0,   # ~3GB
            "large-v2": 3.0,
            "large-v3": 3.0,
        }

        required_memory = model_memory_requirements.get(model_size, 1.5)

        import platform
        is_apple_silicon = platform.system() == "Darwin" and platform.machine() in ["arm64", "arm64e"]

        # For Apple Silicon, prioritize MPS
        if is_apple_silicon:
            for device in devices:
                if device.device_type == DeviceType.MPS and device.memory_gb and device.memory_gb > required_memory:
                    self.logger.info(f"Selected MPS device (Apple Silicon) with {device.memory_gb:.1f}GB unified memory")
                    return device

        # For other systems, prioritize CUDA then MPS
        for device in devices:
            if device.device_type == DeviceType.CUDA and device.memory_gb and device.memory_gb > required_memory:
                self.logger.info(f"Selected CUDA device {device.device_id} with {device.memory_gb:.1f}GB memory")
                return device
            elif device.device_type == DeviceType.MPS and device.memory_gb and device.memory_gb > required_memory:
                self.logger.info(f"Selected MPS device with {device.memory_gb:.1f}GB memory")
                return device


    def get_optimal_worker_count(self, device_type: DeviceType, model_size: str = "medium") -> int:
        """Calculate optimal number of worker threads/processes with cross-platform optimization."""
        if self._optimal_workers is not None:
            return self._optimal_workers

        cpu_count = os.cpu_count() or 1
        import platform
        system = platform.system()

        self.logger.debug(f"Calculating workers for {device_type.value} on {system} with {cpu_count} CPU cores")

        if device_type == DeviceType.CPU:
            # CPU-based processing - conservative to avoid memory pressure
            if system == "Darwin":
                # macOS - moderate concurrency
                self._optimal_workers = min(4, cpu_count)
            elif system == "Windows":
                # Windows - can handle more workers due to better memory management
                self._optimal_workers = min(6, cpu_count)
            elif system == "Linux":
                # Linux - optimal for concurrent processing
                self._optimal_workers = min(8, cpu_count)
            else:
                # Unknown system - conservative
                self._optimal_workers = min(4, cpu_count)

        elif device_type == DeviceType.CUDA:
            # CUDA GPU - limit workers to avoid GPU memory conflicts
            gpu_count = torch.cuda.device_count() if torch.cuda.is_available() else 1
            # Allow 1-2 workers per GPU, but limit total
            self._optimal_workers = min(gpu_count * 2, 4, cpu_count)

        elif device_type == DeviceType.MPS:
            # MPS processing - optimize based on platform
            if system == "Darwin" and platform.machine() in ["arm64", "arm64e"]:
                # Apple Silicon - optimize based on chip type
                self._optimal_workers = self._get_apple_silicon_workers()
            else:
                # Non-Apple Silicon MPS - moderate concurrency
                self._optimal_workers = min(4, cpu_count)
        else:
            # Unknown device type - use all cores
            self._optimal_workers = cpu_count

        # Ensure at least 1 worker
        self._optimal_workers = max(1, self._optimal_workers)

        self.logger.info(f"Optimal worker count for {device_type.value} on {system}: {self._optimal_workers}")
        return self._optimal_workers

    def _get_apple_silicon_workers(self) -> int:
        """Get optimal worker count for Apple Silicon based on chip type."""
        cpu_count = os.cpu_count() or 1

        try:
            # Try to detect performance cores
            import subprocess
            result = subprocess.run(
                ["sysctl", "hw.perflevel0.physicalcpu"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                perf_cores = int(result.stdout.split(":")[1].strip())
                self.logger.debug(f"Apple Silicon performance cores: {perf_cores}")

                # Optimize based on performance core count
                if perf_cores >= 12:  # M4 Pro/Max, M2 Ultra, etc.
                    return min(8, cpu_count)
                elif perf_cores >= 8:  # M1/M2/M3 Pro, M4, etc.
                    return min(6, cpu_count)
                elif perf_cores >= 4:  # M1/M2/M3 base, etc.
                    return min(4, cpu_count)
                else:
                    return min(3, cpu_count)
            else:
                # Fallback based on total cores
                self.logger.debug("Could not detect performance cores, using total core count")
                if cpu_count >= 12:
                    return min(6, cpu_count)
                elif cpu_count >= 8:
                    return min(4, cpu_count)
                else:
                    return min(3, cpu_count)
        except Exception as e:
            self.logger.debug(f"Failed to detect Apple Silicon cores: {e}")
            # Conservative fallback
            return min(4, cpu_count)

    # ... (rest of the class remains the same)
            device_str = device_info.device_type.value
            if device_info.device_type == DeviceType.CUDA and device_info.device_id is not None:
                device_str = f"{device_str}:{device_info.device_id}"
        else:
            device_str = device

        # Set optimization environment variables
        optimization_env = {
            # PyTorch optimizations
            'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:128',
            'TORCH_CUDNN_V8_API_ENABLED': '1',

            # Whisper optimizations
            'WHISPER_CACHE_DIR': str(Path.home() / '.cache' / 'whisper'),

            # Memory optimizations
            'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:128,garbage_collection_threshold:0.8',
        }

        # Apply optimizations
        for key, value in optimization_env.items():
            if key not in os.environ:
                os.environ[key] = value

        # Configure PyTorch for optimal performance
        if torch.cuda.is_available() and device_str.startswith('cuda'):
            # Enable CUDA optimizations
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.deterministic = False
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        return device_str, optimization_env

    def create_model_pool(self, model_name: str, pool_size: int = 2) -> List[whisper.Whisper]:
        """Create a pool of pre-loaded Whisper models for concurrent processing."""
        device_info = self.get_optimal_device(model_name)
        device_str = device_info.device_type.value

        models = []
        self.logger.info(f"Creating model pool with {pool_size} models on {device_str}")

        for i in range(pool_size):
            try:
                model = whisper.load_model(model_name, device=device_str)
                models.append(model)
                self.logger.info(f"Loaded model {i+1}/{pool_size}")
            except Exception as e:
                self.logger.error(f"Failed to load model {i+1}: {e}")
                break

        return models

    def optimize_transcription_params(self, audio_length_seconds: float, model_size: str = "medium") -> Dict[str, Any]:
        """Optimize transcription parameters based on audio characteristics."""

        # Adjust chunk size based on audio length and model
        if audio_length_seconds < 30:
            # Short audio - process in one go
            chunk_length = 30
        elif audio_length_seconds < 300:
            # Medium audio - use moderate chunks
            chunk_length = 60
        else:
            # Long audio - use larger chunks for efficiency
            chunk_length = 120

        # Adjust based on model size
        if model_size in ["large", "large-v2", "large-v3"]:
            chunk_length = min(chunk_length, 60)  # Large models need smaller chunks

        return {
            "chunk_length": chunk_length,
            "stride_length": chunk_length // 4,  # 25% overlap
            "beam_size": 5 if model_size in ["large", "large-v2", "large-v3"] else 1,
            "best_of": 5 if model_size in ["large", "large-v2", "large-v3"] else 1,
            "temperature": 0.0,  # Use deterministic transcription for consistency
            "compression_ratio_threshold": 2.4,
            "logprob_threshold": -1.0,
            "no_speech_threshold": 0.6,
            "condition_on_previous_text": True,
            "fp16": device_info.device_type != DeviceType.CPU,  # Use FP16 on GPU for speed
        }


class BatchTranscriptionProcessor:
    """Processes multiple audio files in optimized batches."""

    def __init__(self, model_name: str = "medium", max_workers: Optional[int] = None):
        self.model_name = model_name
        self.optimizer = PerformanceOptimizer()
        self.device_info = self.optimizer.get_optimal_device(model_name)
        self.max_workers = max_workers or self.optimizer.get_optimal_worker_count(self.device_info.device_type)
        self.model_pool = []
        self.pool_lock = threading.Lock()

    def initialize(self):
        """Initialize the processor with optimized settings."""
        # Optimize environment
        device_str, env_vars = self.optimizer.optimize_whisper_loading(self.model_name)

        # Create model pool
        pool_size = min(self.max_workers, 2)  # Limit pool size to prevent memory issues
        self.model_pool = self.optimizer.create_model_pool(self.model_name, pool_size)

        if not self.model_pool:
            raise RuntimeError("Failed to load any Whisper models")

        self.logger.info(f"Initialized batch processor with {len(self.model_pool)} models, {self.max_workers} workers")

    def get_model_from_pool(self) -> whisper.Whisper:
        """Get a model from the pool (blocking if none available)."""
        while True:
            with self.pool_lock:
                if self.model_pool:
                    return self.model_pool.pop(0)
            time.sleep(0.1)  # Brief wait if no models available

    def return_model_to_pool(self, model: whisper.Whisper):
        """Return a model to the pool."""
        with self.pool_lock:
            self.model_pool.append(model)

    def transcribe_batch(self, audio_files: List[Path]) -> List[Dict[str, Any]]:
        """Transcribe multiple audio files in an optimized batch."""
        if not self.model_pool:
            self.initialize()

        results = []

        def transcribe_single(audio_path: Path) -> Dict[str, Any]:
            model = self.get_model_from_pool()
            try:
                # Get audio length for optimization
                import librosa
                duration = librosa.get_duration(filename=str(audio_path))

                # Get optimized parameters
                params = self.optimizer.optimize_transcription_params(duration, self.model_name)

                # Transcribe
                result = model.transcribe(str(audio_path), **params)

                return {
                    "file": str(audio_path),
                    "success": True,
                    "result": result,
                    "duration": duration
                }
            except Exception as e:
                return {
                    "file": str(audio_path),
                    "success": False,
                    "error": str(e)
                }
            finally:
                self.return_model_to_pool(model)

        # Process in parallel
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(transcribe_single, audio_path) for audio_path in audio_files]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        return results


# Global optimizer instance
_performance_optimizer = PerformanceOptimizer()


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get the global performance optimizer instance."""
    return _performance_optimizer


def optimize_for_current_system() -> Dict[str, Any]:
    """Get optimization recommendations for the current system."""
    optimizer = get_performance_optimizer()
    devices = optimizer.detect_available_devices()

    recommendations = {
        "available_devices": devices,
        "optimal_device": optimizer.get_optimal_device(),
        "optimal_workers": optimizer.get_optimal_worker_count(devices[0].device_type),
        "optimizations": []
    }

    # Add specific recommendations
    if any(d.device_type == DeviceType.CUDA for d in devices):
        recommendations["optimizations"].append("GPU acceleration available - use CUDA for fastest transcription")

    if any(d.device_type == DeviceType.MPS for d in devices):
        recommendations["optimizations"].append("Apple Silicon GPU available - use MPS for improved performance")

    if len(devices) == 1 and devices[0].device_type == DeviceType.CPU:
        recommendations["optimizations"].append("Only CPU available - consider using smaller models or reducing concurrent workers")

    cpu_count = os.cpu_count() or 1
    if cpu_count >= 8:
        recommendations["optimizations"].append(f"High-performance CPU ({cpu_count} cores) - can handle multiple concurrent transcriptions")

    return recommendations
