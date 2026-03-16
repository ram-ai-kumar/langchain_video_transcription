"""Utilities for managing Whisper model loading and transcription output."""

import os
import sys
import logging
import warnings
import contextlib
from typing import Optional
import whisper


class WhisperSilencer:
    """Manages Whisper output suppression to prevent UI pollution."""

    def __init__(self):
        self._original_stdout = None
        self._original_stderr = None
        self._devnull = None

    def _setup_silence(self):
        """Setup output redirection for silence."""
        self._devnull = open(os.devnull, 'w')
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = self._devnull
        sys.stderr = self._devnull

    def _restore_output(self):
        """Restore original output streams."""
        if self._original_stdout:
            sys.stdout = self._original_stdout
        if self._original_stderr:
            sys.stderr = self._original_stderr
        if self._devnull:
            self._devnull.close()
            self._devnull = None

    @contextlib.contextmanager
    def silenced(self):
        """Context manager for temporarily silencing Whisper output."""
        try:
            self._setup_silence()
            yield
        finally:
            self._restore_output()


def load_whisper_model_silent(model_name: str, device: str = "auto") -> whisper.Whisper:
    """
    Load Whisper model with complete output suppression.

    Args:
        model_name: Name of the Whisper model to load
        device: Device to use ('auto', 'cpu', 'cuda', 'mps')

    Returns:
        Loaded Whisper model
    """
    # Determine device if auto
    if device == "auto":
        import torch
        import platform
        is_macos = platform.system() == "Darwin"
        is_apple_silicon = is_macos and platform.machine() in ["arm64", "arm64e"]

        if is_apple_silicon and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"

    # Setup comprehensive silence
    with WhisperSilencer().silenced():
        # Set environment variables for maximum silence
        old_env = {}
        env_vars_to_set = {
            'TQDM_DISABLE': '1',
            'PYTHONWARNINGS': 'ignore::UserWarning',
            'WHISPER_SILENCE': '1',
            'PYTHONIOENCODING': 'utf-8'
        }

        for key, value in env_vars_to_set.items():
            old_env[key] = os.environ.get(key)
            os.environ[key] = value

        # Suppress logging
        logging.getLogger('whisper').setLevel(logging.CRITICAL)

        # Suppress warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                model = whisper.load_model(model_name, device=device)
            finally:
                # Restore environment
                for key, value in old_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    return model


def transcribe_silent(
    model: whisper.Whisper,
    audio_path: str,
    language: Optional[str] = None,
    progress_callback: Optional[Callable] = None,
    **kwargs
) -> dict:
    """
    Transcribe audio with complete output suppression and optional progress capture.

    Args:
        model: Loaded Whisper model
        audio_path: Path to audio file
        language: Language code (optional)
        progress_callback: Callback for progress updates
        **kwargs: Additional arguments for whisper.transcribe

    Returns:
        Transcription result dictionary
    """
    # Setup comprehensive silence
    with WhisperSilencer().silenced():
        # Set environment variables for maximum silence
        old_env = {}
        env_vars_to_set = {
            'TQDM_DISABLE': '1',
            'PYTHONWARNINGS': 'ignore::UserWarning',
            'WHISPER_SILENCE': '1'
        }

        for key, value in env_vars_to_set.items():
            old_env[key] = os.environ.get(key)
            os.environ[key] = value

        # Suppress logging
        logging.getLogger('whisper').setLevel(logging.CRITICAL)

        # Default transcription options for silence
        transcribe_kwargs = {
            'verbose': False,
            'fp16': False,
            'language': language
        }
        transcribe_kwargs.update(kwargs)

        # Suppress warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                # Use the progress-enabled transcription if callback provided
                if progress_callback:
                    # For now, use regular silent transcription to avoid regex issues
                    result = model.transcribe(audio_path, **transcribe_kwargs)
                else:
                    result = model.transcribe(audio_path, **transcribe_kwargs)
            finally:
                # Restore environment
                for key, value in old_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    return result


# Global silencer instance
_whisper_silencer = WhisperSilencer()


@contextlib.contextmanager
def whisper_silenced():
    """Context manager for temporarily silencing Whisper output."""
    with _whisper_silencer.silenced():
        yield
