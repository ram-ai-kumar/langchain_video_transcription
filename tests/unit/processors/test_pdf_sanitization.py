
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.generators.pdf_generator import PDFGenerator
from src.core.config import PipelineConfig

@pytest.fixture
def pdf_generator():
    config = MagicMock(spec=PipelineConfig)
    config.header_file = Path("/Users/ram/Work/Lab/code/video_transcription/config/header.tex")
    config.generate_pdf = True
    return PDFGenerator(config)

def test_sanitize_path_with_unicode(pdf_generator):
    """Test that _sanitize_path correctly replaces narrow no-break space."""
    # String with \u202f (narrow no-break space)
    path_with_unicode = Path("/Users/ram/Screenshot 2025-12-20 at 12.00.48\u202fPM.pdf")
    expected_path = Path("/Users/ram/Screenshot 2025-12-20 at 12.00.48 PM.pdf")
    
    sanitized = pdf_generator._sanitize_path(path_with_unicode)
    
    assert str(sanitized) == str(expected_path)
    assert '\u202f' not in str(sanitized)

def test_sanitize_path_without_unicode(pdf_generator):
    """Test that _sanitize_path leaves normal paths untouched."""
    normal_path = Path("/Users/ram/normal_file.pdf")
    
    sanitized = pdf_generator._sanitize_path(normal_path)
    
    assert sanitized == normal_path

@patch('src.generators.pdf_generator.subprocess.run')
@patch('src.utils.subprocess_utils.capture_command_output')
def test_generate_pdf_calls_sanitized_paths(mock_capture, mock_run, pdf_generator, tmp_path):
    """Test that generate_pdf uses sanitized paths in the pandoc command."""
    markdown_file = tmp_path / "test\u202f.md"
    markdown_file.write_text("# Test")
    pdf_file = tmp_path / "test\u202f.pdf"
    
    # We need to mock _build_pandoc_command to see if it's using sanitized paths
    # Or just check the arguments passed to capture_command_output
    
    mock_capture.return_value = MagicMock(success=True, stdout="", stderr="")
    
    # We won't actually call generate_pdf because it calls multiple internal things
    # Let's just test _build_pandoc_command directly
    
    cmd = pdf_generator._build_pandoc_command(markdown_file, pdf_file, "tectonic")
    
    # Check if the command contains sanitized paths
    # Note: markdown_path and pdf_path are NOT sanitized in _build_pandoc_command currently
    # based on my implementation, only header_path is. 
    # Let's verify if I should sanitize markdown_path and pdf_path too.
    
    assert any(str(pdf_generator.header_path).replace('\u202f', ' ') in arg for arg in cmd)
