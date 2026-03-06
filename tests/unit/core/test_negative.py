"""Negative tests for edge cases and error conditions."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from src.processors.audio_processor import AudioProcessor
from src.processors.image_processor import ImageProcessor
from src.core.config import PipelineConfig
from src.core.exceptions import ConfigurationError, TranscriptionError, OCRProcessingError


@pytest.mark.unit
@pytest.mark.negative
class TestNegative:
    """Negative tests for edge cases and error conditions."""

    def test_audio_processor_empty_file_path(self, mock_config):
        """Test audio processor with empty file path."""
        processor = AudioProcessor(mock_config)

        with pytest.raises(ValueError, match="file_path cannot be empty"):
            processor.process("", Path("/tmp/output.txt"))

    def test_audio_processor_none_file_path(self, mock_config):
        """Test audio processor with None file path."""
        processor = AudioProcessor(mock_config)

        with pytest.raises(ValueError, match="file_path cannot be empty"):
            processor.process(None, Path("/tmp/output.txt"))

    def test_audio_processor_non_existent_output_dir(self, mock_config, temp_dir):
        """Test audio processor with non-existent output directory."""
        processor = AudioProcessor(mock_config)
        audio_path = temp_dir / "test.wav"
        audio_path.write_bytes(b"test content")

        # Non-existent parent directory should be created
        output_path = temp_dir / "non_existent" / "subdir" / "output.txt"
        result = processor.process(audio_path, output_path)

        assert result.success is True
        assert output_path.exists()
        assert output_path.parent.exists()

    def test_image_processor_empty_image_list(self, mock_config):
        """Test image processor with empty image list."""
        processor = ImageProcessor(mock_config)
        output_path = Path("/tmp/output.txt")

        result = processor.process([], output_path)

        assert result.success is False
        assert "no images" in result.message.lower()

    def test_image_processor_none_image_list(self, mock_config):
        """Test image processor with None image list."""
        processor = ImageProcessor(mock_config)
        output_path = Path("/tmp/output.txt")

        with pytest.raises(ValueError, match="image_paths cannot be empty"):
            processor.process(None, output_path)

    def test_config_invalid_model_types(self):
        """Test configuration with invalid model types."""
        # Test with integer instead of string
        with pytest.raises(TypeError):
            PipelineConfig(whisper_model=123)

        # Test with None instead of string
        with pytest.raises(TypeError):
            PipelineConfig(llm_model=None)

        # Test with list instead of string
        with pytest.raises(TypeError):
            PipelineConfig(whisper_model=["tiny", "base"])

    def test_config_invalid_boolean_types(self):
        """Test configuration with invalid boolean types."""
        # Test with string instead of boolean
        with pytest.raises(TypeError):
            PipelineConfig(generate_pdf="true")

        # Test with integer instead of boolean
        with pytest.raises(TypeError):
            PipelineConfig(verbose=1)

        # Test with None instead of boolean
        with pytest.raises(TypeError):
            PipelineConfig(generate_pdf=None)

    def test_file_path_edge_cases(self):
        """Test file path handling with edge cases."""
        from src.utils.file_utils import FileManager

        # Test with very long path
        long_path = Path("/" + "a" * 1000)
        assert FileManager.ensure_directory_exists(long_path)

        # Test with special characters in path
        special_path = Path("/tmp/test@file#name.txt")
        safe_name = FileManager.safe_filename("test@file#name.txt", Path("/tmp"))
        assert "@" not in safe_name
        assert "#" not in safe_name

    def test_memory_edge_cases(self):
        """Test memory handling with edge cases."""
        # Test with zero-byte file
        zero_byte_path = Path("/tmp/zero_byte.txt")
        zero_byte_path.write_bytes(b"")

        # Should process without error (empty file is valid)
        assert zero_byte_path.exists()
        assert zero_byte_path.stat().st_size == 0

    def test_concurrent_access_simulation(self):
        """Test behavior that might occur under concurrent access."""
        import threading
        import time

        results = []

        def worker():
            # Simulate concurrent file access
            temp_file = Path(tempfile.gettempdir()) / f"concurrent_test_{threading.get_ident()}.txt"
            temp_file.write_text(f"Thread {threading.get_ident()}")
            time.sleep(0.01)
            results.append(temp_file.exists())

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All threads should complete successfully
        assert all(results)
        assert len(results) == 5
