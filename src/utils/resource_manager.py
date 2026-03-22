
import os
import psutil
import logging
import platform
import subprocess
from typing import Dict, Any

class ResourceManager:
    """Manages system resources and provides recommendations for concurrency."""
    
    def __init__(self, verbose: bool = False):
        self.logger = logging.getLogger(__name__)
        self.verbose = verbose
        self.is_mac = platform.system() == "Darwin"
        
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system RAM, CPU and GPU stats."""
        vm = psutil.virtual_memory()
        stats = {
            "ram_total_gb": vm.total / (1024**3),
            "ram_available_gb": vm.available / (1024**3),
            "ram_percent": vm.percent,
            "cpu_count": psutil.cpu_count(logical=True),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "gpu_available": False,
            "gpu_type": None
        }
        
        # Check for GPU (MPS on Mac, CUDA elsewhere)
        if self.is_mac:
            # Check for Apple Silicon / MPS availability
            try:
                import torch
                if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    stats["gpu_available"] = True
                    stats["gpu_type"] = "mps"
            except ImportError:
                # Fallback to system check if torch isn't installed yet
                try:
                    res = subprocess.check_output(["sysctl", "-n", "hw.optional.arm64"], text=True)
                    if res.strip() == "1":
                        stats["gpu_available"] = True
                        stats["gpu_type"] = "mps"
                except Exception:
                    pass
        else:
            try:
                import torch
                if torch.cuda.is_available():
                    stats["gpu_available"] = True
                    stats["gpu_type"] = "cuda"
            except ImportError:
                pass
                
        return stats

    def get_concurrency_recommendation(self, heavy_task_memory_gb: float = 8.0) -> Dict[str, int]:
        """
        Calculate recommended concurrency based on available RAM.
        
        Args:
            heavy_task_memory_gb: Estimated RAM needed for one heavy task (e.g. Qwen 3.5).
        """
        stats = self.get_system_stats()
        available_ram = stats["ram_available_gb"]
        
        # Leave at least 25% of total RAM free for the OS/other apps (user requirement)
        buffer_ram = stats["ram_total_gb"] * 0.25
        useable_ram = max(0.5, available_ram - buffer_ram)
        
        # Calculate how many heavy tasks can run
        recommended_heavy = max(1, int(useable_ram // heavy_task_memory_gb))
        
        # General concurrency can be slightly higher than heavy task count
        # if we have image processing or text tasks which are light.
        recommended_total = recommended_heavy + 1
        
        # Cap by CPU count
        recommended_total = min(recommended_total, stats["cpu_count"])
        
        if self.verbose:
            print(f"    [RESOURCE] RAM: {stats['ram_available_gb']:.1f}GB available. "
                  f"Recommend {recommended_heavy} heavy tasks.")
            
        return {
            "max_heavy_tasks": recommended_heavy,
            "max_total_tasks": recommended_total,
            "window_size": recommended_total * 2
        }
