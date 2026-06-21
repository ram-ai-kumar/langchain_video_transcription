"""Smoke tests for study_generator module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.generators.study_generator import StudyMaterialGenerator
from src.core.config import PipelineConfig


@pytest.mark.unit
@pytest.mark.smoke
class TestStudyMaterialGeneratorSmoke:
    """Smoke tests for StudyMaterialGenerator."""

    def test_initialization_with_pdf(self, mock_config):
        """Test initialization with PDF generation enabled."""
        mock_config.generate_pdf = True
        generator = StudyMaterialGenerator(mock_config)
        
        assert generator.config == mock_config
        assert generator.pdf_generator is not None
        assert generator._llm_processor is None

    def test_initialization_without_pdf(self, mock_config):
        """Test initialization without PDF generation."""
        mock_config.generate_pdf = False
        generator = StudyMaterialGenerator(mock_config)
        
        assert generator.config == mock_config
        assert generator.pdf_generator is None
        assert generator._llm_processor is None

    def test_validate_prerequisites(self, mock_config):
        """Test prerequisite validation."""
        generator = StudyMaterialGenerator(mock_config)
        validation = generator.validate_prerequisites()
        
        assert isinstance(validation, dict)
        assert "llm_available" in validation
        assert "pdf_available" in validation
        assert "prompt_file_exists" in validation
        assert "overall_ready" in validation

    def test_get_generator_info(self, mock_config):
        """Test getting generator information."""
        generator = StudyMaterialGenerator(mock_config)
        info = generator.get_generator_info()
        
        assert isinstance(info, dict)
        assert "config" in info
        assert "llm_info" in info

    def test_was_source_pdf_false(self, mock_config, temp_dir):
        """Test PDF source detection when not from PDF."""
        generator = StudyMaterialGenerator(mock_config)
        text_file = temp_dir / "test.txt"
        text_file.write_text("Test content")
        
        result = generator._was_source_pdf(text_file)
        assert result is False

    def test_generate_pdf_only_not_requested(self, mock_config, temp_dir):
        """Test PDF-only generation when not requested."""
        mock_config.generate_pdf = False
        generator = StudyMaterialGenerator(mock_config)
        
        study_file = temp_dir / "study.md"
        pdf_file = temp_dir / "study.pdf"
        
        result = generator.generate_pdf_only(study_file, study_file, pdf_file)
        assert result.success is True
        assert "not requested" in result.message.lower()

    def test_generate_pdf_only_missing_study_file(self, mock_config, temp_dir):
        """Test PDF-only generation with missing study file."""
        mock_config.generate_pdf = True
        generator = StudyMaterialGenerator(mock_config)
        
        study_file = temp_dir / "nonexistent.md"
        pdf_file = temp_dir / "study.pdf"
        
        result = generator.generate_pdf_only(study_file, study_file, pdf_file)
        assert result.success is False
        assert "not found" in result.message.lower()

    @patch('src.generators.study_generator.LLMProcessor')
    def test_lazy_llm_initialization(self, mock_llm_processor_class, mock_config):
        """Test that LLM processor is initialized lazily."""
        mock_config.generate_pdf = False
        generator = StudyMaterialGenerator(mock_config)
        
        # LLM processor should not be initialized yet
        assert generator._llm_processor is None
        
        # Access through validate_prerequisites should initialize it
        mock_config.target = "markdown"
        generator.validate_prerequisites()
        
        # Now it should be initialized
        assert generator._llm_processor is not None

    @patch('src.generators.study_generator.LLMProcessor')
    def test_generate_with_mocked_llm(self, mock_llm_processor_class, mock_config, temp_dir):
        """Test generation with mocked LLM processor."""
        mock_config.generate_pdf = False
        
        # Setup mock
        mock_llm_processor = Mock()
        mock_llm_processor.process.return_value = Mock(
            success=True,
            metadata={"test": "data"}
        )
        mock_llm_processor_class.return_value = mock_llm_processor
        
        generator = StudyMaterialGenerator(mock_config)
        
        transcript_file = temp_dir / "transcript.txt"
        transcript_file.write_text("Test transcript content")
        
        result = generator.generate(transcript_file)
        
        assert result is not None
        mock_llm_processor.process.assert_called_once()
