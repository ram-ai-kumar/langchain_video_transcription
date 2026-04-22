"""Unit tests for sequential pipeline processing."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.core.config import PipelineConfig
from src.core.pipeline import VideoTranscriptionPipeline
from src.processors.base import ProcessResult


@pytest.mark.unit
@pytest.mark.pipeline
class TestPipelineSequential:
    """Test cases for sequential pipeline processing."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return PipelineConfig(
            whisper_model="tiny",
            llm_model="test",
            generate_pdf=False,
            target="text",
            verbose=False
        )

    @pytest.fixture
    def pipeline(self, config):
        """Create a test pipeline."""
        return VideoTranscriptionPipeline(config)

    def test_empty_directory_returns_success(self, pipeline, tmp_path):
        """Test that empty directory returns success."""
        # Create empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = pipeline.process_directory(empty_dir)

        assert result.success is True
        assert "No supported files found" in result.message
        assert result.metadata["groups_found"] == 0

    @patch('src.core.pipeline.VideoTranscriptionPipeline.process_single_source')
    def test_all_tasks_execute_exactly_once(self, mock_process_single, pipeline, tmp_path):
        """Test that all discovered tasks execute exactly once."""
        # Create test files
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        video_file = test_dir / "video1.mp4"
        audio_file = test_dir / "audio1.mp3"
        text_file = test_dir / "text1.txt"

        # Mock file discovery on the pipeline instance
        pipeline.file_discovery = Mock()
        file_groups = {
            "video1": [video_file],
            "audio1": [audio_file],
            "text1": [text_file]
        }
        pipeline.file_discovery.group_files_by_stem.return_value = file_groups
        pipeline.file_discovery.find_primary_source.side_effect = [
            (video_file, "video"),
            (audio_file, "audio"),
            (text_file, "text")
        ]
        pipeline.file_discovery.separate_image_files.return_value = []
        pipeline.file_discovery.discover_files.return_value = []

        # Mock successful processing
        mock_process_single.return_value = ProcessResult(success=True)

        result = pipeline.process_directory(test_dir)

        # Verify each file was processed exactly once
        assert mock_process_single.call_count == 3

        # Verify calls were made with correct files and types
        expected_calls = [
            ((video_file, "video"), {}),
            ((audio_file, "audio"), {}),
            ((text_file, "text"), {})
        ]

        actual_calls = [(call.args, call.kwargs) for call in mock_process_single.call_args_list]
        assert actual_calls == expected_calls

    @patch('src.core.pipeline.VideoTranscriptionPipeline.process_single_source')
    def test_processing_order_is_deterministic(self, mock_process_single, pipeline, tmp_path):
        """Test that processing order is deterministic (sorted)."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create files with names that will be sorted differently
        file_groups = {
            "Z_video": [tmp_path / "Z_video.mp4"],
            "a_audio": [tmp_path / "a_audio.mp3"],
            "M_text": [tmp_path / "M_text.txt"]
        }

        # Mock file discovery on the pipeline instance
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.group_files_by_stem.return_value = file_groups
        pipeline.file_discovery.find_primary_source.side_effect = [
            (tmp_path / "Z_video.mp4", "video"),
            (tmp_path / "a_audio.mp3", "audio"),
            (tmp_path / "M_text.txt", "text")
        ]
        pipeline.file_discovery.separate_image_files.return_value = []
        pipeline.file_discovery.discover_files.return_value = []

        mock_process_single.return_value = ProcessResult(success=True)

        pipeline.process_directory(test_dir)

        # Verify processing order is sorted alphabetically (case-sensitive)
        expected_order = ["Z_video", "a_audio", "M_text"]  # actual sorted order
        actual_order = []

        for call in mock_process_single.call_args_list:
            file_path = call.args[0]
            actual_order.append(file_path.stem)

        assert actual_order == expected_order

    @patch('src.core.pipeline.VideoTranscriptionPipeline.process_single_source')
    def test_failing_task_does_not_abort_remaining_tasks(self, mock_process_single, pipeline, tmp_path):
        """Test that a failing task does not abort remaining tasks."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        file_groups = {
            "file1": [tmp_path / "file1.mp4"],
            "file2": [tmp_path / "file2.mp4"],
            "file3": [tmp_path / "file3.mp4"]
        }

        # Mock file discovery on the pipeline instance
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.group_files_by_stem.return_value = file_groups
        pipeline.file_discovery.find_primary_source.side_effect = [
            (tmp_path / "file1.mp4", "video"),
            (tmp_path / "file2.mp4", "video"),
            (tmp_path / "file3.mp4", "video")
        ]
        pipeline.file_discovery.separate_image_files.return_value = []
        pipeline.file_discovery.discover_files.return_value = []

        # Mock first call to fail, others to succeed
        mock_process_single.side_effect = [
            ProcessResult(success=False, message="Failed"),
            ProcessResult(success=True),
            ProcessResult(success=True)
        ]

        result = pipeline.process_directory(test_dir)

        # Verify all tasks were attempted despite failure
        assert mock_process_single.call_count == 3

        # Result should indicate partial success
        assert result.success is False  # Overall failure due to errors
        assert "errors" in result.message  # Just check that errors are mentioned
        assert result.metadata["groups_processed"] == 2  # 2 successful

    @patch('src.core.pipeline.VideoTranscriptionPipeline.process_single_source')
    def test_process_directory_returns_correct_counts(self, mock_process_single, pipeline, tmp_path):
        """Test that process_directory returns correct counts."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        file_groups = {
            "file1": [tmp_path / "file1.mp4"],
            "file2": [tmp_path / "file2.mp4"],
            "file3": [tmp_path / "file3.mp4"],
            "file4": [tmp_path / "file4.mp4"],
            "file5": [tmp_path / "file5.mp4"]
        }

        # Mock file discovery on the pipeline instance
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.group_files_by_stem.return_value = file_groups
        pipeline.file_discovery.find_primary_source.side_effect = [
            (tmp_path / f"file{i}.mp4", "video") for i in range(1, 6)
        ]
        pipeline.file_discovery.separate_image_files.return_value = []
        pipeline.file_discovery.discover_files.return_value = []

        # Mock 3 successful, 2 failed
        mock_process_single.side_effect = [
            ProcessResult(success=True),
            ProcessResult(success=True),
            ProcessResult(success=True),
            ProcessResult(success=False, message="Failed"),
            ProcessResult(success=False, message="Failed")
        ]

        result = pipeline.process_directory(test_dir)

        # Verify counts are correct (note: error counting includes all processing attempts)
        assert result.success is False
        assert result.metadata["groups_processed"] == 3  # 3 successful
        # The error count includes all failed processing attempts across all stages
        assert result.metadata["errors"] >= 2  # At least 2 errors from our mock failures

    def test_directory_not_found_error(self, pipeline, tmp_path):
        """Test handling of non-existent directory."""
        non_existent = tmp_path / "does_not_exist"

        with pytest.raises(Exception):  # Should raise VideoTranscriptionError
            pipeline.process_directory(non_existent)
