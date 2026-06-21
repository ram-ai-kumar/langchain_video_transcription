"""Smoke tests for llm_processor module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.processors.llm_processor import LLMProcessor
from src.core.config import PipelineConfig


@pytest.mark.unit
@pytest.mark.smoke
class TestLLMProcessorSmoke:
    """Smoke tests for LLMProcessor."""

    def test_initialization(self, mock_config):
        """Test that LLMProcessor can be initialized."""
        processor = LLMProcessor(mock_config)
        
        assert processor.config == mock_config
        assert processor.llm is None
        assert processor.prompt_template is None
        assert processor.study_chain is None

    def test_can_process_text(self, mock_config, sample_text_file):
        """Test that processor can identify text files."""
        processor = LLMProcessor(mock_config)
        assert processor.can_process(sample_text_file) is True

    def test_can_process_non_text(self, mock_config, sample_audio_file):
        """Test that processor rejects non-text files."""
        processor = LLMProcessor(mock_config)
        assert processor.can_process(sample_audio_file) is False

    def test_get_model_info(self, mock_config):
        """Test getting model information."""
        processor = LLMProcessor(mock_config)
        info = processor.get_model_info()
        
        assert isinstance(info, dict)
        assert "model_name" in info
        assert "is_loaded" in info
        assert "prompt_file" in info
        assert "prompt_loaded" in info

    def test_validate_llm_connection(self, mock_config):
        """Test LLM connection validation."""
        processor = LLMProcessor(mock_config)
        
        # This will likely fail if Ollama is not running, but tests the method
        result = processor.validate_llm_connection()
        assert isinstance(result, bool)

    @pytest.mark.skip(reason="Requires Ollama LLM service")
    def test_process_transcript(self, mock_config, sample_text_file, temp_dir):
        """Test basic transcript processing."""
        processor = LLMProcessor(mock_config)
        output_path = temp_dir / "study.md"
        
        result = processor.process(sample_text_file, output_path)
        assert result is not None

    def test_process_empty_transcript(self, mock_config, temp_dir):
        """Test processing empty transcript."""
        processor = LLMProcessor(mock_config)
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("")
        output_path = temp_dir / "study.md"
        
        result = processor.process(empty_file, output_path)
        assert result.success is False
        assert "empty" in result.message.lower()

    @patch('src.processors.llm_processor.OllamaLLM')
    def test_load_llm(self, mock_llm_class, mock_config):
        """Test LLM loading."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        processor = LLMProcessor(mock_config)
        llm = processor._load_llm()
        
        assert llm == mock_llm
        mock_llm_class.assert_called_once_with(model=mock_config.llm_model)

    @patch('src.utils.file_utils.FileManager')
    def test_load_prompt_template(self, mock_file_manager, mock_config):
        """Test prompt template loading."""
        mock_file_manager.safe_read_text.return_value = "Test prompt template with {transcript}"
        
        processor = LLMProcessor(mock_config)
        template = processor._load_prompt_template()
        
        assert template is not None
        mock_file_manager.safe_read_text.assert_called_once_with(mock_config.prompt_file)
