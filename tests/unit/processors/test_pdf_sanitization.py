
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
    # Test with narrow no-break (\u202f)
    markdown_file = Path("/tmp/test\u202ffile.md")
    pdf_file = Path("/tmp/test\u202ffile.pdf")

    # Check _build_pandoc_command directly
    cmd = pdf_generator._build_pandoc_command(markdown_file, pdf_file, "tectonic")

    # Verify that the command contains sanitized paths
    assert any("/tmp/test file.md" in arg for arg in cmd)
    assert any("/tmp/test file.pdf" in arg for arg in cmd)

def test_file_utils_sanitizes_robustly():
    """Test that FileDiscovery.get_output_paths handles all Unicode whitespace."""
    from src.utils.file_utils import FileDiscovery
    config = MagicMock(spec=PipelineConfig)
    discovery = FileDiscovery(config)

    # Test with various space-like characters
    # \u202f = narrow no-break space, \u00a0 = non-breaking space, \t = tab
    # Each should be replaced by a single space
    source_path = Path("/Users/ram/Test\u202fSpace\u00a0Tab\tFile.txt")
    paths = discovery.get_output_paths(source_path, "text")

    # All output paths should have standard spaces
    for path in paths.values():
        path_str = str(path)
        assert '\u202f' not in path_str
        assert '\u00a0' not in path_str
        assert '\t' not in path_str
        # Test Space Tab File
        assert 'Test Space Tab File' in path_str

def test_sanitize_unicode_whitespace(pdf_generator):
    """Test that _sanitize_unicode_whitespace replaces problematic Unicode whitespace."""
    # Test with narrow no-break space (\u202f)
    content_with_nbsp = "Time 11.50.00\u202fAM"
    sanitized = pdf_generator._sanitize_unicode_whitespace(content_with_nbsp)

    assert '\u202f' not in sanitized
    assert '11.50.00 AM' in sanitized

    # Test with non-breaking space (\u00a0)
    content_with_nbsp2 = "Test\u00a0Space"
    sanitized2 = pdf_generator._sanitize_unicode_whitespace(content_with_nbsp2)

    assert '\u00a0' not in sanitized2
    assert 'Test Space' in sanitized2

    # Test with tab - tabs are preserved to maintain markdown formatting
    content_with_tab = "Test\tTab"
    sanitized3 = pdf_generator._sanitize_unicode_whitespace(content_with_tab)

    assert '\t' in sanitized3  # Tabs are preserved for markdown structure
    assert 'Test' in sanitized3
    assert 'Tab' in sanitized3
