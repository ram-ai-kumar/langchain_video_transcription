"""Unit tests for UI utilities."""

import pytest
from unittest.mock import Mock, MagicMock, patch
import io
import sys

from src.utils.ui_utils import ProgressReporter, StatusReporter, ColorFormatter


@pytest.mark.unit
@pytest.mark.ui
class TestProgressReporter:
    """Test cases for ProgressReporter."""

    def test_init(self):
        """Test ProgressReporter initialization."""
        reporter = ProgressReporter(verbose=True)
        assert reporter.verbose is True
        assert reporter.started is False

    def test_start_processing(self):
        """Test starting processing."""
        reporter = ProgressReporter(verbose=True)
        reporter.progress = Mock()
        steps = ["audio", "transcript", "study_material"]

        reporter.start_processing("/test/file.txt", steps)
        
        assert reporter.started is True
        reporter.progress.start.assert_called_once()
        reporter.progress.add_task.assert_called_once_with(
            description="/test/file.txt", 
            total=len(steps)
        )
        assert "/test/file.txt" in reporter.tasks

    def test_next_step(self):
        """Test moving to next step."""
        reporter = ProgressReporter(verbose=True)
        reporter.progress = Mock()
        reporter.tasks["file.txt"] = "task_1"
        
        reporter.next_step("file.txt")
        reporter.progress.update.assert_called_once_with("task_1", advance=1)

    def test_complete_processing_success(self):
        """Test successful processing completion."""
        reporter = ProgressReporter(verbose=True)
        reporter.progress = MagicMock()
        reporter.tasks["file.txt"] = "task_1"

        reporter.complete_processing(success=True, file_path="file.txt", prefix="├── ")

        # Verify it updates description with checkmark and sets to completed
        call_args = reporter.progress.update.call_args[1]
        assert "[green]✓ file.txt[/green]" in call_args["description"]
        assert "├── " in call_args["description"]

    def test_complete_processing_skipped(self):
        """Test processing completion when skipped."""
        reporter = ProgressReporter(verbose=True)
        reporter.progress = MagicMock()
        reporter.tasks["file.txt"] = "task_1"

        reporter.complete_processing(success=True, file_path="file.txt", skipped=True)

        call_args = reporter.progress.update.call_args[1]
        assert "[yellow]⏭  file.txt[/yellow]" in call_args["description"]

    def test_complete_processing_failure(self):
        """Test processing completion with failure."""
        reporter = ProgressReporter(verbose=True)
        reporter.progress = MagicMock()
        reporter.tasks["file.txt"] = "task_1"

        reporter.complete_processing(success=False, file_path="file.txt")

        call_args = reporter.progress.update.call_args[1]
        assert "[red]✗ file.txt[/red]" in call_args["description"]

    def test_stop(self):
        """Test stopping reporter."""
        reporter = ProgressReporter(verbose=True)
        reporter.progress = Mock()
        reporter.started = True
        
        reporter.stop()
        
        assert reporter.started is False
        reporter.progress.stop.assert_called_once()


class TestStatusReporter:
    """Test cases for StatusReporter."""

    def test_init_verbose(self):
        """Test StatusReporter initialization with verbose=True."""
        reporter = StatusReporter(verbose=True)

        assert reporter.verbose is True

    def test_init_not_verbose(self):
        """Test StatusReporter initialization with verbose=False."""
        reporter = StatusReporter(verbose=False)

        assert reporter.verbose is False

    @patch('builtins.print')
    def test_info_verbose(self, mock_print):
        """Test info message with verbose=True."""
        reporter = StatusReporter(verbose=True)

        reporter.info("Test info message")

        mock_print.assert_called_once_with("    [INFO] Test info message")

    @patch('builtins.print')
    def test_info_not_verbose(self, mock_print):
        """Test info message with verbose=False."""
        reporter = StatusReporter(verbose=False)

        reporter.info("Test info message")

        mock_print.assert_not_called()  # Should not print when not verbose

    @patch('builtins.print')
    def test_error_always_shows(self, mock_print):
        """Test error message always shows regardless of verbose."""
        reporter = StatusReporter(verbose=False)

        reporter.error("Test error message")

        mock_print.assert_called_once()  # Errors always show

    @patch('builtins.print')
    def test_warning_verbose(self, mock_print):
        """Test warning message with verbose=True."""
        reporter = StatusReporter(verbose=True)

        reporter.warning("Test warning message")

        mock_print.assert_called_once()

    @patch('builtins.print')
    def test_success_verbose(self, mock_print):
        """Test success message with verbose=True."""
        reporter = StatusReporter(verbose=True)

        reporter.success("Test success message")

        mock_print.assert_called_once()


class TestColorFormatter:
    """Test cases for ColorFormatter."""

    def test_info_formatting(self):
        """Test info message formatting."""
        result = ColorFormatter.info("Test message")

        assert "Test message" in result

    def test_error_formatting(self):
        """Test error message formatting."""
        result = ColorFormatter.error("Test error")

        assert "Test error" in result

    def test_warning_formatting(self):
        """Test warning message formatting."""
        result = ColorFormatter.warning("Test warning")

        assert "Test warning" in result

    def test_success_formatting(self):
        """Test success message formatting."""
        result = ColorFormatter.success("Test success")

        assert "Test success" in result
