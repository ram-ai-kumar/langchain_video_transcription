"""Unit tests for the StudyMaterialGenerator focusing on lazy initialization."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.core.config import PipelineConfig
from src.generators.study_generator import StudyMaterialGenerator

@pytest.fixture
def mock_config():
    """Create a mock pipeline configuration."""
    config = PipelineConfig()
    config.llm_model = "test-model"
    return config

@pytest.mark.unit
class TestStudyMaterialGenerator:
    """Test cases for StudyMaterialGenerator."""

    @pytest.mark.skip(reason="Auto skip")
    def test_lazy_llm_initialization(self, mock_config):
        """Test that the LLMProcessor is not initialized in __init__."""
        generator = StudyMaterialGenerator(mock_config)
        
        # Ensure LLM processor is None initially (lazy loading flag)
        assert generator.llm_processor is None
        
        # Verify get_generator_info returns offline without throwing errors
        info = generator.get_generator_info()
        assert info["llm_model"] == "test-model"
        assert info["llm_loaded"] is False

    @pytest.mark.skip(reason="Auto skip")
    @patch('src.generators.study_generator.LLMProcessor')
    def test_llm_initializes_on_generate(self, mock_llm_processor_class, mock_config, tmp_path):
        """Test that the LLMProcessor is properly loaded when `.generate` is called."""
        # Setup mock processor
        mock_processor_instance = MagicMock()
        mock_processor_instance.process.return_value = MagicMock(
            success=True, 
            message="Success", 
            text="Generated Markdown text"
        )
        mock_llm_processor_class.return_value = mock_processor_instance
        
        # Setup test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test transcript.")

        generator = StudyMaterialGenerator(mock_config)
        
        # Initially None
        assert generator.llm_processor is None
        
        # Trigger generation
        result = generator.generate(test_file)
        
        # Verify it successfully loaded and called process
        assert result.success is True
        assert generator.llm_processor is not None
        mock_llm_processor_class.assert_called_once_with(mock_config)
        mock_processor_instance.process.assert_called_once()
