"""Test configuration and fixtures for pytest."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

# Test fixtures
@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    import tempfile
    import shutil
    
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def sample_video_file(temp_dir):
    """Create a sample video file for testing."""
    video_path = temp_dir / "test_video.mp4"
    video_path.write_bytes(b"fake video content")
    return video_path

@pytest.fixture
def sample_audio_file(temp_dir):
    """Create a sample audio file for testing."""
    audio_path = temp_dir / "test_audio.wav"
    audio_path.write_bytes(b"fake audio content")
    return audio_path

@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file for testing."""
    text_path = temp_dir / "test_text.txt"
    text_path.write_text("This is a test transcript for the video transcription system.")
    return text_path

@pytest.fixture
def sample_image_file(temp_dir):
    """Create a sample image file for testing."""
    image_path = temp_dir / "test_image.png"
    image_path.write_bytes(b"fake image content")
    return image_path

@pytest.fixture
def mock_whisper_model():
    """Mock Whisper model for testing."""
    mock_model = Mock()
    mock_model.transcribe.return_value = {
        "text": "Mock transcription result",
        "language": "en"
    }
    return mock_model

@pytest.fixture
def mock_ollama_llm():
    """Mock Ollama LLM for testing."""
    mock_llm = Mock()
    mock_llm.invoke.return_value = "Generated study material content"
    return mock_llm

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    from src.core.config import PipelineConfig
    
    return PipelineConfig(
        whisper_model="tiny",
        llm_model="gemma3",
        generate_pdf=False,
        verbose=True
    )

@pytest.fixture
def sample_file_group(temp_dir):
    """Create a sample file group for testing."""
    group = {
        "video": temp_dir / "lecture.mp4",
        "audio": temp_dir / "lecture.wav", 
        "transcript": temp_dir / "lecture.txt",
        "images": [
            temp_dir / "slide1.png",
            temp_dir / "slide2.png"
        ]
    }
    return group
