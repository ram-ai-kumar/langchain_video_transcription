"""PDF generator for converting markdown to PDF using Pandoc and Tectonic."""

import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List

from src.core.config import PipelineConfig
from src.core.exceptions import PDFGenerationError
from src.processors.base import ProcessResult


class PDFGenerator:
    """Handles PDF generation using Pandoc and Tectonic."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.header_path = config.header_file

    def generate_pdf(self, markdown_path: Path, pdf_path: Path) -> ProcessResult:
        """Convert markdown file to PDF using Pandoc."""
        try:
            # Validate input path exists
            if not markdown_path.exists():
                raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

            # Resolve paths to absolute to avoid relative path issues
            markdown_abs = markdown_path.resolve()
            pdf_abs = pdf_path.resolve()

            # Verify file is readable and sanitize if needed
            try:
                with open(markdown_abs, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content.strip():
                        raise ValueError("Markdown file is empty")
                    # Sanitize Unicode whitespace to prevent pandoc errors
                    content = self._sanitize_unicode_whitespace(content)
                    # Sanitize Greek characters to LaTeX math mode
                    content = self._sanitize_greek_characters(content)
                    # Check if content has code blocks
                    has_code_blocks = '```' in content
                    # Sanitize code blocks to prevent LaTeX errors
                    content = self._sanitize_code_blocks(content)
            except Exception as e:
                raise FileNotFoundError(f"Cannot read markdown file: {e}")

            # Create output directory
            pdf_abs.parent.mkdir(parents=True, exist_ok=True)

            # If file has code blocks, use stdin approach without header to avoid LaTeX errors
            if has_code_blocks:
                # Try with tectonic engine first (without header, via stdin)
                try:
                    result = self._generate_from_stdin(content, pdf_abs, "tectonic")
                    if result.success:
                        return result
                except PDFGenerationError:
                    pass

                # Try with xelatex as fallback (better Unicode support, without header, via stdin)
                try:
                    result = self._generate_from_stdin(content, pdf_abs, "xelatex")
                    if result.success:
                        return result
                except PDFGenerationError:
                    pass

                # Fallback to minimal configuration with tectonic (via stdin)
                return self._generate_minimal_from_stdin(content, pdf_abs)
            else:
                # No code blocks - use original file-based approach with header for colors
                # Try with xelatex first (better LaTeX compatibility)
                try:
                    result = self._generate_with_engine(markdown_abs, pdf_abs, "xelatex")
                    if result.success:
                        return result
                except PDFGenerationError:
                    pass

                # Try with tectonic as fallback
                try:
                    result = self._generate_with_engine(markdown_abs, pdf_abs, "tectonic")
                    if result.success:
                        return result
                except PDFGenerationError:
                    pass

                # Fallback to minimal configuration
                try:
                    return self._generate_minimal_fallback(markdown_abs, pdf_abs)
                except PDFGenerationError:
                    pass

                # Final fallback: use stdin approach (no colors, but more compatible)
                return self._generate_minimal_from_stdin(content, pdf_abs)

        except Exception as e:
            raise PDFGenerationError(
                f"Failed to generate PDF from {markdown_path.name}: {e}",
                processor="PDFGenerator"
            )

    def _sanitize_path(self, path: Path) -> Path:
        """Sanitize path for compatibility with external tools like Tectonic.

        Replaces all space-like Unicode characters (e.g. \u202f, \u00a0)
        with standard spaces.
        """
        path_str = str(path)
        # Handle all space-like Unicode characters which tectonic often chokes on in paths
        sanitized = re.sub(r'\s', ' ', path_str)

        if sanitized != path_str:
            return Path(sanitized)
        return path

    @contextmanager
    def _copy_to_safe_temp(self, markdown_path: Path) -> Generator[Path, None, None]:
        """Copy markdown to a temp dir with an ASCII-safe filename.

        Tectonic (and some xelatex builds) cannot handle non-ASCII Unicode
        characters in the input file-system path. Copying to a temp dir
        with a plain name sidesteps the issue.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            safe_input = Path(tmpdir) / "input.md"
            shutil.copy2(str(markdown_path), str(safe_input))
            yield safe_input

    def _sanitize_code_blocks(self, content: str) -> str:
        """Sanitize markdown code blocks to prevent LaTeX compilation errors.

        Adds language specifiers to code blocks that don't have them,
        which helps tectonic/xelatex handle them better.
        """
        import re
        lines = content.split('\n')
        result = []
        in_code_block = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('```'):
                if not in_code_block:
                    # Opening tag
                    in_code_block = True
                    if stripped == '```':
                        # No language specifier, use 'text'
                        result.append('```text')
                    else:
                        # Already has a language specifier
                        result.append(line)
                else:
                    # Closing tag
                    in_code_block = False
                    result.append(line)  # Keep closing tag as-is
            else:
                result.append(line)

        return '\n'.join(result)

    def _sanitize_unicode_whitespace(self, content: str) -> str:
        """Sanitize problematic Unicode whitespace characters in markdown content.

        Replaces all space-like Unicode characters (e.g. \u202f, \u00a0, \t)
        with standard spaces to prevent pandoc LaTeX engine errors.
        """
        import re
        # Replace all Unicode whitespace characters with standard spaces
        sanitized = re.sub(r'\s', ' ', content)
        return sanitized

    def _sanitize_greek_characters(self, content: str) -> str:
        """Sanitize Greek Unicode characters by wrapping in LaTeX math mode.

        Converts standalone Greek characters (φ, θ, π, etc.) to LaTeX math mode
        to prevent font rendering errors when fonts don't support them.
        """
        import re
        
        # Common Greek characters that cause LaTeX font errors
        greek_to_latex = {
            'φ': r'$\phi$',
            'θ': r'$\theta$',
            'π': r'$\pi$',
            'α': r'$\alpha$',
            'β': r'$\beta$',
            'γ': r'$\gamma$',
            'δ': r'$\delta$',
            'ε': r'$\epsilon$',
            'λ': r'$\lambda$',
            'μ': r'$\mu$',
            'σ': r'$\sigma$',
            'τ': r'$\tau$',
            'ω': r'$\omega$',
            'Φ': r'$\Phi$',
            'Θ': r'$\Theta$',
            'Π': r'$\Pi$',
            'Γ': r'$\Gamma$',
            'Δ': r'$\Delta$',
            'Σ': r'$\Sigma$',
            'Ω': r'$\Omega$',
        }
        
        # Replace each Greek character with its LaTeX equivalent
        for greek_char, latex_equiv in greek_to_latex.items():
            content = content.replace(greek_char, latex_equiv)
        
        return content

    def _generate_from_stdin(self, content: str, pdf_path: Path, engine: str) -> ProcessResult:
        """Generate PDF from content via stdin to avoid file system issues."""
        try:
            from src.utils.subprocess_utils import capture_command_output

            pdf_abs = pdf_path.resolve()

            with tempfile.TemporaryDirectory() as tmpdir:
                temp_pdf = Path(tmpdir) / "output.pdf"

                cmd = [
                    "pandoc",
                    "-o", str(temp_pdf),
                    "--from", "markdown+lists_without_preceding_blankline",
                    f"--pdf-engine={engine}",
                    "--variable", "fontsize=12pt",
                    "--variable", "mainfont=Arial",
                    "--variable", "sansfont=Arial",
                    "--toc",
                    "--toc-depth=3",
                    "--number-sections",
                    "--wrap=none",
                    "--standalone",
                    "--fail-if-warnings=false",
                ]

                # Pass content via stdin (encode as bytes)
                result = capture_command_output(cmd, input=content.encode('utf-8'))
                shutil.move(str(temp_pdf), str(pdf_abs))

            return ProcessResult(
                success=True,
                output_path=pdf_abs,
                message=f"Successfully generated PDF using {engine} via stdin",
                metadata={
                    "engine": engine,
                    "pdf_file": str(pdf_abs),
                    "via_stdin": True
                }
            )

        except subprocess.CalledProcessError as e:
            raise PDFGenerationError(
                f"PDF generation failed with {engine} (via stdin): {self._extract_error_message(e)}",
                processor="PDFGenerator"
            )

    def _generate_minimal_from_stdin(self, content: str, pdf_path: Path) -> ProcessResult:
        """Try minimal PDF generation from content via stdin without header."""
        try:
            from src.utils.subprocess_utils import capture_command_output

            pdf_abs = pdf_path.resolve()

            # First try with tectonic
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    temp_pdf = Path(tmpdir) / "output.pdf"
                    cmd = [
                        "pandoc",
                        "-o", str(temp_pdf),
                        "--from", "markdown+lists_without_preceding_blankline",
                        "--pdf-engine=tectonic",
                        "--variable", "fontsize=12pt",
                        "--variable", "mainfont=Arial",
                        "--variable", "sansfont=Arial",
                        "--wrap=none",
                        "--standalone",
                        "--fail-if-warnings=false",
                    ]
                    capture_command_output(cmd, input=content.encode('utf-8'))
                    shutil.move(str(temp_pdf), str(pdf_abs))

                return ProcessResult(
                    success=True,
                    output_path=pdf_abs,
                    message="Generated PDF with minimal configuration (tectonic via stdin)",
                    metadata={"fallback_mode": True, "engine": "tectonic", "via_stdin": True}
                )
            except subprocess.CalledProcessError as e:
                # Try with xelatex instead
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        temp_pdf = Path(tmpdir) / "output.pdf"
                        cmd = [
                            "pandoc",
                            "-o", str(temp_pdf),
                            "--from", "markdown+lists_without_preceding_blankline",
                            "--pdf-engine=xelatex",
                            "--variable", "fontsize=12pt",
                            "--variable", "mainfont=Arial",
                            "--variable", "sansfont=Arial",
                            "--wrap=none",
                            "--standalone",
                            "--fail-if-warnings=false",
                        ]
                        capture_command_output(cmd, input=content.encode('utf-8'))
                        shutil.move(str(temp_pdf), str(pdf_abs))

                    return ProcessResult(
                        success=True,
                        output_path=pdf_abs,
                        message="Generated PDF with minimal configuration (xelatex via stdin)",
                        metadata={"fallback_mode": True, "engine": "xelatex", "via_stdin": True}
                    )
                except subprocess.CalledProcessError as e2:
                    # Try with default latex engine as last resort
                    try:
                        with tempfile.TemporaryDirectory() as tmpdir:
                            temp_pdf = Path(tmpdir) / "output.pdf"
                            cmd = [
                                "pandoc",
                                "-o", str(temp_pdf),
                                "--from", "gfm",
                                "--variable", "fontsize=12pt",
                                "--variable", "mainfont=Arial",
                                "--variable", "sansfont=Arial",
                                "--wrap=none",
                                "--standalone",
                                "--fail-if-warnings=false",
                            ]
                            capture_command_output(cmd, input=content.encode('utf-8'))
                            shutil.move(str(temp_pdf), str(pdf_abs))

                        return ProcessResult(
                            success=True,
                            output_path=pdf_abs,
                            message="Generated PDF with minimal configuration (default latex via stdin)",
                            metadata={"fallback_mode": True, "engine": "default", "via_stdin": True}
                        )
                    except subprocess.CalledProcessError as e3:
                        # If all fail, raise the original error
                        raise PDFGenerationError(
                            f"Minimal PDF generation failed (tectonic, xelatex, and default via stdin): {self._extract_error_message(e)}",
                            processor="PDFGenerator"
                        )

        except subprocess.CalledProcessError as e:
            raise PDFGenerationError(
                f"Minimal PDF generation also failed (via stdin): {self._extract_error_message(e)}",
                processor="PDFGenerator"
            )

    def _generate_without_header(self, markdown_path: Path, pdf_path: Path, engine: str) -> ProcessResult:
        """Generate PDF without header file to isolate header-related issues."""
        try:
            from src.utils.subprocess_utils import capture_command_output

            with tempfile.TemporaryDirectory() as tmpdir:
                temp_pdf = Path(tmpdir) / "output.pdf"
                markdown_abs = markdown_path.resolve()
                pdf_abs = pdf_path.resolve()

                cmd = [
                    "pandoc",
                    str(markdown_abs),
                    "-o", str(temp_pdf),
                    "--from", "markdown+lists_without_preceding_blankline",
                    f"--pdf-engine={engine}",
                    "--variable", "fontsize=12pt",
                    "--variable", "mainfont=Arial",
                    "--variable", "sansfont=Arial",
                    "--toc",
                    "--toc-depth=3",
                    "--number-sections",
                    "--wrap=none",
                    "--standalone",
                    "--fail-if-warnings=false",
                ]
                capture_command_output(cmd, text=True)
                shutil.move(str(temp_pdf), str(pdf_abs))

            return ProcessResult(
                success=True,
                output_path=pdf_abs,
                message=f"Successfully generated PDF using {engine} without header",
                metadata={
                    "engine": engine,
                    "markdown_file": str(markdown_abs),
                    "pdf_file": str(pdf_abs),
                    "no_header": True
                }
            )

        except subprocess.CalledProcessError as e:
            raise PDFGenerationError(
                f"PDF generation failed with {engine} (no header): {self._extract_error_message(e)}",
                processor="PDFGenerator"
            )

    def _generate_with_engine(self, markdown_path: Path, pdf_path: Path, engine: str) -> ProcessResult:
        """Generate PDF using specific LaTeX engine."""
        try:
            from src.utils.subprocess_utils import capture_command_output

            with self._copy_to_safe_temp(markdown_path) as safe_input:
                with tempfile.TemporaryDirectory() as tmpdir:
                    temp_pdf = Path(tmpdir) / "output.pdf"
                    cmd = self._build_pandoc_command(safe_input, temp_pdf, engine)
                    capture_command_output(cmd, text=True)
                    shutil.move(str(temp_pdf), str(pdf_path))

            return ProcessResult(
                success=True,
                output_path=pdf_path,
                message=f"Successfully generated PDF using {engine}",
                metadata={
                    "engine": engine,
                    "markdown_file": str(markdown_path),
                    "pdf_file": str(pdf_path),
                }
            )

        except subprocess.CalledProcessError as e:
            raise PDFGenerationError(
                f"PDF generation failed with {engine}: {self._extract_error_message(e)}",
                processor="PDFGenerator"
            )

    def _build_pandoc_command(self, markdown_path: Path, pdf_path: Path, engine: str) -> List[str]:
        """Build Pandoc command for the specified engine."""
        return [
            "pandoc",
            str(self._sanitize_path(markdown_path)),
            "-o", str(self._sanitize_path(pdf_path)),
            "--from", "markdown+lists_without_preceding_blankline",
            f"--pdf-engine={engine}",
            f"--include-in-header={str(self._sanitize_path(self.header_path))}",
            "--variable", "fontsize=12pt",
            "--toc",
            "--toc-depth=3",
            "--number-sections",
            "--fail-if-warnings=false",
            "--log=INFO",
        ]

    def _generate_minimal_fallback(self, markdown_path: Path, pdf_path: Path) -> ProcessResult:
        """Try minimal PDF generation without header and fancy options."""
        try:
            from src.utils.subprocess_utils import capture_command_output

            with self._copy_to_safe_temp(markdown_path) as safe_input:
                # First try with xelatex (better LaTeX compatibility)
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        temp_pdf = Path(tmpdir) / "output.pdf"
                        cmd = [
                            "pandoc",
                            str(safe_input),
                            "-o", str(temp_pdf),
                            "--from", "markdown+lists_without_preceding_blankline",
                            "--pdf-engine=xelatex",
                            "--variable", "fontsize=12pt",
                            "--variable", "mainfont=Arial",
                            "--variable", "sansfont=Arial",
                            "--fail-if-warnings=false",
                        ]
                        capture_command_output(cmd)
                        shutil.move(str(temp_pdf), str(pdf_path))

                    return ProcessResult(
                        success=True,
                        output_path=pdf_path,
                        message="Generated PDF with minimal configuration (xelatex)",
                        metadata={"fallback_mode": True, "engine": "xelatex"}
                    )
                except subprocess.CalledProcessError as e:
                    # Try with tectonic as fallback
                    try:
                        with tempfile.TemporaryDirectory() as tmpdir:
                            temp_pdf = Path(tmpdir) / "output.pdf"
                            cmd = [
                                "pandoc",
                                str(safe_input),
                                "-o", str(temp_pdf),
                                "--from", "markdown+lists_without_preceding_blankline",
                                "--pdf-engine=tectonic",
                                "--variable", "fontsize=12pt",
                                "--variable", "mainfont=Arial",
                                "--variable", "sansfont=Arial",
                                "--fail-if-warnings=false",
                            ]
                            capture_command_output(cmd)
                            shutil.move(str(temp_pdf), str(pdf_path))

                        return ProcessResult(
                            success=True,
                            output_path=pdf_path,
                            message="Generated PDF with minimal configuration (tectonic)",
                            metadata={"fallback_mode": True, "engine": "tectonic"}
                        )
                    except subprocess.CalledProcessError as e2:
                        # Try with default latex engine as last resort
                        try:
                            with tempfile.TemporaryDirectory() as tmpdir:
                                temp_pdf = Path(tmpdir) / "output.pdf"
                                cmd = [
                                    "pandoc",
                                    str(safe_input),
                                    "-o", str(temp_pdf),
                                    "--from", "markdown",
                                    "--variable", "fontsize=12pt",
                                    "--variable", "mainfont=Arial",
                                    "--variable", "sansfont=Arial",
                                    "--fail-if-warnings=false",
                                ]
                                capture_command_output(cmd)
                                shutil.move(str(temp_pdf), str(pdf_path))

                            return ProcessResult(
                                success=True,
                                output_path=pdf_path,
                                message="Generated PDF with minimal configuration (default latex)",
                                metadata={"fallback_mode": True, "engine": "default"}
                            )
                        except subprocess.CalledProcessError as e3:
                            # If all fail, raise the original error
                            raise PDFGenerationError(
                                f"Minimal PDF generation failed (xelatex, tectonic, and default): {self._extract_error_message(e)}",
                                processor="PDFGenerator"
                            )

        except subprocess.CalledProcessError as e:
            raise PDFGenerationError(
                f"Minimal PDF generation also failed: {self._extract_error_message(e)}",
                processor="PDFGenerator"
            )

    def _extract_error_message(self, error: subprocess.CalledProcessError) -> str:
        """Extract meaningful error message from subprocess error."""
        # Get the raw error output
        if error.stderr:
            error_output = error.stderr.decode('utf-8') if isinstance(error.stderr, bytes) else error.stderr
        elif error.stdout:
            error_output = error.stdout.decode('utf-8') if isinstance(error.stdout, bytes) else error.stdout
        else:
            error_output = str(error)

        # Clean up error output - remove only the most obvious command lines
        # Keep most error details for debugging
        lines = error_output.split('\n')
        cleaned_lines = []
        for line in lines:
            line_stripped = line.strip()
            # Skip only exact command invocations at the start of lines
            if line_stripped and (line_stripped.startswith('pandoc "') or line_stripped.startswith('tectonic "')):
                continue
            # Keep everything else including error messages
            if line_stripped:
                cleaned_lines.append(line_stripped)

        error_output = '\n'.join(cleaned_lines).strip()

        # If we ended up with nothing after cleaning, provide a generic message
        if not error_output:
            return f"Command failed with exit code {error.returncode}"

        if "Permission denied" in error_output:
            return "Permission denied - check write permissions"
        elif "No such file" in error_output or "cannot find" in error_output.lower():
            return "Missing file or directory"
        elif "Undefined control sequence" in error_output:
            return "LaTeX syntax error in markdown file"
        elif "LaTeX Error" in error_output or "Unicode character" in error_output:
            return "LaTeX compilation error"
        else:
            # Return last 800 chars to see more of the actual error
            return error_output[-800:] if len(error_output) > 800 else error_output

    def validate_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        try:
            from src.utils.subprocess_utils import run_silent_command
            run_silent_command(["pandoc", "--version"])
            try:
                run_silent_command(["tectonic", "--version"])
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_dependency_info(self) -> dict:
        """Get information about available dependencies."""
        info = {"pandoc": False, "latex_engines": []}

        try:
            from src.utils.subprocess_utils import capture_command_output
            result = capture_command_output(["pandoc", "--version"], text=True)
            info["pandoc"] = True
            info["pandoc_version"] = result.stdout.split('\n')[0] if result.stdout else "Unknown"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        try:
            from src.utils.subprocess_utils import run_silent_command
            run_silent_command(["tectonic", "--version"])
            info["latex_engines"].append("tectonic")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return info
