"""Comprehensive tests for PDFGenerator to achieve 100% coverage."""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open

from src.generators.pdf_generator import PDFGenerator
from src.core.config import PipelineConfig
from src.core.exceptions import PDFGenerationError
from src.processors.base import ProcessResult


@pytest.fixture
def pdf_config(tmp_path):
    """Create a config with real header file."""
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Test prompt")
    header_file = tmp_path / "header.tex"
    header_file.write_text("Test header")
    return PipelineConfig(
        prompt_file=prompt_file,
        header_file=header_file,
        generate_pdf=True,
    )


@pytest.fixture
def pdf_generator(pdf_config):
    return PDFGenerator(pdf_config)


@pytest.fixture
def markdown_file(tmp_path):
    """Create a real markdown file."""
    md = tmp_path / "test.md"
    md.write_text("# Test\n\nThis is test content.")
    return md


class TestPDFGeneratorInit:
    def test_init(self, pdf_config):
        gen = PDFGenerator(pdf_config)
        assert gen.config == pdf_config
        assert gen.header_path == pdf_config.header_file


class TestSanitizePath:
    def test_sanitize_path_with_unicode(self, pdf_generator):
        path = Path("/tmp/test\u202ffile.pdf")
        sanitized = pdf_generator._sanitize_path(path)
        assert "\u202f" not in str(sanitized)
        assert "test file.pdf" in str(sanitized)

    def test_sanitize_path_without_unicode(self, pdf_generator):
        path = Path("/tmp/normal_file.pdf")
        assert pdf_generator._sanitize_path(path) == path


class TestSanitizeCodeBlocks:
    def test_code_block_without_language(self, pdf_generator):
        content = "Some text\n```\ncode here\n```\nMore text"
        result = pdf_generator._sanitize_code_blocks(content)
        assert "```text" in result

    def test_code_block_with_language(self, pdf_generator):
        content = "Some text\n```python\ncode here\n```\nMore text"
        result = pdf_generator._sanitize_code_blocks(content)
        assert "```python" in result

    def test_no_code_blocks(self, pdf_generator):
        content = "Just regular text\nNo code blocks"
        result = pdf_generator._sanitize_code_blocks(content)
        assert result == content

    def test_multiple_code_blocks(self, pdf_generator):
        content = "```\ncode1\n```\ntext\n```js\ncode2\n```"
        result = pdf_generator._sanitize_code_blocks(content)
        assert "```text" in result
        assert "```js" in result


class TestSanitizeUnicodeWhitespace:
    def test_replaces_nbsp(self, pdf_generator):
        content = "Test\u00a0Space"
        result = pdf_generator._sanitize_unicode_whitespace(content)
        assert result == "Test Space"

    def test_replaces_narrow_no_break_space(self, pdf_generator):
        content = "Test\u202fSpace"
        result = pdf_generator._sanitize_unicode_whitespace(content)
        assert result == "Test Space"

    def test_removes_zero_width_space(self, pdf_generator):
        content = "Test\u200bSpace"
        result = pdf_generator._sanitize_unicode_whitespace(content)
        assert result == "TestSpace"

    def test_removes_zero_width_non_joiner(self, pdf_generator):
        content = "Test\u200cSpace"
        result = pdf_generator._sanitize_unicode_whitespace(content)
        assert result == "TestSpace"

    def test_removes_zero_width_joiner(self, pdf_generator):
        content = "Test\u200dSpace"
        result = pdf_generator._sanitize_unicode_whitespace(content)
        assert result == "TestSpace"

    def test_removes_bom(self, pdf_generator):
        content = "\ufeffTest"
        result = pdf_generator._sanitize_unicode_whitespace(content)
        assert result == "Test"

    def test_preserves_newlines(self, pdf_generator):
        content = "Line1\nLine2\tTab"
        result = pdf_generator._sanitize_unicode_whitespace(content)
        assert "\n" in result
        assert "\t" in result

    def test_replaces_all_space_chars(self, pdf_generator):
        for char in ['\u2000', '\u2001', '\u2002', '\u2003', '\u2004',
                      '\u2005', '\u2006', '\u2007', '\u2008', '\u2009',
                      '\u200a', '\u205f', '\u3000']:
            content = f"Test{char}Space"
            result = pdf_generator._sanitize_unicode_whitespace(content)
            assert result == "Test Space", f"Failed for char {repr(char)}"


class TestSanitizeGreekCharacters:
    def test_lowercase_greek(self, pdf_generator):
        content = "The angle \u03b8 is important"
        result = pdf_generator._sanitize_greek_characters(content)
        assert "$\\theta$" in result

    def test_uppercase_greek(self, pdf_generator):
        content = "Sum \u03a3 of values"
        result = pdf_generator._sanitize_greek_characters(content)
        assert "$\\Sigma$" in result

    def test_pi(self, pdf_generator):
        content = "\u03c0 radius"
        result = pdf_generator._sanitize_greek_characters(content)
        assert "$\\pi$" in result

    def test_no_greek(self, pdf_generator):
        content = "No Greek characters here"
        result = pdf_generator._sanitize_greek_characters(content)
        assert result == content

    def test_all_greek_chars(self, pdf_generator):
        chars = {
            '\u03c6': r'$\phi$', '\u03b8': r'$\theta$', '\u03c0': r'$\pi$',
            '\u03b1': r'$\alpha$', '\u03b2': r'$\beta$', '\u03b3': r'$\gamma$',
            '\u03b4': r'$\delta$', '\u03b5': r'$\epsilon$', '\u03bb': r'$\lambda$',
            '\u03bc': r'$\mu$', '\u03c3': r'$\sigma$', '\u03c4': r'$\tau$',
            '\u03c9': r'$\omega$', '\u03a6': r'$\Phi$', '\u0398': r'$\Theta$',
            '\u03a0': r'$\Pi$', '\u0393': r'$\Gamma$', '\u0394': r'$\Delta$',
            '\u03a3': r'$\Sigma$', '\u03a9': r'$\Omega$',
        }
        for greek, latex in chars.items():
            result = pdf_generator._sanitize_greek_characters(greek)
            assert result == latex, f"Failed for {repr(greek)}"


class TestCopyToSafeTemp:
    def test_copy_to_safe_temp(self, pdf_generator, tmp_path):
        src = tmp_path / "source.md"
        src.write_text("Test content")
        with pdf_generator._copy_to_safe_temp(src) as safe_path:
            assert safe_path.exists()
            assert safe_path.read_text() == "Test content"
            assert safe_path.name == "input.md"


class TestBuildPandocCommand:
    def test_build_pandoc_command(self, pdf_generator, tmp_path):
        md_path = tmp_path / "test.md"
        pdf_path = tmp_path / "test.pdf"
        cmd = pdf_generator._build_pandoc_command(md_path, pdf_path, "tectonic")
        assert "pandoc" in cmd[0]
        assert "--pdf-engine=tectonic" in cmd
        assert "--toc" in cmd
        assert "--number-sections" in cmd


class TestExtractErrorMessage:
    def test_extract_error_with_stderr_bytes(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = b"Error: something went wrong"
        result = pdf_generator._extract_error_message(error)
        assert "something went wrong" in result

    def test_extract_error_with_stderr_str(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = "Error: something went wrong"
        result = pdf_generator._extract_error_message(error)
        assert "something went wrong" in result

    def test_extract_error_with_stdout_bytes(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = None
        error.stdout = b"Output error message"
        result = pdf_generator._extract_error_message(error)
        assert "Output error message" in result

    def test_extract_error_with_stdout_str(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = None
        error.stdout = "Output error message"
        result = pdf_generator._extract_error_message(error)
        assert "Output error message" in result

    def test_extract_error_no_output(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = None
        error.stdout = None
        error.returncode = 1
        result = pdf_generator._extract_error_message(error)
        # When no stderr/stdout, falls back to str(error)
        assert "non-zero" in result or "exit" in result

    def test_extract_error_permission_denied(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = "Permission denied"
        result = pdf_generator._extract_error_message(error)
        assert "Permission denied" in result

    def test_extract_error_no_such_file(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = "No such file or directory"
        result = pdf_generator._extract_error_message(error)
        assert "Missing file" in result

    def test_extract_error_cannot_find(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = "cannot find the file"
        result = pdf_generator._extract_error_message(error)
        assert "Missing file" in result

    def test_extract_error_undefined_control_sequence(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = "Undefined control sequence at line 5"
        result = pdf_generator._extract_error_message(error)
        assert "LaTeX syntax error" in result

    def test_extract_error_latex_error(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = "LaTeX Error: Something bad"
        result = pdf_generator._extract_error_message(error)
        assert "LaTeX compilation error" in result

    def test_extract_error_unicode_character(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = "Unicode character not found"
        result = pdf_generator._extract_error_message(error)
        assert "LaTeX compilation error" in result

    def test_extract_error_strips_pandoc_command(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = 'pandoc "input.md"\nReal error here'
        result = pdf_generator._extract_error_message(error)
        assert "Real error here" in result
        assert 'pandoc "input.md"' not in result

    def test_extract_error_strips_tectonic_command(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = 'tectonic "input.tex"\nReal error here'
        result = pdf_generator._extract_error_message(error)
        assert "Real error here" in result

    def test_extract_error_long_output_truncated(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = "x" * 1000
        result = pdf_generator._extract_error_message(error)
        assert len(result) <= 800

    def test_extract_error_empty_after_cleaning(self, pdf_generator):
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = 'pandoc "input.md"'
        result = pdf_generator._extract_error_message(error)
        assert "exit code 1" in result


class TestGeneratePDF:
    @patch('src.generators.pdf_generator.shutil.move')
    @patch('src.utils.subprocess_utils.capture_command_output')
    def test_generate_pdf_no_code_blocks_success(self, mock_capture, mock_move, pdf_generator, markdown_file, tmp_path):
        """Test successful PDF generation without code blocks."""
        pdf_path = tmp_path / "output.pdf"
        mock_result = Mock()
        mock_result.stdout = "pandoc 2.0"
        mock_capture.return_value = mock_result

        # Create a fake PDF file so shutil.move has something to move
        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator.generate_pdf(markdown_file, pdf_path)

        assert result.success is True

    def test_generate_pdf_file_not_found(self, pdf_generator, tmp_path):
        """Test PDF generation with non-existent markdown file."""
        pdf_path = tmp_path / "output.pdf"
        non_existent = tmp_path / "nonexistent.md"
        with pytest.raises(PDFGenerationError):
            pdf_generator.generate_pdf(non_existent, pdf_path)

    def test_generate_pdf_empty_file(self, pdf_generator, tmp_path):
        """Test PDF generation with empty markdown file."""
        md = tmp_path / "empty.md"
        md.write_text("")
        pdf_path = tmp_path / "output.pdf"
        with pytest.raises(PDFGenerationError):
            pdf_generator.generate_pdf(md, pdf_path)

    @patch('src.utils.subprocess_utils.capture_command_output')
    def test_generate_pdf_with_code_blocks_all_fallbacks_fail(self, mock_capture, pdf_generator, tmp_path):
        """Test PDF generation with code blocks where all engines fail."""
        md = tmp_path / "test.md"
        md.write_text("# Test\n\n```python\nprint('hello')\n```\n")
        pdf_path = tmp_path / "output.pdf"

        # Make all subprocess calls fail
        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        mock_capture.side_effect = error

        # Also make inkmd unavailable
        with patch.dict('sys.modules', {'inkmd': None}):
            with pytest.raises(PDFGenerationError):
                pdf_generator.generate_pdf(md, pdf_path)

    @patch('src.utils.subprocess_utils.capture_command_output')
    def test_generate_pdf_without_code_blocks_all_fallbacks_fail(self, mock_capture, pdf_generator, tmp_path):
        """Test PDF generation without code blocks where all engines fail."""
        md = tmp_path / "test.md"
        md.write_text("# Test\n\nRegular content\n")
        pdf_path = tmp_path / "output.pdf"

        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        mock_capture.side_effect = error

        with patch.dict('sys.modules', {'inkmd': None}):
            with pytest.raises(PDFGenerationError):
                pdf_generator.generate_pdf(md, pdf_path)

    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_generate_pdf_with_code_blocks_xelatex_stdin_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        """Test PDF generation with code blocks succeeds via xelatex stdin fallback."""
        md = tmp_path / "test.md"
        md.write_text("# Test\n\n```python\nprint('hello')\n```\n")
        pdf_path = tmp_path / "output.pdf"

        # First call (tectonic via stdin) fails, second (xelatex via stdin) succeeds
        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        success_result = Mock()
        success_result.stdout = "ok"
        mock_capture.side_effect = [error, success_result]

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator.generate_pdf(md, pdf_path)

        assert result.success is True
        assert result.metadata.get("via_stdin") is True

    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_generate_pdf_without_code_blocks_xelatex_engine_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        """Test PDF generation without code blocks succeeds via xelatex engine fallback."""
        md = tmp_path / "test.md"
        md.write_text("# Test\n\nRegular content\n")
        pdf_path = tmp_path / "output.pdf"

        # First call (tectonic) fails, second (xelatex) succeeds
        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        success_result = Mock()
        success_result.stdout = "ok"
        mock_capture.side_effect = [error, success_result]

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator.generate_pdf(md, pdf_path)

        assert result.success is True

    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_generate_pdf_with_code_blocks_stdin_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        """Test PDF generation with code blocks succeeds via stdin."""
        md = tmp_path / "test.md"
        md.write_text("# Test\n\n```python\nprint('hello')\n```\n")
        pdf_path = tmp_path / "output.pdf"

        # First call (tectonic via stdin) succeeds
        mock_result = Mock()
        mock_result.stdout = "ok"
        mock_capture.return_value = mock_result

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator.generate_pdf(md, pdf_path)

        assert result.success is True
        assert "stdin" in result.message.lower() or "via stdin" in result.metadata.get("via_stdin", "")

    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_generate_pdf_no_code_blocks_engine_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        """Test PDF generation without code blocks succeeds via engine."""
        md = tmp_path / "test.md"
        md.write_text("# Test\n\nRegular content\n")
        pdf_path = tmp_path / "output.pdf"

        mock_result = Mock()
        mock_result.stdout = "ok"
        mock_capture.return_value = mock_result

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator.generate_pdf(md, pdf_path)

        assert result.success is True


class TestGenerateFromStdin:
    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        pdf_path = tmp_path / "output.pdf"
        mock_result = Mock()
        mock_result.stdout = "ok"
        mock_capture.return_value = mock_result

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator._generate_from_stdin("content", pdf_path, "tectonic")

        assert result.success is True
        assert result.metadata["engine"] == "tectonic"

    @patch('src.utils.subprocess_utils.capture_command_output')
    def test_failure(self, mock_capture, pdf_generator, tmp_path):
        pdf_path = tmp_path / "output.pdf"
        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        mock_capture.side_effect = error

        with pytest.raises(PDFGenerationError):
            pdf_generator._generate_from_stdin("content", pdf_path, "tectonic")


class TestGenerateMinimalFromStdin:
    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_tectonic_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        pdf_path = tmp_path / "output.pdf"
        mock_result = Mock()
        mock_result.stdout = "ok"
        mock_capture.return_value = mock_result

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator._generate_minimal_from_stdin("content", pdf_path)

        assert result.success is True
        assert result.metadata["engine"] == "tectonic"

    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_xelatex_fallback_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        pdf_path = tmp_path / "output.pdf"
        # First call (tectonic) fails, second (xelatex) succeeds
        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        success_result = Mock()
        success_result.stdout = "ok"
        mock_capture.side_effect = [error, success_result]

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator._generate_minimal_from_stdin("content", pdf_path)

        assert result.success is True
        assert result.metadata["engine"] == "xelatex"

    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_default_latex_fallback_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        pdf_path = tmp_path / "output.pdf"
        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        success_result = Mock()
        success_result.stdout = "ok"
        mock_capture.side_effect = [error, error, success_result]

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator._generate_minimal_from_stdin("content", pdf_path)

        assert result.success is True
        assert result.metadata["engine"] == "default"

    @patch('src.utils.subprocess_utils.capture_command_output')
    def test_all_engines_fail(self, mock_capture, pdf_generator, tmp_path):
        pdf_path = tmp_path / "output.pdf"
        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        mock_capture.side_effect = error

        with pytest.raises(PDFGenerationError):
            pdf_generator._generate_minimal_from_stdin("content", pdf_path)

    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_outer_called_process_error(self, mock_move, mock_capture, pdf_generator, tmp_path):
        """Test outer CalledProcessError handler when shutil.move raises."""
        pdf_path = tmp_path / "output.pdf"
        mock_result = Mock()
        mock_result.stdout = "ok"
        mock_capture.return_value = mock_result
        # shutil.move raises CalledProcessError to hit outer except on line 393
        mock_move.side_effect = subprocess.CalledProcessError(1, "mv")

        with pytest.raises(PDFGenerationError):
            pdf_generator._generate_minimal_from_stdin("content", pdf_path)


class TestGenerateWithEngine:
    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("Test content")
        pdf_path = tmp_path / "output.pdf"

        mock_result = Mock()
        mock_result.stdout = "ok"
        mock_capture.return_value = mock_result

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator._generate_with_engine(md, pdf_path, "tectonic")

        assert result.success is True
        assert result.metadata["engine"] == "tectonic"

    @patch('src.utils.subprocess_utils.capture_command_output')
    def test_failure(self, mock_capture, pdf_generator, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("Test content")
        pdf_path = tmp_path / "output.pdf"

        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        mock_capture.side_effect = error

        with pytest.raises(PDFGenerationError):
            pdf_generator._generate_with_engine(md, pdf_path, "tectonic")


class TestGenerateWithoutHeader:
    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("Test content")
        pdf_path = tmp_path / "output.pdf"

        mock_result = Mock()
        mock_result.stdout = "ok"
        mock_capture.return_value = mock_result

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator._generate_without_header(md, pdf_path, "tectonic")

        assert result.success is True
        assert result.metadata["no_header"] is True

    @patch('src.utils.subprocess_utils.capture_command_output')
    def test_failure(self, mock_capture, pdf_generator, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("Test content")
        pdf_path = tmp_path / "output.pdf"

        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        mock_capture.side_effect = error

        with pytest.raises(PDFGenerationError):
            pdf_generator._generate_without_header(md, pdf_path, "tectonic")


class TestGenerateMinimalFallback:
    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_xelatex_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("Test content")
        pdf_path = tmp_path / "output.pdf"

        mock_result = Mock()
        mock_result.stdout = "ok"
        mock_capture.return_value = mock_result

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator._generate_minimal_fallback(md, pdf_path)

        assert result.success is True
        assert result.metadata["engine"] == "xelatex"

    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_tectonic_fallback_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("Test content")
        pdf_path = tmp_path / "output.pdf"

        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        success = Mock()
        success.stdout = "ok"
        mock_capture.side_effect = [error, success]

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator._generate_minimal_fallback(md, pdf_path)

        assert result.success is True
        assert result.metadata["engine"] == "tectonic"

    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_default_latex_fallback_success(self, mock_move, mock_capture, pdf_generator, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("Test content")
        pdf_path = tmp_path / "output.pdf"

        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        success = Mock()
        success.stdout = "ok"
        mock_capture.side_effect = [error, error, success]

        with patch('src.generators.pdf_generator.tempfile.TemporaryDirectory') as mock_tmp:
            tmp_dir = tmp_path / "tmpdir"
            tmp_dir.mkdir()
            (tmp_dir / "output.pdf").write_bytes(b"%PDF-1.4")
            mock_tmp.return_value.__enter__.return_value = str(tmp_dir)
            mock_tmp.return_value.__exit__.return_value = None

            result = pdf_generator._generate_minimal_fallback(md, pdf_path)

        assert result.success is True
        assert result.metadata["engine"] == "default"

    @patch('src.utils.subprocess_utils.capture_command_output')
    def test_all_fail(self, mock_capture, pdf_generator, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("Test content")
        pdf_path = tmp_path / "output.pdf"

        error = subprocess.CalledProcessError(1, "pandoc")
        error.stderr = b"Error"
        error.stdout = None
        mock_capture.side_effect = error

        with pytest.raises(PDFGenerationError):
            pdf_generator._generate_minimal_fallback(md, pdf_path)

    @patch('src.utils.subprocess_utils.capture_command_output')
    @patch('src.generators.pdf_generator.shutil.move')
    def test_outer_called_process_error(self, mock_move, mock_capture, pdf_generator, tmp_path):
        """Test outer CalledProcessError handler when shutil.move raises."""
        md = tmp_path / "test.md"
        md.write_text("Test content")
        pdf_path = tmp_path / "output.pdf"

        mock_result = Mock()
        mock_result.stdout = "ok"
        mock_capture.return_value = mock_result
        mock_move.side_effect = subprocess.CalledProcessError(1, "mv")

        with pytest.raises(PDFGenerationError):
            pdf_generator._generate_minimal_fallback(md, pdf_path)


class TestGenerateWithInkmd:
    def test_inkmd_not_installed(self, pdf_generator, tmp_path):
        pdf_path = tmp_path / "output.pdf"
        with patch.dict('sys.modules', {'inkmd': None}):
            with pytest.raises(PDFGenerationError) as exc_info:
                pdf_generator._generate_with_inkmd("content", pdf_path)
            assert "inkmd is not installed" in str(exc_info.value)

    def test_inkmd_success(self, pdf_generator, tmp_path):
        pdf_path = tmp_path / "output.pdf"
        mock_inkmd = Mock()
        mock_inkmd.compile.return_value = b"%PDF-1.4 fake pdf bytes"
        with patch.dict('sys.modules', {'inkmd': mock_inkmd}):
            result = pdf_generator._generate_with_inkmd("content", pdf_path)
        assert result.success is True
        assert result.metadata["engine"] == "inkmd"
        assert pdf_path.exists()

    def test_inkmd_failure(self, pdf_generator, tmp_path):
        pdf_path = tmp_path / "output.pdf"
        mock_inkmd = Mock()
        mock_inkmd.compile.side_effect = Exception("inkmd error")
        with patch.dict('sys.modules', {'inkmd': mock_inkmd}):
            with pytest.raises(PDFGenerationError):
                pdf_generator._generate_with_inkmd("content", pdf_path)


class TestValidateDependencies:
    @patch('src.utils.subprocess_utils.run_silent_command')
    def test_all_available(self, mock_run, pdf_generator):
        mock_run.return_value = Mock(returncode=0)
        assert pdf_generator.validate_dependencies() is True

    @patch('src.utils.subprocess_utils.run_silent_command')
    def test_pandoc_missing(self, mock_run, pdf_generator):
        mock_run.side_effect = FileNotFoundError("pandoc not found")
        assert pdf_generator.validate_dependencies() is False

    @patch('src.utils.subprocess_utils.run_silent_command')
    def test_tectonic_missing(self, mock_run, pdf_generator):
        # First call (pandoc) succeeds, second (tectonic) fails
        mock_run.side_effect = [Mock(returncode=0), FileNotFoundError("tectonic not found")]
        assert pdf_generator.validate_dependencies() is False

    @patch('src.utils.subprocess_utils.run_silent_command')
    def test_pandoc_called_process_error(self, mock_run, pdf_generator):
        mock_run.side_effect = subprocess.CalledProcessError(1, "pandoc")
        assert pdf_generator.validate_dependencies() is False

    @patch('src.utils.subprocess_utils.run_silent_command')
    def test_tectonic_called_process_error(self, mock_run, pdf_generator):
        mock_run.side_effect = [Mock(returncode=0), subprocess.CalledProcessError(1, "tectonic")]
        assert pdf_generator.validate_dependencies() is False


class TestGetDependencyInfo:
    @patch('src.utils.subprocess_utils.run_silent_command')
    @patch('src.utils.subprocess_utils.capture_command_output')
    def test_all_available(self, mock_capture, mock_run, pdf_generator):
        mock_capture.return_value = Mock(stdout="pandoc 2.19")
        mock_run.return_value = Mock(returncode=0)
        with patch.dict('sys.modules', {'inkmd': Mock(__version__='0.5.0')}):
            info = pdf_generator.get_dependency_info()
        assert info["pandoc"] is True
        assert "tectonic" in info["latex_engines"]
        assert info["inkmd"] is True

    @patch('src.utils.subprocess_utils.run_silent_command')
    @patch('src.utils.subprocess_utils.capture_command_output')
    def test_pandoc_missing(self, mock_capture, mock_run, pdf_generator):
        mock_capture.side_effect = FileNotFoundError("pandoc not found")
        mock_run.side_effect = FileNotFoundError("tectonic not found")
        with patch.dict('sys.modules', {'inkmd': None}):
            info = pdf_generator.get_dependency_info()
        assert info["pandoc"] is False
        assert info["latex_engines"] == []
        assert info["inkmd"] is False

    @patch('src.utils.subprocess_utils.capture_command_output')
    def test_pandoc_called_process_error(self, mock_capture, pdf_generator):
        mock_capture.side_effect = subprocess.CalledProcessError(1, "pandoc")
        with patch('src.utils.subprocess_utils.run_silent_command', side_effect=subprocess.CalledProcessError(1, "tectonic")):
            with patch.dict('sys.modules', {'inkmd': None}):
                info = pdf_generator.get_dependency_info()
        assert info["pandoc"] is False
        assert info["latex_engines"] == []
