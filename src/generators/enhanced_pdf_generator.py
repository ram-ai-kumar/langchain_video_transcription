"""Enhanced PDF generator with AI content marking."""

import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.core.config import PipelineConfig
from src.core.exceptions import PDFGenerationError
from src.domain.ai_marking import AIMarkingConfig, AuthorInfo, WatermarkConfig
from src.generators.pdf_generator import PDFGenerator
from src.processors.base import ProcessResult


class EnhancedPDFGenerator(PDFGenerator):
    """Enhanced PDF generator with AI content marking."""

    def __init__(self, config: PipelineConfig, ai_marking_config: Optional[AIMarkingConfig] = None):
        super().__init__(config)
        self.ai_marking_config = ai_marking_config or AIMarkingConfig.create_default()

    def generate_pdf(self, markdown_path: Path, pdf_path: Path) -> ProcessResult:
        """Generate PDF with AI content marking."""
        try:
            # Create temporary markdown with AI marking
            marked_markdown_path = self._add_ai_marking_to_markdown(markdown_path)

            # Create enhanced header with watermarking and attribution
            enhanced_header_path = self._create_enhanced_header()

            try:
                # Generate PDF with enhanced features
                result = self._generate_with_enhanced_features(
                    marked_markdown_path, pdf_path, enhanced_header_path
                )

                return ProcessResult(
                    success=True,
                    output_path=pdf_path,
                    message="Successfully generated AI-marked PDF",
                    metadata={
                        "ai_marked": True,
                        "watermark_enabled": self.ai_marking_config.enable_watermark,
                        "attribution_enabled": self.ai_marking_config.enable_attribution,
                        "acknowledgment_enabled": self.ai_marking_config.enable_acknowledgment,
                        "author": self.ai_marking_config.author_info.name
                    }
                )

            finally:
                # Clean up temporary files
                if marked_markdown_path.exists():
                    marked_markdown_path.unlink()
                if enhanced_header_path.exists():
                    enhanced_header_path.unlink()

        except Exception as e:
            # Return failure result instead of raising exception to allow fallback
            return ProcessResult(
                success=False,
                output_path=pdf_path,
                message=f"Enhanced PDF generation failed: {e}",
                metadata={"enhanced_failed": True, "error": str(e)}
            )

    def _add_ai_marking_to_markdown(self, markdown_path: Path) -> Path:
        """Add AI marking content to markdown file."""
        try:
            # Read original markdown
            with open(markdown_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Create enhanced content
            enhanced_content = original_content

            # Add acknowledgment page if enabled
            if self.ai_marking_config.enable_acknowledgment:
                acknowledgment_content = self._generate_acknowledgment_markdown()
                enhanced_content += "\n\n\\newpage\n\n" + acknowledgment_content

            # Write to temporary file
            temp_path = markdown_path.parent / f"temp_{markdown_path.stem}_marked.md"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(enhanced_content)

            return temp_path

        except Exception as e:
            raise PDFGenerationError(f"Failed to add AI marking to markdown: {e}")

    def _create_enhanced_header(self) -> Path:
        """Create enhanced LaTeX header with watermarking and attribution."""
        try:
            # Read original header
            with open(self.config.header_file, 'r', encoding='utf-8') as f:
                original_header = f.read()

            # Create enhanced header
            enhanced_header = self._enhance_header_content(original_header)

            # Write to temporary file
            temp_header = Path(tempfile.gettempdir()) / "enhanced_header.tex"
            with open(temp_header, 'w', encoding='utf-8') as f:
                f.write(enhanced_header)

            return temp_header

        except Exception as e:
            raise PDFGenerationError(f"Failed to create enhanced header: {e}")

    def _enhance_header_content(self, original_header: str) -> str:
        """Enhance header content with AI marking features."""
        enhanced_header = original_header

        # Add watermarking package if enabled
        if self.ai_marking_config.enable_watermark:
            watermark_package = """
% Watermark package for AI content marking
\\usepackage{draftwatermark}
\\SetWatermarkText{""" + self.ai_marking_config.watermark_config.text + """}
\\SetWatermarkScale{""" + str(self.ai_marking_config.watermark_config.font_size / 48) + """}
\\SetWatermarkAngle{""" + str(self.ai_marking_config.watermark_config.rotation) + """}
\\SetWatermarkColor{""" + self.ai_marking_config.watermark_config.get_latex_watermark_color() + """}
\\SetWatermarkOpacity{""" + str(self.ai_marking_config.watermark_config.opacity) + """}
\\SetWatermarkVerCenter{0.5cm}
\\SetWatermarkHorCenter{0.5cm}
"""
            enhanced_header = watermark_package + enhanced_header

        # Update footer with attribution if enabled
        if self.ai_marking_config.enable_attribution:
            attribution_text = self.ai_marking_config.author_info.get_attribution_text()
            enhanced_header = enhanced_header.replace(
                "\\fancyfoot[C]{\\small AI-generated Study Material | Ram Kumar, saas.expert.ram@gmail.com}",
                f"\\fancyfoot[C]{{\\small AI-generated | {attribution_text}}}"
            )

        return enhanced_header

    def _generate_with_enhanced_features(
        self,
        markdown_path: Path,
        pdf_path: Path,
        enhanced_header_path: Path
    ) -> ProcessResult:
        """Generate PDF using enhanced header and marked content."""
        try:
            # Try different LaTeX engines in order of preference
            engines = ["xelatex", "pdflatex"]

            for engine in engines:
                try:
                    result = self._generate_with_engine_enhanced(
                        markdown_path, pdf_path, engine, enhanced_header_path
                    )
                    if result.success:
                        return result
                except PDFGenerationError:
                    # Try next engine
                    continue

            # If all engines failed, try minimal fallback
            return self._generate_minimal_fallback_enhanced(markdown_path, pdf_path)

        except Exception as e:
            raise PDFGenerationError(f"Enhanced PDF generation failed: {e}")

    def _generate_with_engine_enhanced(
        self,
        markdown_path: Path,
        pdf_path: Path,
        engine: str,
        enhanced_header_path: Path
    ) -> ProcessResult:
        """Generate PDF using specific LaTeX engine with enhanced header."""
        try:
            cmd = self._build_enhanced_pandoc_command(
                markdown_path, pdf_path, engine, enhanced_header_path
            )

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            return ProcessResult(
                success=True,
                output_path=pdf_path,
                message=f"Successfully generated AI-marked PDF using {engine}",
                metadata={
                    "engine": engine,
                    "markdown_file": str(markdown_path),
                    "pdf_file": str(pdf_path),
                    "enhanced_header": str(enhanced_header_path)
                }
            )

        except subprocess.CalledProcessError as e:
            error_msg = self._extract_error_message(e)
            raise PDFGenerationError(
                f"Enhanced PDF generation failed with {engine}: {error_msg}"
            )

    def _build_enhanced_pandoc_command(
        self,
        markdown_path: Path,
        pdf_path: Path,
        engine: str,
        enhanced_header_path: Path
    ) -> List[str]:
        """Build Pandoc command with enhanced header."""
        base_cmd = [
            "pandoc",
            str(markdown_path),
            "-o", str(pdf_path),
            f"--pdf-engine={engine}",
            f"--include-in-header={str(enhanced_header_path)}",
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

    def _generate_minimal_fallback_enhanced(self, markdown_path: Path, pdf_path: Path) -> ProcessResult:
        """Try minimal PDF generation with basic AI marking."""
        try:
            # Create minimal header with just attribution
            minimal_header = self._create_minimal_header()

            cmd = [
                "pandoc",
                str(markdown_path),
                "-o", str(pdf_path),
                "--pdf-engine=pdflatex",
                f"--include-in-header={minimal_header}",
                "--variable", "fontsize=12pt",
                "--fail-if-warnings=false",
                "--pdf-engine-opt=-interaction=nonstopmode"
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True)

            # Clean up minimal header
            if minimal_header.exists():
                minimal_header.unlink()

            return ProcessResult(
                success=True,
                output_path=pdf_path,
                message="Generated AI-marked PDF with minimal configuration",
                metadata={"fallback_mode": True, "minimal_enhancement": True}
            )

        except subprocess.CalledProcessError as e:
            raise PDFGenerationError(
                f"Minimal enhanced PDF generation also failed: {self._extract_error_message(e)}"
            )

    def _create_minimal_header(self) -> Path:
        """Create minimal header with just attribution."""
        minimal_header_content = f"""
% Minimal header for AI marking fallback
\\usepackage{{fancyhdr}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\renewcommand{{\\headrulewidth}}{{0.5pt}}
\\renewcommand{{\\footrulewidth}}{{0.5pt}}
\\fancyhead[L]{{\\leftmark}}
\\fancyhead[R]{{\\thepage}}
\\fancyfoot[C]{{\\small AI-generated | {self.ai_marking_config.author_info.get_attribution_text()}}}
"""

        temp_header = Path(tempfile.gettempdir()) / "minimal_enhanced_header.tex"
        with open(temp_header, 'w', encoding='utf-8') as f:
            f.write(minimal_header_content)

        return temp_header

    def _generate_acknowledgment_markdown(self) -> str:
        """Generate acknowledgment page content."""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        acknowledgment = f"""
---

# Acknowledgment

This study material was generated using an automated utility script created by:

**{self.ai_marking_config.author_info.name}**
{self.ai_marking_config.author_info.email}

## About This Utility

This Python-based system demonstrates advanced software engineering principles
in media processing and AI-powered content generation. It seamlessly processes
video, audio, text, and image files to create comprehensive learning materials
including transcripts, summaries, glossaries, and practice questions.

## Technical Features

- **Multi-modal Media Processing**: Supports video, audio, text, and image inputs
- **AI-Powered Content Generation**: Uses state-of-the-art language models
- **Automated PDF Generation**: Creates professionally formatted study materials
- **Intelligent Conflict Resolution**: Handles mixed media file scenarios
- **Object-Oriented Architecture**: Clean, maintainable, and extensible design

## Architecture Highlights

- **Service-Oriented Design**: Loosely coupled, reusable services
- **Domain-Driven Design**: Rich domain model with business logic encapsulation
- **Comprehensive Testing**: High test coverage across all layers
- **Error Handling**: Robust error management and recovery

---

*Generated on {current_time}*
"""
        return acknowledgment
