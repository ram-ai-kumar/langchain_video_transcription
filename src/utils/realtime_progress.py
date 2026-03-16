"""Real-time progress utilities for showing progress during long-running operations."""

import time
import threading
import logging
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import subprocess
import re


class ProgressStage(Enum):
    """Stages of processing for different operations."""
    EXTRACTING_AUDIO = "extracting_audio"
    LOADING_MODEL = "loading_model"
    TRANSCRIBING = "transcribing"
    GENERATING_STUDY = "generating_study"
    CREATING_PDF = "creating_pdf"


@dataclass
class RealtimeProgress:
    """Real-time progress information."""
    stage: ProgressStage
    current: float
    total: float
    description: str
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    @property
    def percentage(self) -> float:
        """Calculate percentage complete."""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100


class RealtimeProgressManager:
    """Manages real-time progress updates for long-running operations."""
    
    def __init__(self, update_callback: Optional[Callable[[RealtimeProgress], None]] = None):
        self.update_callback = update_callback
        self.logger = logging.getLogger(__name__)
        self._current_progress: Optional[RealtimeProgress] = None
        self._lock = threading.Lock()
        self._last_update = 0.0
        self._min_update_interval = 0.1  # 100ms minimum between updates
    
    def create_progress_tracker(self, stage: ProgressStage, total: float, description: str = "") -> 'ProgressTracker':
        """Create a new progress tracker for a specific stage."""
        return ProgressTracker(self, stage, total, description)
    
    def update_progress(self, progress: RealtimeProgress):
        """Update progress with throttling."""
        current_time = time.time()
        with self._lock:
            if current_time - self._last_update >= self._min_update_interval:
                self._current_progress = progress
                if self.update_callback:
                    self.update_callback(progress)
                self._last_update = current_time
    
    def get_current_progress(self) -> Optional[RealtimeProgress]:
        """Get current progress information."""
        with self._lock:
            return self._current_progress


class ProgressTracker:
    """Tracks progress for a specific operation."""
    
    def __init__(self, manager: RealtimeProgressManager, stage: ProgressStage, total: float, description: str = ""):
        self.manager = manager
        self.stage = stage
        self.total = total
        self.description = description
        self.current = 0.0
        self.start_time = time.time()
        self._last_percentage = -1.0
    
    def update(self, current: float, description: Optional[str] = None):
        """Update current progress."""
        self.current = current
        if description:
            self.description = description
        
        # Only update if percentage changed significantly
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        if abs(percentage - self._last_percentage) >= 1.0:  # Update only on 1% change
            progress = RealtimeProgress(
                stage=self.stage,
                current=self.current,
                total=self.total,
                description=self.description or f"{self.stage.value.replace('_', ' ').title()}"
            )
            self.manager.update_progress(progress)
            self._last_percentage = percentage
    
    def increment(self, amount: float = 1.0, description: Optional[str] = None):
        """Increment progress by amount."""
        self.update(self.current + amount, description)
    
    def set_percentage(self, percentage: float, description: Optional[str] = None):
        """Set progress by percentage (0-100)."""
        self.update((percentage / 100.0) * self.total, description)
    
    def finish(self, description: Optional[str] = None):
        """Mark progress as complete."""
        self.update(self.total, description or f"Completed {self.stage.value}")


class WhisperProgressTracker:
    """Tracks Whisper transcription progress with simulated updates."""
    
    def __init__(self, progress_manager: RealtimeProgressManager, audio_duration_seconds: float):
        self.progress_manager = progress_manager
        self.audio_duration = audio_duration_seconds
        self.tracker = progress_manager.create_progress_tracker(
            ProgressStage.TRANSCRIBING, 
            100.0,  # Use percentage as total
            "Transcribing audio..."
        )
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start progress tracking."""
        self._running = True
        self._thread = threading.Thread(target=self._simulate_progress)
        self._thread.daemon = True
        self._thread.start()
    
    def stop(self):
        """Stop progress tracking."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
    
    def _simulate_progress(self):
        """Simulate transcription progress since Whisper doesn't provide callbacks."""
        # Estimate transcription time based on audio duration
        # Whisper typically processes at ~0.3x real-time speed on CPU, faster on GPU
        estimated_duration = self.audio_duration * 0.3  # Conservative estimate
        
        start_time = time.time()
        last_update = 0.0
        
        while self._running and last_update < 100.0:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Calculate estimated progress
            estimated_progress = min((elapsed / estimated_duration) * 100, 95.0)  # Cap at 95% until complete
            
            # Update progress if significantly changed
            if estimated_progress - last_update >= 1.0:
                self.tracker.set_percentage(estimated_progress)
                last_update = estimated_progress
            
            # Sleep for a short time
            time.sleep(0.2)
        
        # If still running, set to 100%
        if self._running:
            self.tracker.set_percentage(100.0, "Transcription complete!")


class FFmpegProgressTracker:
    """Tracks FFmpeg audio extraction progress."""
    
    def __init__(self, progress_manager: RealtimeProgressManager):
        self.progress_manager = progress_manager
        self.tracker = progress_manager.create_progress_tracker(
            ProgressStage.EXTRACTING_AUDIO,
            100.0,
            "Extracting audio..."
        )
    
    def parse_progress_line(self, line: str) -> bool:
        """Parse FFmpeg progress line and update tracker."""
        # FFmpeg progress line format: frame=123 fps=30.0 q=28.0 size=1024kB time=00:01:23.45 bitrate=128.0kbits/s
        time_match = re.search(r'time=(\d+):(\d+):(\d+\.?\d*)', line)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            seconds = float(time_match.group(3))
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # We don't know the total duration, so we'll estimate based on time
            # Assume most videos are under 2 hours for this estimation
            estimated_total = 7200  # 2 hours in seconds
            percentage = min((total_seconds / estimated_total) * 100, 95.0)
            
            self.tracker.set_percentage(percentage, f"Extracting audio... {hours:02d}:{minutes:02d}:{seconds:05.2f}")
            return True
        
        return False


def create_whisper_progress_callback(progress_manager: RealtimeProgressManager, audio_duration: float) -> Callable:
    """Create a progress callback for Whisper transcription."""
    tracker = WhisperProgressTracker(progress_manager, audio_duration)
    tracker.start()
    
    def callback(progress_info):
        """Progress callback that does nothing (Whisper doesn't provide real progress)."""
        # Whisper doesn't actually call this callback, but we keep it for interface compatibility
        pass
    
    # Return a callback that also handles cleanup
    def wrapped_callback():
        tracker.stop()
    
    return callback, wrapped_callback


def create_ffmpeg_progress_callback(progress_manager: RealtimeProgressManager) -> Callable[[str], bool]:
    """Create a progress callback for FFmpeg operations."""
    ffmpeg_tracker = FFmpegProgressTracker(progress_manager)
    
    def callback(line: str) -> bool:
        """Process FFmpeg output line."""
        return ffmpeg_tracker.parse_progress_line(line)
    
    return callback
