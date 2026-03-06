"""Unit tests for media type detection."""

import pytest
from pathlib import Path

from src.utils.media_utils import MediaTypeDetector


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.media
class TestMediaTypeDetector:
    """Test cases for MediaTypeDetector."""

    def test_detect_video_file(self, sample_video_file):
        """Test video file detection."""
        detector = MediaTypeDetector()
        media_type = detector.detect_media_type(sample_video_file)

        assert media_type == "video"

    def test_detect_audio_file(self, sample_audio_file):
        """Test audio file detection."""
        detector = MediaTypeDetector()
        media_type = detector.detect_media_type(sample_audio_file)

        assert media_type == "audio"

    def test_detect_text_file(self, sample_text_file):
        """Test text file detection."""
        detector = MediaTypeDetector()
        media_type = detector.detect_media_type(sample_text_file)

        assert media_type == "text"

    def test_detect_image_file_png(self, sample_image_file):
        """Test PNG image file detection."""
        detector = MediaTypeDetector()
        media_type = detector.detect_media_type(sample_image_file)

        assert media_type == "image"

    def test_detect_image_file_jpg(self, temp_dir):
        """Test JPG image file detection."""
        jpg_path = temp_dir / "test.jpg"
        jpg_path.write_bytes(b"image content")

        detector = MediaTypeDetector()
        media_type = detector.detect_media_type(jpg_path)

        assert media_type == "image"

    def test_detect_unsupported_extension(self, temp_dir):
        """Test detection of unsupported file extension."""
        unknown_file = temp_dir / "test.xyz"
        unknown_file.write_bytes(b"content")

        detector = MediaTypeDetector()
        media_type = detector.detect_media_type(unknown_file)

        assert media_type == "unknown"

    def test_get_processing_steps_video(self):
        """Test getting processing steps for video files."""
        detector = MediaTypeDetector()
        steps = detector.get_processing_steps("video")

        assert "audio" in steps
        assert "transcript" in steps
        assert "study_material" in steps
        assert "pdf" in steps

    def test_get_processing_steps_audio(self):
        """Test getting processing steps for audio files."""
        detector = MediaTypeDetector()
        steps = detector.get_processing_steps("audio")

        assert "transcript" in steps
        assert "study_material" in steps
        assert "pdf" in steps
        assert "audio" not in steps  # Audio is the starting point

    def test_get_processing_steps_text(self):
        """Test getting processing steps for text files."""
        detector = MediaTypeDetector()
        steps = detector.get_processing_steps("text")

        assert "transcript" in steps
        assert "study_material" in steps
        assert "pdf" in steps
        assert "text" not in steps  # Text is the starting point

    def test_get_processing_steps_image(self):
        """Test getting processing steps for image files."""
        detector = MediaTypeDetector()
        steps = detector.get_processing_steps("image")

        assert "transcript" in steps
        assert "study_material" in steps
        assert "pdf" in steps
        assert "image" not in steps  # Images are the starting point
