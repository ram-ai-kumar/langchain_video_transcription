"""Smoke tests for whisper_utils module."""

import pytest
from src.utils.whisper_utils import WhisperSilencer, whisper_silenced


@pytest.mark.unit
@pytest.mark.smoke
class TestWhisperSilencerSmoke:
    """Smoke tests for WhisperSilencer."""

    def test_initialization(self):
        """Test that WhisperSilencer can be initialized."""
        silencer = WhisperSilencer()
        assert silencer._original_stdout is None
        assert silencer._original_stderr is None
        assert silencer._devnull is None

    def test_silenced_context_manager(self):
        """Test that silenced context manager works."""
        silencer = WhisperSilencer()
        
        with silencer.silenced():
            # Context manager should not raise exceptions
            pass
        
        # After context, streams should be restored
        assert silencer._devnull is None

    def test_global_whisper_silenced(self):
        """Test that global whisper_silenced context manager works."""
        with whisper_silenced():
            # Context manager should not raise exceptions
            pass


@pytest.mark.unit
@pytest.mark.smoke
class TestLoadWhisperModelSilentSmoke:
    """Smoke tests for load_whisper_model_silent."""

    @pytest.mark.skip(reason="Requires Whisper model download")
    def test_load_whisper_model_silent_tiny(self):
        """Test loading tiny model silently."""
        from src.utils.whisper_utils import load_whisper_model_silent
        
        model = load_whisper_model_silent("tiny", device="cpu")
        assert model is not None

    @pytest.mark.skip(reason="Requires Whisper model download")
    def test_load_whisper_model_silent_auto_device(self):
        """Test loading model with auto device detection."""
        from src.utils.whisper_utils import load_whisper_model_silent
        
        model = load_whisper_model_silent("tiny", device="auto")
        assert model is not None


@pytest.mark.unit
@pytest.mark.smoke
class TestTranscribeSilentSmoke:
    """Smoke tests for transcribe_silent."""

    @pytest.mark.skip(reason="Requires Whisper model and audio file")
    def test_transcribe_silent_basic(self, temp_dir):
        """Test silent transcription."""
        from src.utils.whisper_utils import load_whisper_model_silent, transcribe_silent
        
        # Create a dummy audio file
        audio_path = temp_dir / "test.wav"
        audio_path.write_bytes(b"fake audio")
        
        model = load_whisper_model_silent("tiny", device="cpu")
        # This will fail with real audio, but tests the function signature
        assert callable(transcribe_silent)
