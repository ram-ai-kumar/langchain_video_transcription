"""Utilities for managing subprocess output to prevent UI pollution."""

import os
import subprocess
import sys
import threading
import tempfile
from contextlib import contextmanager
from typing import Optional, Dict, Any


class SubprocessSilencer:
    """Manages subprocess output suppression to prevent UI pollution."""

    def __init__(self):
        self._original_env = {}
        self._lock = threading.Lock()

    def setup_environment(self):
        """Setup environment variables to silence subprocess outputs."""
        with self._lock:
            # Store original environment
            self._original_env = {
                'TQDM_DISABLE': os.environ.get('TQDM_DISABLE'),
                'PYTHONWARNINGS': os.environ.get('PYTHONWARNINGS'),
                'WHISPER_SILENCE': os.environ.get('WHISPER_SILENCE'),
                'FFMPEG_LOGLEVEL': os.environ.get('FFMPEG_LOGLEVEL'),
                'PANDOC_LOGLEVEL': os.environ.get('PANDOC_LOGLEVEL'),
            }

            # Set silence environment variables
            os.environ['TQDM_DISABLE'] = '1'
            os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning'
            os.environ['WHISPER_SILENCE'] = '1'
            os.environ['FFMPEG_LOGLEVEL'] = 'error'
            os.environ['PANDOC_LOGLEVEL'] = 'error'

    def restore_environment(self):
        """Restore original environment variables."""
        with self._lock:
            for key, value in self._original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    @contextmanager
    def silenced(self):
        """Context manager for temporarily silencing subprocess output."""
        self.setup_environment()
        try:
            yield
        finally:
            self.restore_environment()


def run_silent_command(
    cmd: list,
    check: bool = True,
    text: bool = False,
    env: Optional[Dict[str, str]] = None,
    **kwargs
) -> subprocess.CompletedProcess:
    """
    Run a subprocess command with completely silenced output.

    Args:
        cmd: Command to run
        check: Whether to raise exception on non-zero exit
        text: Whether to decode output as text
        env: Additional environment variables
        **kwargs: Additional arguments for subprocess.run

    Returns:
        subprocess.CompletedProcess: The completed process result
    """
    # Ensure all output is suppressed
    if 'stdout' not in kwargs:
        kwargs['stdout'] = subprocess.DEVNULL
    if 'stderr' not in kwargs:
        kwargs['stderr'] = subprocess.DEVNULL

    # Set environment variables for silence
    silent_env = {
        'TQDM_DISABLE': '1',
        'PYTHONWARNINGS': 'ignore::UserWarning',
        'WHISPER_SILENCE': '1',
        'FFMPEG_LOGLEVEL': 'error',
        'PANDOC_LOGLEVEL': 'error',
        'LANG': 'en_US.UTF-8',
        'LC_ALL': 'en_US.UTF-8'
    }

    if env:
        silent_env.update(env)

    # Merge with current process environment so PATH and other vars are inherited
    if 'env' in kwargs:
        merged = {**os.environ, **kwargs['env'], **silent_env}
    else:
        merged = {**os.environ, **silent_env}
    kwargs['env'] = merged

    return subprocess.run(cmd, check=check, text=text, **kwargs)


def capture_command_output(
    cmd: list,
    check: bool = True,
    text: bool = False,
    env: Optional[Dict[str, str]] = None,
    **kwargs
) -> subprocess.CompletedProcess:
    """
    Run a subprocess command and capture output while suppressing UI pollution.

    This is useful when you need the output but want to prevent UI pollution.

    Args:
        cmd: Command to run
        check: Whether to raise exception on non-zero exit
        text: Whether to decode output as text
        env: Additional environment variables
        **kwargs: Additional arguments for subprocess.run

    Returns:
        subprocess.CompletedProcess: The completed process result with captured output
    """
    # Set environment variables for silence
    silent_env = {
        'TQDM_DISABLE': '1',
        'PYTHONWARNINGS': 'ignore::UserWarning',
        'WHISPER_SILENCE': '1',
        'FFMPEG_LOGLEVEL': 'error',
        'PANDOC_LOGLEVEL': 'error',
        'LANG': 'en_US.UTF-8',
        'LC_ALL': 'en_US.UTF-8'
    }

    if env:
        silent_env.update(env)

    # Merge with current process environment so PATH and other vars are inherited
    if 'env' in kwargs:
        merged = {**os.environ, **kwargs['env'], **silent_env}
    else:
        merged = {**os.environ, **silent_env}
    kwargs['env'] = merged

    # Use capture_output=True but ensure the environment is silenced
    return subprocess.run(cmd, check=check, capture_output=True, text=text, **kwargs)


# Global silencer instance
_silencer = SubprocessSilencer()


def setup_global_silence():
    """Setup global subprocess silence for the entire application."""
    _silencer.setup_environment()


def restore_global_environment():
    """Restore the original environment."""
    _silencer.restore_environment()


@contextmanager
def temporarily_silenced():
    """Context manager for temporarily silencing subprocess output."""
    with _silencer.silenced():
        yield
