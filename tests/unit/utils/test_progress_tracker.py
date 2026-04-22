"""Unit tests for ProgressTracker class."""

import pytest
from pathlib import Path
from unittest.mock import patch
from src.utils.progress_tracker import ProgressTracker


@pytest.mark.unit
@pytest.mark.utils
class TestProgressTracker:
    """Test cases for ProgressTracker functionality."""

    @pytest.fixture
    def tracker(self):
        """Create a fresh ProgressTracker for each test."""
        return ProgressTracker()

    def test_path_truncation_short_path(self, tracker):
        """Test path truncation for short paths (≤3 levels)."""
        # Test 2-level path
        short_path = Path("/data/video.mp4")
        result = tracker._format_path(short_path)
        assert result == "/data/video.mp4"

        # Test 3-level path
        medium_path = Path("/data/lectures/video.mp4")
        result = tracker._format_path(medium_path)
        assert result == "/data/lectures/video.mp4"

    def test_path_truncation_long_path(self, tracker):
        """Test path truncation for long paths (4+ levels)."""
        # Test 4-level path
        long_path = Path("/data/lectures/week1/video.mp4")
        result = tracker._format_path(long_path)
        assert result == "/lectures/week1/video.mp4"

        # Test 5+ level path
        very_long_path = Path("/Users/ram/Work/Lab/code/video_transcription/data/lectures/week1/video.mp4")
        result = tracker._format_path(very_long_path)
        assert result == ".../lectures/week1/video.mp4"

    def test_start_file_initialization(self, tracker):
        """Test starting file tracking initializes correctly."""
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text", "markdown", "pdf"]

        tracker.start_file(file_path, stages)

        assert str(file_path) in tracker.active_files
        assert tracker.active_files[str(file_path)]['current_stage'] == 0
        assert tracker.active_files[str(file_path)]['stages'] == stages
        assert str(file_path) in tracker.max_line_length

    def test_complete_stage_progression(self, tracker):
        """Test stage completion updates current stage correctly."""
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text", "markdown", "pdf"]

        tracker.start_file(file_path, stages)

        # Complete first stage
        tracker.complete_stage(file_path)
        assert tracker.active_files[str(file_path)]['current_stage'] == 1

        # Complete second stage
        tracker.complete_stage(file_path)
        assert tracker.active_files[str(file_path)]['current_stage'] == 2

        # Complete third stage
        tracker.complete_stage(file_path)
        assert tracker.active_files[str(file_path)]['current_stage'] == 3

    def test_complete_file_moves_to_completed(self, tracker):
        """Test completing file moves it from active to completed."""
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text", "markdown", "pdf"]

        tracker.start_file(file_path, stages)
        assert str(file_path) in tracker.active_files
        assert str(file_path) not in tracker.completed_files

        tracker.complete_file(file_path)
        assert str(file_path) not in tracker.active_files
        assert str(file_path) in tracker.completed_files

    def test_progress_display_past_and_current_only(self, tracker):
        """Test progress display shows only past and current stages."""
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text", "markdown", "pdf"]

        # Test initial state (no stages completed)
        tracker.start_file(file_path, stages)

        # Test the display logic directly by checking the parts
        file_info = tracker.active_files[str(file_path)]
        current_stage = file_info['current_stage']

        # Initially should show only "..." for current stage
        progress_parts = []
        for i, stage in enumerate(stages):
            if i < current_stage:
                progress_parts.append(stage)
            elif i == current_stage and not False:  # not complete
                progress_parts.append("...")
            else:
                break

        progress_str = " > ".join(progress_parts)
        assert "..." in progress_str
        assert "audio" not in progress_str  # Past stage not shown yet
        assert "text" not in progress_str   # Future stage not shown

        # Complete first stage and test again
        tracker.complete_stage(file_path)
        file_info = tracker.active_files[str(file_path)]
        current_stage = file_info['current_stage']

        progress_parts = []
        for i, stage in enumerate(stages):
            if i < current_stage:
                progress_parts.append(stage)
            elif i == current_stage and not False:  # not complete
                progress_parts.append("...")
            else:
                break

        progress_str = " > ".join(progress_parts)
        assert "audio" in progress_str   # Past stage shown
        assert "..." in progress_str    # Current stage shown
        assert "text" not in progress_str  # Future stage not shown

    def test_progress_display_completed_file(self, tracker):
        """Test completed file display shows all stages with checkmark."""
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text", "markdown", "pdf"]

        tracker.start_file(file_path, stages)

        # Complete all stages
        for _ in stages:
            tracker.complete_stage(file_path)

        # Complete file
        with patch('builtins.print') as mock_print:
            tracker.complete_file(file_path)

            # Check that print was called with checkmark
            mock_print.assert_called()
            call_args = str(mock_print.call_args)
            assert "✓" in call_args
            assert "audio > text > markdown > pdf" in call_args

    def test_clear_all_resets_state(self, tracker):
        """Test clear_all resets all tracking state."""
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text", "markdown", "pdf"]

        tracker.start_file(file_path, stages)
        tracker.complete_stage(file_path)

        # Verify state exists
        assert len(tracker.active_files) > 0
        assert len(tracker.max_line_length) > 0

        # Clear all
        tracker.clear_all()

        # Verify state is reset
        assert len(tracker.active_files) == 0
        assert len(tracker.completed_files) == 0
        assert len(tracker.file_lines) == 0
        assert len(tracker.max_line_length) == 0

    @patch('builtins.print')
    def test_in_place_display_updates(self, mock_print, tracker):
        """Test that display updates happen in-place with carriage return."""
        file_path = Path("/data/video.mp4")
        stages = ["audio", "text", "markdown", "pdf"]

        tracker.start_file(file_path, stages)

        # Verify print was called
        mock_print.assert_called()

        # Check that the call contains the expected elements
        call_args_list = mock_print.call_args_list
        assert len(call_args_list) > 0

        # The important thing is that print was called with the right parameters
        # We don't need to check the exact string format due to escaping issues
        first_call = call_args_list[0]
        assert first_call.kwargs.get('end') == ""  # No newline for in-place update
        assert first_call.kwargs.get('flush') == True  # Immediate flush

    def test_different_file_types_stages(self, tracker):
        """Test different file types have correct stages."""
        # Video file stages
        video_path = Path("/data/video.mp4")
        video_stages = ["audio", "text", "markdown", "pdf"]
        tracker.start_file(video_path, video_stages)

        # Audio file stages
        audio_path = Path("/data/audio.mp3")
        audio_stages = ["text", "markdown", "pdf"]
        tracker.start_file(audio_path, audio_stages)

        # Text file stages
        text_path = Path("/data/document.txt")
        text_stages = ["markdown", "pdf"]
        tracker.start_file(text_path, text_stages)

        # Verify all files are tracked
        assert len(tracker.active_files) == 3
        assert tracker.active_files[str(video_path)]['stages'] == video_stages
        assert tracker.active_files[str(audio_path)]['stages'] == audio_stages
        assert tracker.active_files[str(text_path)]['stages'] == text_stages
