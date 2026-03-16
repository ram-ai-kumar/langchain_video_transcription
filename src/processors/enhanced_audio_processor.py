"""Enhanced audio processor with multi-core and GPU acceleration support."""

import logging
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import concurrent.futures

import whisper
import torch

from src.core.config import PipelineConfig
from src.core.exceptions import TranscriptionError, ModelLoadError
from src.processors.base import BaseProcessor, ProcessResult
from src.utils.performance_optimizer import PerformanceOptimizer, BatchTranscriptionProcessor


class EnhancedAudioProcessor(BaseProcessor):
    """Enhanced audio processor with multi-core and GPU acceleration."""
    
    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.optimizer = PerformanceOptimizer()
        self.batch_processor = None
        self.model_cache = {}
        self.model_lock = threading.Lock()
        
        # Detect optimal device
        self.device_info = self.optimizer.get_optimal_device(config.whisper_model)
        self.device_str = self.device_info.device_type.value
        if self.device_info.device_type.value == "cuda" and self.device_info.device_id is not None:
            self.device_str = f"{self.device_str}:{self.device_info.device_id}"
        
        self.logger.info(f"Enhanced audio processor initialized with device: {self.device_str}")
    
    def can_process(self, file_path: Path) -> bool:
        """Check if processor can handle the file type."""
        return self.config.is_audio_file(file_path)
    
    def _load_model(self, model_name: str) -> whisper.Whisper:
        """Load Whisper model with optimizations."""
        with self.model_lock:
            if model_name in self.model_cache:
                return self.model_cache[model_name]
            
            try:
                # Optimize loading
                device_str, env_vars = self.optimizer.optimize_whisper_loading(model_name)
                
                # Load model with optimizations
                self.logger.info(f"Loading {model_name} model on {device_str}")
                
                # Configure PyTorch for optimal performance
                if torch.cuda.is_available() and device_str.startswith('cuda'):
                    torch.backends.cudnn.benchmark = True
                    torch.backends.cuda.matmul.allow_tf32 = True
                    torch.backends.cudnn.allow_tf32 = True
                
                model = whisper.load_model(model_name, device=device_str)
                
                # Cache the model
                self.model_cache[model_name] = model
                
                self.logger.info(f"Successfully loaded {model_name} model")
                return model
                
            except Exception as e:
                raise ModelLoadError(f"Failed to load Whisper model '{model_name}': {e}")
    
    def process(self, audio_path: Path, transcript_path: Path) -> ProcessResult:
        """Transcribe audio to text with performance optimizations."""
        try:
            self.validate_input(audio_path)
            self.ensure_output_dir(transcript_path)
            
            # Load optimized model
            model = self._load_model(self.config.whisper_model)
            
            # Get audio duration for optimization
            try:
                import librosa
                duration = librosa.get_duration(filename=str(audio_path))
                self.logger.info(f"Audio duration: {duration:.2f} seconds")
            except ImportError:
                duration = 0
                self.logger.warning("librosa not available, cannot detect audio duration")
            
            # Get optimized transcription parameters
            params = self.optimizer.optimize_transcription_params(duration, self.config.whisper_model)
            
            # Add language setting
            if self.config.transcription_language:
                params['language'] = self.config.transcription_language
            
            self.logger.info(f"Transcribing with optimized params: {params}")
            
            # Transcribe with optimizations
            start_time = time.time()
            
            # Use the enhanced transcription method
            result = self._transcribe_optimized(model, str(audio_path), params)
            
            transcription_time = time.time() - start_time
            self.logger.info(f"Transcription completed in {transcription_time:.2f} seconds")
            
            # Write transcript
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(result["text"])
            
            # Calculate performance metrics
            text_length = len(result["text"])
            processing_speed = text_length / transcription_time if transcription_time > 0 else 0
            
            return ProcessResult(
                success=True,
                output_path=transcript_path,
                message=f"Successfully transcribed {audio_path.name}",
                metadata={
                    "duration": result.get("duration"),
                    "language": result.get("language"),
                    "text_length": text_length,
                    "transcription_time": transcription_time,
                    "processing_speed": processing_speed,
                    "device": self.device_str,
                    "model": self.config.whisper_model
                }
            )
            
        except Exception as e:
            raise TranscriptionError(
                f"Failed to transcribe {audio_path.name}: {e}",
                file_path=str(audio_path),
                processor="EnhancedAudioProcessor"
            )
    
    def _transcribe_optimized(self, model: whisper.Whisper, audio_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Transcribe with performance optimizations."""
        try:
            # For GPU devices, use optimized transcription
            if self.device_info.device_type.value in ["cuda", "mps"]:
                return self._transcribe_gpu_optimized(model, audio_path, params)
            else:
                # For CPU, use standard transcription with optimizations
                return model.transcribe(audio_path, **params)
        except Exception as e:
            self.logger.warning(f"Optimized transcription failed, falling back to standard: {e}")
            return model.transcribe(audio_path, **params)
    
    def _transcribe_gpu_optimized(self, model: whisper.Whisper, audio_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """GPU-optimized transcription."""
        # Enable mixed precision for better performance
        original_fp16 = params.get('fp16', False)
        if self.device_info.device_type.value == "cuda":
            params['fp16'] = True
        
        try:
            result = model.transcribe(audio_path, **params)
            return result
        finally:
            # Restore original fp16 setting
            params['fp16'] = original_fp16
    
    def process_batch(self, audio_files: List[Path], output_dir: Path) -> List[ProcessResult]:
        """Process multiple audio files in an optimized batch."""
        self.logger.info(f"Processing batch of {len(audio_files)} files")
        
        # Initialize batch processor if not already done
        if self.batch_processor is None:
            self.batch_processor = BatchTranscriptionProcessor(
                model_name=self.config.whisper_model,
                max_workers=self.optimizer.get_optimal_worker_count(self.device_info.device_type)
            )
            self.batch_processor.initialize()
        
        # Process batch
        batch_results = self.batch_processor.transcribe_batch(audio_files)
        
        # Convert to ProcessResult objects and write files
        results = []
        for result in batch_results:
            audio_path = Path(result["file"])
            transcript_path = output_dir / f"{audio_path.stem}.txt"
            
            if result["success"]:
                try:
                    # Write transcript
                    with open(transcript_path, "w", encoding="utf-8") as f:
                        f.write(result["result"]["text"])
                    
                    process_result = ProcessResult(
                        success=True,
                        output_path=transcript_path,
                        message=f"Successfully transcribed {audio_path.name}",
                        metadata={
                            "duration": result["result"].get("duration"),
                            "language": result["result"].get("language"),
                            "text_length": len(result["result"]["text"]),
                            "device": self.device_str,
                            "model": self.config.whisper_model
                        }
                    )
                except Exception as e:
                    process_result = ProcessResult(
                        success=False,
                        output_path=transcript_path,
                        message=f"Failed to write transcript for {audio_path.name}: {e}"
                    )
            else:
                process_result = ProcessResult(
                    success=False,
                    output_path=transcript_path,
                    message=f"Failed to transcribe {audio_path.name}: {result['error']}"
                )
            
            results.append(process_result)
        
        successful_count = sum(1 for r in results if r.success)
        self.logger.info(f"Batch processing completed: {successful_count}/{len(results)} successful")
        
        return results
    
    def get_performance_info(self) -> Dict[str, Any]:
        """Get performance information and recommendations."""
        return {
            "device_info": {
                "type": self.device_info.device_type.value,
                "device_id": self.device_info.device_id,
                "memory_gb": self.device_info.memory_gb,
                "compute_capability": self.device_info.compute_capability
            },
            "cached_models": list(self.model_cache.keys()),
            "optimizations": self.optimizer.optimize_for_current_system()
        }
    
    def cleanup(self):
        """Clean up resources."""
        with self.model_lock:
            self.model_cache.clear()
        
        if self.batch_processor:
            # Clean up batch processor models
            self.batch_processor.model_pool.clear()
        
        # Clear GPU cache if using CUDA
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.logger.info("Enhanced audio processor cleanup completed")
