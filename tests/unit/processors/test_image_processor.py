"""Unit tests for ImageProcessor."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.processors.image_processor import ImageProcessor
from src.core.config import PipelineConfig


@pytest.mark.unit
@pytest.mark.processor
@pytest.mark.ocr
class TestImageProcessor:
    """Test cases for ImageProcessor."""

    def test_init(self, mock_config):
        """Test ImageProcessor initialization."""
        processor = ImageProcessor(mock_config)

        assert processor.config == mock_config
        assert processor.logger is not None

    @patch('src.processors.image_processor.pytesseract')
    def test_process_images_success(self, mock_config, temp_dir):
        """Test successful image processing."""
        with patch('src.processors.image_processor.pytesseract') as mock_tesseract:
            mock_tesseract.image_to_string.return_value = "Extracted text from image"

            processor = ImageProcessor(mock_config)
            image_path = temp_dir / "test_image.png"
            output_path = temp_dir / "output.txt"

            result = processor.process([image_path], output_path)

            assert result.success is True
            assert result.output_path == output_path
            assert output_path.exists()
            assert "Extracted text from image" in output_path.read_text()

    def test_process_images_file_not_found(self, mock_config, temp_dir):
        """Test processing when image file doesn't exist."""
        processor = ImageProcessor(mock_config)
        non_existent_path = temp_dir / "non_existent.png"
        output_path = temp_dir / "output.txt"

        result = processor.process([non_existent_path], output_path)

        assert result.success is False
        assert "not found" in result.message.lower()

    def test_process_images_no_text_found(self, mock_config, temp_dir):
        """Test handling when no text is found in images."""
        with patch('src.processors.image_processor.pytesseract') as mock_tesseract:
            mock_tesseract.image_to_string.return_value = ""  # Empty string indicates no text found

            processor = ImageProcessor(mock_config)
            image_path = temp_dir / "test_image.png"
            output_path = temp_dir / "output.txt"

            result = processor.process([image_path], output_path)

            assert result.success is True  # Should still succeed even with no text
            assert output_path.exists()
            assert output_path.read_text() == ""  # Empty file created

    def test_process_images_ocr_error(self, mock_config, temp_dir):
        """Test handling of OCR errors."""
        with patch('src.processors.image_processor.pytesseract') as mock_tesseract:
            mock_tesseract.image_to_string.side_effect = Exception("OCR failed")

            processor = ImageProcessor(mock_config)
            image_path = temp_dir / "test_image.png"
            output_path = temp_dir / "output.txt"

            result = processor.process([image_path], output_path)

            assert result.success is False
            assert "ocr" in result.message.lower() or "tesseract" in result.message.lower()

    def test_process_images_empty_list(self, mock_config, temp_dir):
        """Test processing with empty image list."""
        processor = ImageProcessor(mock_config)
        output_path = temp_dir / "output.txt"

        result = processor.process([], output_path)

        assert result.success is False
        assert "no images" in result.message.lower()
