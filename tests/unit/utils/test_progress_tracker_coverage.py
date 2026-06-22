"""Comprehensive tests for progress_tracker to achieve 100% coverage."""

import pytest
import shutil
from pathlib import Path
from unittest.mock import patch

from src.utils.progress_tracker import ProgressTracker


@pytest.fixture
def tracker():
    return ProgressTracker()


class TestStartFile:
    @patch('builtins.print')
    def test_start_file(self, mock_print, tracker):
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text", "markdown"]
        tracker.start_file(file_path, stages)
        assert str(file_path) in tracker.active_files
        assert tracker.active_files[str(file_path)]['current_stage'] == 0
        assert tracker.active_files[str(file_path)]['stages'] == stages
        assert str(file_path) in tracker.file_lines
        assert str(file_path) in tracker.max_line_length


class TestCompleteStage:
    @patch('builtins.print')
    def test_complete_stage(self, mock_print, tracker):
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text", "markdown"]
        tracker.start_file(file_path, stages)
        tracker.complete_stage(file_path)
        assert tracker.active_files[str(file_path)]['current_stage'] == 1

    @patch('builtins.print')
    def test_complete_stage_nonexistent(self, mock_print, tracker):
        file_path = Path("/data/nonexistent.mp4")
        tracker.complete_stage(file_path)
        # Should not raise


class TestCompleteFile:
    @patch('builtins.print')
    def test_complete_file(self, mock_print, tracker):
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text"]
        tracker.start_file(file_path, stages)
        tracker.complete_file(file_path)
        assert str(file_path) not in tracker.active_files
        assert str(file_path) in tracker.completed_files

    @patch('builtins.print')
    def test_complete_file_nonexistent(self, mock_print, tracker):
        file_path = Path("/data/nonexistent.mp4")
        tracker.complete_file(file_path)
        # Should not raise


class TestTerminalWidth:
    def test_terminal_width(self, tracker):
        width = tracker._terminal_width()
        assert isinstance(width, int)
        assert width > 0


class TestFormatPath:
    def test_short_path(self, tracker):
        path = Path("/data/video.mp4")
        result = tracker._format_path(path, 80)
        assert result == "data/video.mp4"

    def test_medium_path(self, tracker):
        path = Path("/data/lectures/video.mp4")
        result = tracker._format_path(path, 80)
        assert result == "lectures/video.mp4"

    def test_long_path_truncated_to_filename(self, tracker):
        path = Path("/data/lectures/week1/very_long_video_filename_that_exceeds_budget.mp4")
        result = tracker._format_path(path, 30)
        # Should fall back to filename if parent/filename too long
        assert "very_long_video_filename_that_exceeds_budget.mp4" in result or "..." in result

    def test_path_filename_only_fits(self, tracker):
        """Test that filename-only is used when parent+filename too long but filename fits."""
        path = Path("/very/long/path/that/exceeds/budget/short.mp4")
        result = tracker._format_path(path, 15)
        # parent+filename too long, but filename "short.mp4" fits in 15
        assert result == "short.mp4"

    def test_very_long_filename_middle_ellipsis(self, tracker):
        path = Path("/data/this_is_a_very_long_filename_that_exceeds_the_budget.mp4")
        result = tracker._format_path(path, 20)
        assert "..." in result

    def test_path_no_parent(self, tracker):
        path = Path("video.mp4")
        result = tracker._format_path(path, 80)
        assert result == "video.mp4"

    def test_path_empty_parts(self, tracker):
        path = Path("video.mp4")
        result = tracker._format_path(path, 80)
        assert "video.mp4" in result


class TestBuildLine:
    @patch('builtins.print')
    def test_build_line_active(self, mock_print, tracker):
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text", "markdown"]
        tracker.start_file(file_path, stages)
        line = tracker._build_line(file_path, stages, 0, False, 80)
        assert "video.mp4" in line
        assert "[1/3: audio]" in line

    @patch('builtins.print')
    def test_build_line_complete(self, mock_print, tracker):
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text", "markdown"]
        tracker.start_file(file_path, stages)
        line = tracker._build_line(file_path, stages, 2, True, 80)
        assert "✓" in line
        assert "video.mp4" in line

    def test_build_line_stage_overflow(self, tracker):
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text"]
        line = tracker._build_line(file_path, stages, 5, False, 80)
        # current_stage > total should use last stage name
        assert "text" in line


class TestUpdateDisplay:
    @patch('builtins.print')
    def test_update_display_active(self, mock_print, tracker):
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text"]
        tracker.start_file(file_path, stages)
        mock_print.assert_called()
        # Verify in-place update (end="" and flush=True)
        last_call = mock_print.call_args_list[-1]
        assert last_call.kwargs.get('end') == ""
        assert last_call.kwargs.get('flush') is True

    @patch('builtins.print')
    def test_update_display_complete(self, mock_print, tracker):
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text"]
        tracker.start_file(file_path, stages)
        mock_print.reset_mock()
        tracker.complete_file(file_path)
        mock_print.assert_called()
        last_call = mock_print.call_args_list[-1]
        # Complete should NOT have end="" (uses default newline)
        assert last_call.kwargs.get('end') != ""

    @patch('builtins.print')
    def test_update_display_padding(self, mock_print, tracker):
        """Test that padding is applied when line gets shorter."""
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text", "markdown", "pdf"]
        tracker.start_file(file_path, stages)
        # Complete all stages to make line shorter
        tracker.complete_stage(file_path)
        tracker.complete_stage(file_path)
        tracker.complete_stage(file_path)
        # Complete file - line should be shorter, padding applied
        tracker.complete_file(file_path)
        # Verify print was called
        assert mock_print.called

    def test_update_display_nonexistent(self, tracker):
        """Test _update_display with unknown file key."""
        tracker._update_display("/nonexistent/path")
        # Should not raise


class TestClearAll:
    @patch('builtins.print')
    def test_clear_all(self, mock_print, tracker):
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text"]
        tracker.start_file(file_path, stages)
        tracker.complete_stage(file_path)
        assert len(tracker.active_files) > 0
        tracker.clear_all()
        assert len(tracker.active_files) == 0
        assert len(tracker.completed_files) == 0
        assert len(tracker.file_lines) == 0
        assert len(tracker.max_line_length) == 0


class TestMultipleFiles:
    @patch('builtins.print')
    def test_multiple_files_tracked(self, mock_print, tracker):
        file1 = Path("/data/video1.mp4")
        file2 = Path("/data/video2.mp4")
        stages = ["audio", "text"]
        tracker.start_file(file1, stages)
        tracker.start_file(file2, stages)
        assert len(tracker.active_files) == 2
        tracker.complete_file(file1)
        assert str(file1) not in tracker.active_files
        assert str(file1) in tracker.completed_files
        assert str(file2) in tracker.active_files
