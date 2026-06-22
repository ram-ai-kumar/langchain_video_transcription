"""Comprehensive tests for ui_utils to achieve 100% coverage."""

import pytest
from unittest.mock import patch

from src.utils.ui_utils import ColorFormatter, StatusReporter


class TestColorFormatter:
    def test_format_known_color(self):
        result = ColorFormatter.format("text", "red")
        assert "\033[31m" in result
        assert "\033[0m" in result
        assert "text" in result

    def test_format_unknown_color(self):
        result = ColorFormatter.format("text", "nonexistent")
        assert result == "text"

    def test_error(self):
        result = ColorFormatter.error("error text")
        assert "\033[31m" in result
        assert "error text" in result

    def test_success(self):
        result = ColorFormatter.success("success text")
        assert "\033[32m" in result
        assert "success text" in result

    def test_warning(self):
        result = ColorFormatter.warning("warning text")
        assert "\033[33m" in result
        assert "warning text" in result

    def test_info(self):
        result = ColorFormatter.info("info text")
        assert "\033[34m" in result
        assert "info text" in result

    def test_bold(self):
        result = ColorFormatter.bold("bold text")
        assert "\033[1m" in result
        assert "bold text" in result

    def test_all_colors(self):
        for color in ['red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white', 'reset', 'bold', 'underline']:
            result = ColorFormatter.format("test", color)
            assert "test" in result


class TestStatusReporter:
    @patch('builtins.print')
    def test_info_verbose(self, mock_print):
        reporter = StatusReporter(verbose=True)
        reporter.info("Test message")
        mock_print.assert_called_once_with("    [INFO] Test message")

    @patch('builtins.print')
    def test_info_not_verbose(self, mock_print):
        reporter = StatusReporter(verbose=False)
        reporter.info("Test message")
        mock_print.assert_not_called()

    @patch('builtins.print')
    def test_info_custom_prefix(self, mock_print):
        reporter = StatusReporter(verbose=True)
        reporter.info("Test message", prefix="[CUSTOM]")
        mock_print.assert_called_once_with("    [CUSTOM] Test message")

    @patch('builtins.print')
    def test_warning_verbose(self, mock_print):
        reporter = StatusReporter(verbose=True)
        reporter.warning("Test warning")
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "[WARN]" in call_args
        assert "Test warning" in call_args

    @patch('builtins.print')
    def test_warning_not_verbose(self, mock_print):
        reporter = StatusReporter(verbose=False)
        reporter.warning("Test warning")
        mock_print.assert_not_called()

    @patch('builtins.print')
    def test_warning_custom_prefix(self, mock_print):
        reporter = StatusReporter(verbose=True)
        reporter.warning("Test warning", prefix="[ALERT]")
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "[ALERT]" in call_args

    @patch('builtins.print')
    def test_error_always_shows(self, mock_print):
        reporter = StatusReporter(verbose=False)
        reporter.error("Test error")
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "[ERROR]" in call_args
        assert "Test error" in call_args

    @patch('builtins.print')
    def test_error_verbose(self, mock_print):
        reporter = StatusReporter(verbose=True)
        reporter.error("Test error")
        mock_print.assert_called_once()

    @patch('builtins.print')
    def test_error_custom_prefix(self, mock_print):
        reporter = StatusReporter(verbose=False)
        reporter.error("Test error", prefix="[FATAL]")
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "[FATAL]" in call_args

    @patch('builtins.print')
    def test_success_verbose(self, mock_print):
        reporter = StatusReporter(verbose=True)
        reporter.success("Test success")
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "[SUCCESS]" in call_args

    @patch('builtins.print')
    def test_success_not_verbose(self, mock_print):
        reporter = StatusReporter(verbose=False)
        reporter.success("Test success")
        mock_print.assert_not_called()

    @patch('builtins.print')
    def test_success_custom_prefix(self, mock_print):
        reporter = StatusReporter(verbose=True)
        reporter.success("Test success", prefix="[DONE]")
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "[DONE]" in call_args

    @patch('builtins.print')
    def test_debug_verbose(self, mock_print):
        reporter = StatusReporter(verbose=True)
        reporter.debug("Test debug")
        mock_print.assert_called_once_with("    [DEBUG] Test debug")

    @patch('builtins.print')
    def test_debug_not_verbose(self, mock_print):
        reporter = StatusReporter(verbose=False)
        reporter.debug("Test debug")
        mock_print.assert_not_called()

    @patch('builtins.print')
    def test_debug_custom_prefix(self, mock_print):
        reporter = StatusReporter(verbose=True)
        reporter.debug("Test debug", prefix="[TRACE]")
        mock_print.assert_called_once_with("    [TRACE] Test debug")
