"""PDF generator for converting markdown to PDF using Pandoc."""

import subprocess
from pathlib import Path
from typing import List, Optional

from src.core.config import PipelineConfig
from src.core.exceptions import PDFGenerationError
from src.processors.base import ProcessResult


class PDFGenerator:
    """Handles PDF generation using Pandoc and LaTeX."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.header_path = config.header_file
    
    def generate_pdf(self, markdown_path: Path, pdf_path: Path) -> ProcessResult:
        """Convert markdown file to PDF using Pandoc."""
        try:
            if not markdown_path.exists():
                raise FileNotFoundError(f"Markdown file not found: {markdown_path}")
            
            # Ensure output directory exists
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Try different LaTeX engines in order of preference
            engines = ["xelatex", "pdflatex"]
            
            for engine in engines:
                try:
                    result = self._generate_with_engine(markdown_path, pdf_path, engine)
                    if result.success:
                        return result
                except PDFGenerationError:
                    # Try next engine
                    continue
            
            # If all engines failed, try minimal fallback
            return self._generate_minimal_fallback(markdown_path, pdf_path)
            
        except Exception as e:
            raise PDFGenerationError(
                f"Failed to generate PDF from {markdown_path.name}: {e}",
                processor="PDFGenerator"
            )
    
    def _generate_with_engine(self, markdown_path: Path, pdf_path: Path, engine: str) -> ProcessResult:
        """Generate PDF using specific LaTeX engine."""
        try:
            cmd = self._build_pandoc_command(markdown_path, pdf_path, engine)
            
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            
            return ProcessResult(
                success=True,
                output_path=pdf_path,
                message=f"Successfully generated PDF using {engine}",
                metadata={
                    "engine": engine,
                    "markdown_file": str(markdown_path),
                    "pdf_file": str(pdf_path)
                }
            )
            
        except subprocess.CalledProcessError as e:
            error_msg = self._extract_error_message(e)
            raise PDFGenerationError(
                f"PDF generation failed with {engine}: {error_msg}",
                processor="PDFGenerator"
            )
    
    def _build_pandoc_command(self, markdown_path: Path, pdf_path: Path, engine: str) -> List[str]:
        """Build Pandoc command for the specified engine."""
        base_cmd = [
            "pandoc",
            str(markdown_path),
            "-o", str(pdf_path),
            f"--pdf-engine={engine}",
            f"--include-in-header={str(self.header_path)}",
            "--variable", "fontsize=12pt",
            "--toc",
            "--toc-depth=3",
            "--number-sections",
            "--fail-if-warnings=false",
            "--log=INFO",
            "--pdf-engine-opt=-interaction=nonstopmode",
            "--pdf-engine-opt=-shell-escape"
        ]
        
        return base_cmd
    
    def _generate_minimal_fallback(self, markdown_path: Path, pdf_path: Path) -> ProcessResult:
        """Try minimal PDF generation without header and fancy options."""
        try:
            cmd = [
                "pandoc",
                str(markdown_path),
                "-o", str(pdf_path),
                "--pdf-engine=pdflatex",
                "--variable", "fontsize=12pt",
                "--fail-if-warnings=false",
                "--pdf-engine-opt=-interaction=nonstopmode"
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            return ProcessResult(
                success=True,
                output_path=pdf_path,
                message="Generated PDF with minimal configuration",
                metadata={"fallback_mode": True}
            )
            
        except subprocess.CalledProcessError as e:
            raise PDFGenerationError(
                f"Minimal PDF generation also failed: {self._extract_error_message(e)}",
                processor="PDFGenerator"
            )
    
    def _extract_error_message(self, error: subprocess.CalledProcessError) -> str:
        """Extract meaningful error message from subprocess error."""
        if error.stderr:
            error_output = error.stderr
        elif error.stdout:
            error_output = error.stdout
        else:
            error_output = str(error)
        
        # Look for specific error patterns
        if "Permission denied" in error_output:
            return "Permission denied - check write permissions"
        elif "No such file" in error_output or "cannot find" in error_output.lower():
            return "Missing file or directory"
        elif "Undefined control sequence" in error_output:
            return "LaTeX syntax error in markdown file"
        elif "LaTeX Error" in error_output or "Unicode character" in error_output:
            return "LaTeX compilation error"
        else:
            # Return last 500 characters of error output
            return error_output[-500:] if len(error_output) > 500 else error_output
    
    def validate_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        try:
            # Check if pandoc is available
            subprocess.run(["pandoc", "--version"], check=True, capture_output=True)
            
            # Check if at least one LaTeX engine is available
            engines = ["xelatex", "pdflatex"]
            for engine in engines:
                try:
                    subprocess.run([engine, "--version"], check=True, capture_output=True)
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            
            return False
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_dependency_info(self) -> dict:
        """Get information about available dependencies."""
        info = {"pandoc": False, "latex_engines": []}
        
        # Check pandoc
        try:
            result = subprocess.run(["pandoc", "--version"], check=True, capture_output=True, text=True)
            info["pandoc"] = True
            info["pandoc_version"] = result.stdout.split('\n')[0] if result.stdout else "Unknown"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Check LaTeX engines
        engines = ["xelatex", "pdflatex", "lualatex"]
        for engine in engines:
            try:
                subprocess.run([engine, "--version"], check=True, capture_output=True)
                info["latex_engines"].append(engine)
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        return info
