"""Comprehensive tests for text_processor to achieve 100% coverage."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.processors.text_processor import TextProcessor
from src.core.config import PipelineConfig
from src.core.exceptions import ProcessingError


@pytest.fixture
def config(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Test prompt")
    header = tmp_path / "header.tex"
    header.write_text("Test header")
    return PipelineConfig(prompt_file=prompt, header_file=header, generate_pdf=False)


@pytest.fixture
def processor(config):
    return TextProcessor(config)


class TestCanProcess:
    def test_can_process_txt(self, processor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        assert processor.can_process(f) is True

    def test_can_process_non_txt(self, processor, tmp_path):
        f = tmp_path / "test.mp4"
        f.write_bytes(b"video")
        assert processor.can_process(f) is False


class TestReadTextFile:
    def test_read_utf8(self, processor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello café", encoding="utf-8")
        assert processor._read_text_file(f) == "Hello café"

    def test_read_latin1_fallback(self, processor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Test content", encoding="latin-1")
        content = processor._read_text_file(f)
        assert "Test content" in content

    def test_read_latin1_fallback_success(self, processor, tmp_path):
        """Test that latin-1 fallback succeeds when UTF-8 fails."""
        f = tmp_path / "test.txt"
        # Write bytes that are invalid UTF-8 but valid latin-1
        f.write_bytes(b'\xe9\xe8\xe0 non-ascii')
        content = processor._read_text_file(f)
        assert "non-ascii" in content

    def test_read_both_encodings_fail(self, processor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"fake")
        # First open (utf-8) raises UnicodeDecodeError, second open (latin-1) raises Exception
        with patch('builtins.open', side_effect=[UnicodeDecodeError("utf-8", b"", 0, 1, "error"), Exception("Cannot read")]):
            with pytest.raises(ProcessingError):
                processor._read_text_file(f)


class TestProcess:
    def test_process_same_path(self, processor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Test content")
        result = processor.process(f, f)
        assert result.success is True
        assert "Using existing" in result.message
        assert result.output_path == f

    def test_process_different_path(self, processor, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("Test content")
        dst = tmp_path / "subdir" / "output.txt"
        result = processor.process(src, dst)
        assert result.success is True
        assert dst.exists()
        assert "Processed" in result.message

    def test_process_file_not_found(self, processor, tmp_path):
        non_existent = tmp_path / "nonexistent.txt"
        with pytest.raises(ProcessingError):
            processor.process(non_existent, tmp_path / "output.txt")

    def test_process_not_a_file(self, processor, tmp_path):
        d = tmp_path / "directory"
        d.mkdir()
        with pytest.raises(ProcessingError):
            processor.process(d, tmp_path / "output.txt")


class TestValidateTextContent:
    def test_valid_content(self, processor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Valid content")
        assert processor.validate_text_content(f) is True

    def test_empty_content(self, processor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("")
        assert processor.validate_text_content(f) is False

    def test_whitespace_only(self, processor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("   \n\n   ")
        assert processor.validate_text_content(f) is False

    def test_read_exception(self, processor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        with patch.object(processor, '_read_text_file', side_effect=Exception("Read error")):
            assert processor.validate_text_content(f) is False


class TestGetTextStats:
    def test_normal_content(self, processor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Line 1\nLine 2\nLine 3")
        stats = processor.get_text_stats(f)
        assert stats["character_count"] == len("Line 1\nLine 2\nLine 3")
        assert stats["line_count"] == 3
        assert stats["word_count"] == 6
        assert stats["has_content"] is True

    def test_empty_content(self, processor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("")
        stats = processor.get_text_stats(f)
        assert stats["character_count"] == 0
        assert stats["has_content"] is False

    def test_stats_exception(self, processor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        with patch.object(processor, '_read_text_file', side_effect=Exception("Read error")):
            stats = processor.get_text_stats(f)
            assert "error" in stats
            assert "Read error" in stats["error"]
