"""Smoke tests for error_summarizer module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.utils.error_summarizer import ErrorSummarizer
from src.utils.error_logger import ErrorLogger
from src.core.config import PipelineConfig


@pytest.mark.unit
@pytest.mark.smoke
class TestErrorSummarizerSmoke:
    """Smoke tests for ErrorSummarizer."""

    def test_initialization(self, temp_dir, mock_config):
        """Test that ErrorSummarizer can be initialized."""
        error_logger = ErrorLogger(cache_dir=temp_dir)
        summarizer = ErrorSummarizer(mock_config, error_logger)
        
        assert summarizer.config == mock_config
        assert summarizer.error_logger == error_logger
        assert summarizer.llm is None
        assert summarizer.summary_chain is None

    def test_summarize_errors_no_errors(self, temp_dir, mock_config):
        """Test summarization when no errors exist."""
        error_logger = ErrorLogger(cache_dir=temp_dir)
        summarizer = ErrorSummarizer(mock_config, error_logger)
        
        result = summarizer.summarize_errors()
        assert result is None

    def test_summarize_errors_with_errors(self, temp_dir, mock_config):
        """Test summarization with errors (mocked LLM)."""
        error_logger = ErrorLogger(cache_dir=temp_dir)
        error_logger.log_error("test_type", "Test error message")
        
        summarizer = ErrorSummarizer(mock_config, error_logger)
        
        with patch.object(summarizer, '_get_summary_chain') as mock_chain:
            mock_chain.return_value.invoke.return_value = "Test summary"
            result = summarizer.summarize_errors()
            
            assert result == "Test summary"
            mock_chain.return_value.invoke.assert_called_once()

    def test_get_cached_summary_none(self, temp_dir, mock_config):
        """Test get_cached_summary when no summary exists."""
        error_logger = ErrorLogger(cache_dir=temp_dir)
        summarizer = ErrorSummarizer(mock_config, error_logger)
        
        result = summarizer.get_cached_summary()
        assert result is None

    def test_get_cached_summary_exists(self, temp_dir, mock_config):
        """Test get_cached_summary when summary exists."""
        error_logger = ErrorLogger(cache_dir=temp_dir)
        error_logger.save_summary("Test summary")
        
        summarizer = ErrorSummarizer(mock_config, error_logger)
        result = summarizer.get_cached_summary()
        
        assert result == "Test summary"
