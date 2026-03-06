"""Unit tests for file utilities."""

import pytest
from pathlib import Path
import tempfile

from src.utils.file_utils import FileDiscovery, FileManager
from src.core.config import PipelineConfig


@pytest.mark.unit
@pytest.mark.utils
class TestFileDiscovery:
    """Test cases for FileDiscovery."""

    def test_group_files_by_stem_empty(self, temp_dir):
        """Test grouping files with empty directory."""
        discovery = FileDiscovery(Mock())

        result = discovery.group_files_by_stem(temp_dir)

        assert result == {}

    def test_group_files_by_stem_success(self, temp_dir, sample_video_file, sample_audio_file, sample_text_file, sample_image_file):
        """Test successful file grouping by stem."""
        # Create test files
        (temp_dir / "lecture.mp4").write_bytes(b"video content")
        (temp_dir / "lecture.wav").write_bytes(b"audio content")
        (temp_dir / "lecture.txt").write_text("transcript content")
        (temp_dir / "slide1.png").write_bytes(b"image content")
        (temp_dir / "slide2.jpg").write_bytes(b"image content")

        discovery = FileDiscovery(Mock())
        result = discovery.group_files_by_stem(temp_dir)

        assert "lecture" in result
        assert result["lecture"]["video"].name == "lecture.mp4"
        assert result["lecture"]["audio"].name == "lecture.wav"
        assert result["lecture"]["transcript"].name == "lecture.txt"
        assert len(result["lecture"]["images"]) == 2
        assert result["lecture"]["images"][0].name == "slide1.png"
        assert result["lecture"]["images"][1].name == "slide2.jpg"

    def test_get_supported_extensions(self):
        """Test getting supported extensions."""
        config = PipelineConfig()
        discovery = FileDiscovery(config)

        extensions = discovery.get_supported_extensions()

        assert "video" in extensions
        assert "audio" in extensions
        assert "text" in extensions
        assert "image" in extensions


class TestFileManager:
    """Test cases for FileManager."""

    def test_ensure_directory_exists_creates_directory(self, temp_dir):
        """Test directory creation when it doesn't exist."""
        test_dir = temp_dir / "new_directory"

        FileManager.ensure_directory_exists(test_dir)

        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_ensure_directory_exists_existing_directory(self, temp_dir):
        """Test handling when directory already exists."""
        test_dir = temp_dir / "existing_directory"
        test_dir.mkdir()

        FileManager.ensure_directory_exists(test_dir)

        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_safe_filename_generation(self):
        """Test safe filename generation."""
        config = PipelineConfig()
        manager = FileManager(config)

        # Test basic filename
        safe_name = manager.safe_filename("test.txt", Path("/output"))
        assert safe_name == "test.txt"

        # Test filename with special characters
        safe_name_special = manager.safe_filename("test@file#.txt", Path("/output"))
        assert safe_name_special == "test_file_.txt"  # Special chars replaced

        # Test filename conflict resolution
        (Path("/output/test.txt")).write_text("existing")
        safe_name_conflict = manager.safe_filename("test.txt", Path("/output"))
        assert safe_name_conflict == "test_1.txt"  # Number added to avoid conflict
