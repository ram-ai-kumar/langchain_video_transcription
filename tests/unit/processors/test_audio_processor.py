"""Unit tests for AudioProcessor."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.processors.audio_processor import AudioProcessor
from src.core.config import PipelineConfig


@pytest.mark.unit
@pytest.mark.processor
class TestAudioProcessor:
    """Test cases for AudioProcessor."""

    def test_init(self, mock_config):
        """Test AudioProcessor initialization."""
        processor = AudioProcessor(mock_config)

        assert processor.config == mock_config
        assert processor.logger is not None

    @patch('src.processors.audio_processor.whisper')
    def test_load_whisper_model(self, mock_whisper, mock_config):
        """Test Whisper model loading."""
        mock_whisper.load_model.return_value = Mock()

        processor = AudioProcessor(mock_config)
        model = processor._load_whisper_model()

        mock_whisper.load_model.assert_called_once_with("tiny", device="cpu")
        assert model is not None

    def test_process_audio_success(self, mock_config, temp_dir):
        """Test successful audio processing."""
        with patch('src.processors.audio_processor.whisper') as mock_whisper:
            mock_whisper.load_model.return_value = Mock()
            mock_whisper.load_model.return_value.transcribe.return_value = {
                "text": "Transcribed audio content"
            }

            processor = AudioProcessor(mock_config)
            audio_path = temp_dir / "test_audio.wav"
            output_path = temp_dir / "output.txt"

            result = processor.process(audio_path, output_path)

            assert result.success is True
            assert result.output_path == output_path
            assert output_path.exists()
            assert "Transcribed audio content" in output_path.read_text()

    def test_process_audio_file_not_found(self, mock_config, temp_dir):
        """Test processing when audio file doesn't exist."""
        processor = AudioProcessor(mock_config)
        non_existent_path = temp_dir / "non_existent.wav"
        output_path = temp_dir / "output.txt"

        result = processor.process(non_existent_path, output_path)

        assert result.success is False
        assert "not found" in result.message.lower()

    def test_process_audio_whisper_error(self, mock_config, temp_dir):
        """Test handling of Whisper transcription errors."""
        with patch('src.processors.audio_processor.whisper') as mock_whisper:
            mock_whisper.load_model.return_value = Mock()
            mock_whisper.load_model.return_value.transcribe.side_effect = Exception("Whisper failed")

            processor = AudioProcessor(mock_config)
            audio_path = temp_dir / "test_audio.wav"
            output_path = temp_dir / "output.txt"

            result = processor.process(audio_path, output_path)

            assert result.success is False
            assert "whisper" in result.message.lower() or "transcription" in result.message.lower()
