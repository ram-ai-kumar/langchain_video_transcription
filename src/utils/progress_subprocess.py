"""Enhanced subprocess utilities with progress capture while preventing UI pollution."""

import os
import subprocess
import sys
import threading
import re
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any, Callable, Tuple
from dataclasses import dataclass
from enum import Enum


class ProgressType(Enum):
    """Types of progress information."""
    PERCENTAGE = "percentage"
    FRAME_COUNT = "frame_count"
    TIME_ELAPSED = "time_elapsed"
    TIME_REMAINING = "time_remaining"
    SPEED = "speed"
    SIZE = "size"


@dataclass
class ProgressInfo:
    """Progress information from subprocess output."""
    type: ProgressType
    value: float
    total: Optional[float] = None
    unit: str = ""
    description: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class ProgressParser:
    """Parses progress information from subprocess output."""
    
    def __init__(self):
        # Common regex patterns for different tools
        self.patterns = {
            'ffmpeg_progress': re.compile(
                r'frame=\s*(\d+)\s+fps=\s*[\d.]+\s+q=\s*[\d.]+\s+(?:size|L)?=\s*[\d.]+\kB\s+time=\s*([\d:]+)\s+bitrate=\s*[\d.]+kbits/s'
            ),
            'ffmpeg_percentage': re.compile(
                r'(\d+(?:\.\d+)?)%'
            ),
            'whisper_progress': re.compile(
                r'(\d+)%\|\s*(\d+)/(\d+)\s*\[([^\]]+)\]'
            ),
            'pandoc_progress': re.compile(
                r'(\d+)%'
            ),
            'generic_percentage': re.compile(
                r'(\d+(?:\.\d+)?)%.*?(\d+(?:\.\d+)?)(?:/(\d+(?:\.\d+)?))?'
            ),
        }
    
    def parse_line(self, line: str) -> Optional[ProgressInfo]:
        """Parse a single line of output for progress information."""
        line = line.strip()
        
        # Try ffmpeg patterns
        match = self.patterns['ffmpeg_progress'].search(line)
        if match:
            frame_count = int(match.group(1))
            time_str = match.group(2)
            return ProgressInfo(
                type=ProgressType.FRAME_COUNT,
                value=frame_count,
                unit="frames",
                description=f"Frame {frame_count} at {time_str}"
            )
        
        # Try whisper patterns
        match = self.patterns['whisper_progress'].search(line)
        if match:
            percentage = float(match.group(1))
            current = int(match.group(2))
            total = int(match.group(3))
            time_info = match.group(4)
            return ProgressInfo(
                type=ProgressType.PERCENTAGE,
                value=percentage,
                total=total,
                unit="%",
                description=f"{percentage}% ({current}/{total}) {time_info}"
            )
        
        # Try generic percentage patterns
        match = self.patterns['generic_percentage'].search(line)
        if match:
            percentage = float(match.group(1))
            current = float(match.group(2)) if len(match.groups()) > 1 else None
            total = float(match.group(3)) if len(match.groups()) > 2 and match.group(3) else None
            return ProgressInfo(
                type=ProgressType.PERCENTAGE,
                value=percentage,
                total=total,
                unit="%",
                description=f"{percentage}% complete"
            )
        
        return None


class ProgressCallback:
    """Callback for handling progress updates."""
    
    def __init__(self, callback: Callable[[ProgressInfo], None]):
        self.callback = callback
        self.last_update = 0
        self.min_interval = 0.1  # Minimum 100ms between updates
    
    def __call__(self, progress_info: ProgressInfo):
        """Call the callback if enough time has passed."""
        current_time = time.time()
        if current_time - self.last_update >= self.min_interval:
            self.callback(progress_info)
            self.last_update = current_time


def run_command_with_progress(
    cmd: list,
    progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    check: bool = True,
    text: bool = False,
    env: Optional[Dict[str, str]] = None,
    **kwargs
) -> subprocess.CompletedProcess:
    """
    Run a subprocess command while capturing progress information.
    
    Args:
        cmd: Command to run
        progress_callback: Callback function to receive progress updates
        check: Whether to raise exception on non-zero exit
        text: Whether to decode output as text
        env: Additional environment variables
        **kwargs: Additional arguments for subprocess.run
        
    Returns:
        subprocess.CompletedProcess: The completed process result
    """
    # Set environment variables for silence but allow progress
    silent_env = {
        'TQDM_DISABLE': '1',
        'PYTHONWARNINGS': 'ignore::UserWarning',
        'WHISPER_SILENCE': '1',
        'FFMPEG_LOGLEVEL': 'info',  # Changed from 'error' to 'info' to get progress
        'PANDOC_LOGLEVEL': 'error',
        'LANG': 'en_US.UTF-8',
        'LC_ALL': 'en_US.UTF-8'
    }
    
    if env:
        silent_env.update(env)
    
    # Add to existing environment
    if 'env' in kwargs:
        kwargs['env'].update(silent_env)
    else:
        kwargs['env'] = silent_env
    
    # Setup progress parsing
    parser = ProgressParser()
    callback = None
    if progress_callback:
        callback = ProgressCallback(progress_callback)
    
    # Use Popen for real-time output capture
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Combine stderr into stdout
        text=text,
        **kwargs
    )
    
    # Capture output in real-time
    output_lines = []
    
    if process.stdout:
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
                
            output_lines.append(line)
            
            # Parse progress information
            if callback:
                progress_info = parser.parse_line(line)
                if progress_info:
                    callback(progress_info)
    
    # Wait for process to complete
    process.wait()
    
    # Combine output
    output = ''.join(output_lines) if text else b''.join(output_lines)
    
    # Create result
    result = subprocess.CompletedProcess(
        args=cmd,
        returncode=process.returncode,
        stdout=output,
        stderr=None  # Combined into stdout
    )
    
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )
    
    return result


def ffmpeg_with_progress(
    cmd: list,
    progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    **kwargs
) -> subprocess.CompletedProcess:
    """
    Run ffmpeg with progress capture.
    
    Args:
        cmd: ffmpeg command (without -loglevel)
        progress_callback: Callback for progress updates
        **kwargs: Additional arguments
        
    Returns:
        subprocess.CompletedProcess: The completed process result
    """
    # Ensure ffmpeg command has proper log level for progress
    if "-loglevel" not in " ".join(cmd):
        cmd = ["ffmpeg", "-loglevel", "info"] + cmd[1:]
    
    return run_command_with_progress(cmd, progress_callback, **kwargs)


def whisper_with_progress(
    model,
    audio_path: str,
    progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    **kwargs
) -> dict:
    """
    Run Whisper transcription with progress capture.
    
    Args:
        model: Loaded Whisper model
        audio_path: Path to audio file
        progress_callback: Callback for progress updates
        **kwargs: Additional arguments for whisper.transcribe
        
    Returns:
        dict: Transcription result
    """
    # For Whisper, we need to capture stdout from the model loading/transcription
    # This is more complex since Whisper doesn't expose progress callbacks directly
    
    # Setup progress parsing
    parser = ProgressParser()
    callback = None
    if progress_callback:
        callback = ProgressCallback(progress_callback)
    
    # Redirect stdout temporarily to capture progress
    import io
    import contextlib
    
    captured_output = io.StringIO()
    
    with contextlib.redirect_stdout(captured_output):
        # Run transcription
        result = model.transcribe(audio_path, **kwargs)
    
    # Parse captured output for progress information
    captured_output.seek(0)
    for line in captured_output:
        if callback:
            progress_info = parser.parse_line(line)
            if progress_info:
                callback(progress_info)
    
    return result


@contextmanager
def temporary_progress_env():
    """Context manager for temporarily enabling progress output."""
    old_env = {}
    progress_vars = {
        'FFMPEG_LOGLEVEL': 'info',
        'TQDM_DISABLE': '0',  # Enable tqdm for progress
    }
    
    try:
        # Store old values
        for key, value in progress_vars.items():
            old_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        yield
        
    finally:
        # Restore old values
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
