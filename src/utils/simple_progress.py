"""Simple progress simulation for showing progress during long operations."""

import time
import threading
import logging
from typing import Callable, Optional


class ProgressSimulator:
    """Simulates progress for operations that don't provide real progress callbacks."""
    
    def __init__(self, update_callback: Callable[[float, str], None], duration_estimate: float = 60.0):
        self.update_callback = update_callback
        self.duration_estimate = duration_estimate
        self.logger = logging.getLogger(__name__)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None
    
    def start(self, description: str = "Processing..."):
        """Start progress simulation."""
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._simulate_progress, args=(description,))
        self._thread.daemon = True
        self._thread.start()
    
    def stop(self, final_description: str = "Complete!"):
        """Stop progress simulation and set to 100%."""
        self._running = False
        if self.update_callback:
            self.update_callback(100.0, final_description)
        if self._thread:
            self._thread.join(timeout=1.0)
    
    def _simulate_progress(self, description: str):
        """Simulate progress updates."""
        start_time = time.time()
        last_progress = 0.0
        
        while self._running:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Calculate estimated progress (cap at 95% until stopped)
            estimated_progress = min((elapsed / self.duration_estimate) * 100, 95.0)
            
            # Update only if progress changed significantly
            if estimated_progress - last_progress >= 1.0:
                if self.update_callback:
                    self.update_callback(estimated_progress, description)
                last_progress = estimated_progress
            
            # Sleep for a short time
            time.sleep(0.2)


def simulate_transcription_progress(progress_callback: Callable[[float, str], None], audio_duration: float) -> ProgressSimulator:
    """Create a progress simulator for transcription."""
    # Estimate transcription time (Whisper is typically 0.2-0.5x real-time speed)
    estimated_time = audio_duration * 0.4  # Conservative estimate
    return ProgressSimulator(progress_callback, estimated_time)


def simulate_extraction_progress(progress_callback: Callable[[float, str], None]) -> ProgressSimulator:
    """Create a progress simulator for audio extraction."""
    # Audio extraction is typically fast (0.1-0.3x real-time)
    return ProgressSimulator(progress_callback, 30.0)  # 30 seconds default estimate
