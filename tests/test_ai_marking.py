"""Tests for AI content marking functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.domain.ai_marking import AuthorInfo, WatermarkConfig, AIMarkingConfig
from src.generators.enhanced_pdf_generator import EnhancedPDFGenerator
from src.core.config import PipelineConfig
from src.core.exceptions import PDFGenerationError


class TestAuthorInfo:
    """Test AuthorInfo value object."""

    def test_get_attribution_text(self):
        """Test attribution text formatting."""
        author = AuthorInfo(name="Ram Kumar", email="saas.expert.ram@gmail.com")
        expected = "Ram Kumar, saas.expert.ram@gmail.com"
        assert author.get_attribution_text() == expected


class TestWatermarkConfig:
    """Test WatermarkConfig value object."""

    def test_default_values(self):
        """Test default watermark configuration."""
        config = WatermarkConfig()
        assert config.text == "AI Generated Content"
        assert config.opacity == 0.3
        assert config.rotation == 45
        assert config.font_size == 48
        assert config.color == "#CCCCCC"

    def test_latex_color_conversion(self):
        """Test hex to LaTeX color conversion."""
        config = WatermarkConfig(color="#FF0000")  # Red
        latex_color = config.get_latex_watermark_color()
        assert "rgb,1.000,0.000,0.000" in latex_color

    def test_latex_color_invalid_hex(self):
        """Test LaTeX color conversion with invalid hex."""
        config = WatermarkConfig(color="invalid")
        latex_color = config.get_latex_watermark_color()
        assert latex_color == "{rgb,0.8,0.8,0.8}"  # Default gray


class TestAIMarkingConfig:
    """Test AIMarkingConfig value object."""

    def test_create_default(self):
        """Test default AI marking configuration."""
        config = AIMarkingConfig.create_default()

        assert config.author_info.name == "Ram Kumar"
        assert config.author_info.email == "saas.expert.ram@gmail.com"
        assert config.enable_watermark is True
        assert config.enable_attribution is True
        assert config.enable_acknowledgment is True

    def test_custom_config(self):
        """Test custom AI marking configuration."""
        author = AuthorInfo(name="Test Author", email="test@example.com")
        watermark = WatermarkConfig(text="Custom Watermark")

        config = AIMarkingConfig(
            author_info=author,
            watermark_config=watermark,
            enable_watermark=False
        )

        assert config.author_info == author
        assert config.watermark_config == watermark
        assert config.enable_watermark is False


class TestEnhancedPDFGenerator:
    """Test EnhancedPDFGenerator class."""

    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = PipelineConfig(
                output_dir=Path(temp_dir),
                generate_pdf=True,
                enable_ai_marking=True
            )
            # Create dummy header file
            header_path = Path(temp_dir) / "header.tex"
            header_path.write_text("% Test header")
            config.header_file = header_path

            # Create dummy prompt file
            prompt_path = Path(temp_dir) / "prompt.txt"
            prompt_path.write_text("Test prompt")
            config.prompt_file = prompt_path

            yield config

    @pytest.fixture
    def sample_markdown(self):
        """Create sample markdown content."""
        return """# Test Document

This is a test document for AI marking functionality.

## Section 1

Some content here.

## Section 2

More content here.
"""

    def test_init_with_default_ai_config(self, temp_config):
        """Test initialization with default AI marking config."""
        generator = EnhancedPDFGenerator(temp_config)

        assert generator.ai_marking_config is not None
        assert generator.ai_marking_config.author_info.name == "Ram Kumar"
        assert generator.ai_marking_config.enable_watermark is True

    def test_init_with_custom_ai_config(self, temp_config):
        """Test initialization with custom AI marking config."""
        custom_config = AIMarkingConfig(
            author_info=AuthorInfo(name="Custom", email="custom@test.com"),
            watermark_config=WatermarkConfig(),
            enable_watermark=False
        )

        generator = EnhancedPDFGenerator(temp_config, custom_config)

        assert generator.ai_marking_config.author_info.name == "Custom"
        assert generator.ai_marking_config.enable_watermark is False

    def test_add_ai_marking_to_markdown_with_acknowledgment(self, temp_config, sample_markdown):
        """Test adding AI marking to markdown with acknowledgment."""
        generator = EnhancedPDFGenerator(temp_config)

        # Create temporary markdown file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(sample_markdown)
            markdown_path = Path(f.name)

        try:
            marked_path = generator._add_ai_marking_to_markdown(markdown_path)

            # Read marked content
            marked_content = marked_path.read_text(encoding='utf-8')

            # Check that acknowledgment is added
            assert "Acknowledgment" in marked_content
            assert "Ram Kumar" in marked_content
            assert "saas.expert.ram@gmail.com" in marked_content
            assert "Generated on" in marked_content

            # Check that original content is preserved
            assert "Test Document" in marked_content
            assert "Section 1" in marked_content

        finally:
            # Cleanup
            if markdown_path.exists():
                markdown_path.unlink()
            if marked_path.exists():
                marked_path.unlink()

    def test_add_ai_marking_to_markdown_disabled_acknowledgment(self, temp_config, sample_markdown):
        """Test adding AI marking to markdown with acknowledgment disabled."""
        # Disable acknowledgment
        custom_config = AIMarkingConfig(
            author_info=AuthorInfo(name="Test", email="test@test.com"),
            watermark_config=WatermarkConfig(),
            enable_acknowledgment=False
        )
        temp_config.ai_marking_config = custom_config

        generator = EnhancedPDFGenerator(temp_config)

        # Create temporary markdown file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(sample_markdown)
            markdown_path = Path(f.name)

        try:
            marked_path = generator._add_ai_marking_to_markdown(markdown_path)

            # Read marked content
            marked_content = marked_path.read_text(encoding='utf-8')

            # Check that acknowledgment is NOT added
            assert "Acknowledgment" not in marked_content

            # Check that original content is preserved
            assert "Test Document" in marked_content

        finally:
            # Cleanup
            if markdown_path.exists():
                markdown_path.unlink()
            if marked_path.exists():
                marked_path.unlink()

    def test_enhance_header_content_with_watermark(self, temp_config):
        """Test header enhancement with watermark."""
        generator = EnhancedPDFGenerator(temp_config)

        original_header = "% Original header\n\\usepackage{fancyhdr}"
        enhanced_header = generator._enhance_header_content(original_header)

        # Check that watermark package is added
        assert "draftwatermark" in enhanced_header
        assert "SetWatermarkText" in enhanced_header
        assert "AI Generated Content" in enhanced_header

        # Check that original content is preserved
        assert "fancyhdr" in enhanced_header

    def test_enhance_header_content_with_attribution(self, temp_config):
        """Test header enhancement with attribution."""
        generator = EnhancedPDFGenerator(temp_config)

        original_header = "% Original header\n\\fancyfoot[C]{\\small Generated Study Material}"
        enhanced_header = generator._enhance_header_content(original_header)

        # Check that footer is updated with attribution
        assert "Ram Kumar, saas.expert.ram@gmail.com" in enhanced_header
        assert "Generated Study Material" not in enhanced_header

    def test_enhance_header_content_disabled_features(self, temp_config):
        """Test header enhancement with features disabled."""
        # Disable watermark and attribution
        custom_config = AIMarkingConfig(
            author_info=AuthorInfo(name="Test", email="test@test.com"),
            watermark_config=WatermarkConfig(),
            enable_watermark=False,
            enable_attribution=False
        )
        temp_config.ai_marking_config = custom_config

        generator = EnhancedPDFGenerator(temp_config)

        original_header = "% Original header\n\\usepackage{fancyhdr}\n\\fancyfoot[C]{\\small Generated Study Material}"
        enhanced_header = generator._enhance_header_content(original_header)

        # Check that watermark package is NOT added
        assert "draftwatermark" not in enhanced_header

        # Check that footer is NOT changed
        assert "Generated Study Material" in enhanced_header

    def test_generate_acknowledgment_markdown(self, temp_config):
        """Test acknowledgment markdown generation."""
        generator = EnhancedPDFGenerator(temp_config)

        acknowledgment = generator._generate_acknowledgment_markdown()

        # Check key content
        assert "Acknowledgment" in acknowledgment
        assert "Ram Kumar" in acknowledgment
        assert "saas.expert.ram@gmail.com" in acknowledgment
        assert "About This Utility" in acknowledgment
        assert "Technical Features" in acknowledgment
        assert "Architecture Highlights" in acknowledgment
        assert "Generated on" in acknowledgment

    @patch('subprocess.run')
    def test_generate_pdf_success(self, mock_subprocess, temp_config, sample_markdown):
        """Test successful PDF generation with AI marking."""
        # Mock successful subprocess calls
        mock_subprocess.return_value = Mock(
            stdout="",
            stderr="",
            returncode=0
        )

        generator = EnhancedPDFGenerator(temp_config)

        # Create temporary markdown file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(sample_markdown)
            markdown_path = Path(f.name)

        pdf_path = markdown_path.with_suffix('.pdf')

        try:
            result = generator.generate_pdf(markdown_path, pdf_path)

            assert result.success is True
            assert "AI-marked PDF" in result.message
            assert result.metadata["ai_marked"] is True
            assert result.metadata["watermark_enabled"] is True
            assert result.metadata["attribution_enabled"] is True
            assert result.metadata["acknowledgment_enabled"] is True

        finally:
            # Cleanup
            if markdown_path.exists():
                markdown_path.unlink()
            if pdf_path.exists():
                pdf_path.unlink()

    def test_generate_pdf_error_handling(self, temp_config, sample_markdown):
        """Test PDF generation error handling."""
        generator = EnhancedPDFGenerator(temp_config)

        # Create invalid markdown path to trigger error
        invalid_path = Path("/nonexistent/path.md")
        pdf_path = Path("/nonexistent/path.pdf")

        with pytest.raises(PDFGenerationError):
            generator.generate_pdf(invalid_path, pdf_path)
