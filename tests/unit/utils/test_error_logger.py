"""Smoke tests for error_logger module."""

import pytest
from pathlib import Path
from src.utils.error_logger import ErrorLogger


@pytest.mark.unit
@pytest.mark.smoke
class TestErrorLoggerSmoke:
    """Smoke tests for ErrorLogger."""

    def test_initialization(self, temp_dir):
        """Test that ErrorLogger can be initialized."""
        logger = ErrorLogger(cache_dir=temp_dir)
        assert logger.cache_dir == temp_dir
        assert logger.error_log_path == temp_dir / "errors.txt"
        assert logger.summary_path == temp_dir / "errors_summary.txt"
        assert logger.cache_dir.exists()

    def test_log_error(self, temp_dir):
        """Test that errors can be logged."""
        logger = ErrorLogger(cache_dir=temp_dir)
        logger.log_error("test_type", "Test error message", "Test context")
        
        assert logger.get_error_count() == 1
        errors = logger.get_errors()
        assert "test_type" in errors
        assert "Test error message" in errors
        assert "Test context" in errors

    def test_clear_errors(self, temp_dir):
        """Test that errors can be cleared."""
        logger = ErrorLogger(cache_dir=temp_dir)
        logger.log_error("test_type", "Test error message")
        assert logger.get_error_count() == 1
        
        logger.clear_errors()
        assert logger.get_error_count() == 0

    def test_save_and_get_summary(self, temp_dir):
        """Test that summary can be saved and retrieved."""
        logger = ErrorLogger(cache_dir=temp_dir)
        summary = "Test summary content"
        logger.save_summary(summary)
        
        retrieved = logger.get_summary()
        assert retrieved == summary

    def test_get_error_count_empty(self, temp_dir):
        """Test error count when no errors logged."""
        logger = ErrorLogger(cache_dir=temp_dir)
        assert logger.get_error_count() == 0

    def test_get_errors_empty(self, temp_dir):
        """Test get_errors when no errors logged."""
        logger = ErrorLogger(cache_dir=temp_dir)
        assert logger.get_errors() == ""

    def test_get_summary_none(self, temp_dir):
        """Test get_summary when no summary saved."""
        logger = ErrorLogger(cache_dir=temp_dir)
        assert logger.get_summary() is None
