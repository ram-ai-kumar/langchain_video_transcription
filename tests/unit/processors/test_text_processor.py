"""Smoke tests for text_processor module."""

import pytest
from pathlib import Path
from src.processors.text_processor import TextProcessor
from src.core.config import PipelineConfig


@pytest.mark.unit
@pytest.mark.smoke
class TestTextProcessorSmoke:
    """Smoke tests for TextProcessor."""

    def test_initialization(self, mock_config):
        """Test that TextProcessor can be initialized."""
        processor = TextProcessor(mock_config)
        assert processor.config == mock_config

    def test_can_process_text(self, mock_config, sample_text_file):
        """Test that processor can identify text files."""
        processor = TextProcessor(mock_config)
        assert processor.can_process(sample_text_file) is True

    def test_can_process_non_text(self, mock_config, sample_audio_file):
        """Test that processor rejects non-text files."""
        processor = TextProcessor(mock_config)
        assert processor.can_process(sample_audio_file) is False

    def test_process_text_file(self, mock_config, sample_text_file, temp_dir):
        """Test basic text file processing."""
        processor = TextProcessor(mock_config)
        output_path = temp_dir / "output.txt"
        
        result = processor.process(sample_text_file, output_path)
        
        assert result.success is True
        assert output_path.exists()
        assert "text_length" in result.metadata

    def test_process_text_same_path(self, mock_config, sample_text_file):
        """Test processing when input and output are the same."""
        processor = TextProcessor(mock_config)
        
        result = processor.process(sample_text_file, sample_text_file)
        
        assert result.success is True
        assert "Using existing" in result.message

    def test_validate_text_content(self, mock_config, sample_text_file):
        """Test text content validation."""
        processor = TextProcessor(mock_config)
        assert processor.validate_text_content(sample_text_file) is True

    def test_validate_text_content_empty(self, mock_config, temp_dir):
        """Test validation with empty file."""
        processor = TextProcessor(mock_config)
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("")
        
        assert processor.validate_text_content(empty_file) is False

    def test_get_text_stats(self, mock_config, sample_text_file):
        """Test getting text statistics."""
        processor = TextProcessor(mock_config)
        stats = processor.get_text_stats(sample_text_file)
        
        assert isinstance(stats, dict)
        assert "character_count" in stats
        assert "line_count" in stats
        assert "word_count" in stats
        assert "has_content" in stats

    def test_read_text_file_utf8(self, mock_config, temp_dir):
        """Test reading UTF-8 encoded text."""
        processor = TextProcessor(mock_config)
        text_file = temp_dir / "utf8.txt"
        text_file.write_text("Test content with unicode: café", encoding="utf-8")
        
        content = processor._read_text_file(text_file)
        assert "café" in content

    def test_read_text_file_latin1_fallback(self, mock_config, temp_dir):
        """Test reading with latin-1 fallback."""
        processor = TextProcessor(mock_config)
        text_file = temp_dir / "latin1.txt"
        text_file.write_text("Test content", encoding="latin-1")
        
        content = processor._read_text_file(text_file)
        assert "Test content" in content
