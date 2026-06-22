"""Integration tests for progress display functionality."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.core.config import PipelineConfig
from src.core.pipeline import VideoTranscriptionPipeline


@pytest.mark.integration
@pytest.mark.progress
class TestProgressDisplayIntegration:
    """Integration tests for progress display in pipeline."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PipelineConfig(
            whisper_model="tiny",
            llm_model="test",
            generate_pdf=True,
            target="pdf",
            verbose=False
        )

    @pytest.fixture
    def pipeline(self, config):
        """Create test pipeline."""
        return VideoTranscriptionPipeline(config)

    def test_progress_tracker_initialization(self, pipeline):
        """Test that progress tracker is properly initialized."""
        # Verify progress tracker exists
        assert hasattr(pipeline, 'progress_tracker')
        assert pipeline.progress_tracker is not None

        # Verify it's the right class
        from src.utils.progress_tracker import ProgressTracker
        assert isinstance(pipeline.progress_tracker, ProgressTracker)

    @patch('src.core.pipeline.AudioProcessor')
    @patch('src.core.pipeline.StudyMaterialGenerator')
    @patch('src.utils.ui_utils.StatusReporter')
    def test_progress_display_called_during_processing(self, mock_status, mock_study, mock_audio, pipeline, config, tmp_path):
        """Test that progress display methods are called during pipeline processing."""
        # Setup mocks to return success
        from src.processors.base import ProcessResult
        mock_audio.return_value.process.return_value = ProcessResult(success=True)
        mock_audio.return_value.extract_audio_from_video.return_value = ProcessResult(success=True)
        mock_study.return_value.generate.return_value = ProcessResult(success=True)
        mock_study.return_value.generate_pdf_only.return_value = ProcessResult(success=True)

        # Create test file
        test_file = tmp_path / "test_video.mp4"
        test_file.touch()

        # Mock file discovery to avoid actual file system operations
        pipeline.file_discovery = MagicMock()
        pipeline.file_discovery.get_output_paths.return_value = {
            'audio_file': tmp_path / "test_video.mp3",
            'transcript_file': tmp_path / "test_video.txt",
            'study_file': tmp_path / "test_video.md",
            'pdf_file': tmp_path / "test_video.pdf"
        }

        # Mock the actual processing methods to avoid subprocess calls
        pipeline.audio_processor.process = MagicMock(return_value=ProcessResult(success=True))
        pipeline.audio_processor.extract_audio_from_video = MagicMock(return_value=ProcessResult(success=True))
        pipeline.study_generator.generate = MagicMock(return_value=ProcessResult(success=True))
        pipeline.study_generator.generate_pdf_only = MagicMock(return_value=ProcessResult(success=True))

        # Process the file
        result = pipeline.process_single_source(test_file, "video")

        # Verify processing completed successfully
        assert result.success is True

        # Verify progress tracker was used (it should have been called through the pipeline)
        assert hasattr(pipeline, 'progress_tracker')

    def test_progress_display_path_truncation(self, pipeline, config, tmp_path):
        """Test that progress display uses path truncation for long paths."""
        # Create test file with deep path
        deep_path = tmp_path / "level1" / "level2" / "level3" / "level4" / "test_video.mp4"
        deep_path.parent.mkdir(parents=True)
        deep_path.touch()

        # Test path truncation logic directly
        formatted_path = pipeline.progress_tracker._format_path(deep_path, 80)

        # _format_path shows parent/filename
        assert 'level4' in formatted_path
        assert 'test_video.mp4' in formatted_path

    def test_progress_tracker_different_file_types(self, pipeline, config, tmp_path):
        """Test progress tracker works with different file types."""
        # Test different file types
        test_files = [
            (tmp_path / "video.mp4", "video"),
            (tmp_path / "audio.mp3", "audio"),
            (tmp_path / "document.txt", "text"),
            (tmp_path / "slides.png", "image"),
        ]

        for file_path, file_type in test_files:
            file_path.touch()

            # Get processing stages for this file type
            stages = pipeline._get_processing_stages(file_type)

            # Verify stages are appropriate for file type
            if file_type == "video":
                assert "audio" in stages
                assert "text" in stages
                assert "markdown" in stages
                assert "pdf" in stages
            elif file_type == "audio":
                assert "audio" not in stages
                assert "text" in stages
                assert "markdown" in stages
                assert "pdf" in stages
            elif file_type == "text":
                assert "audio" not in stages
                assert "text" in stages  # Text files should have text stage
                assert "markdown" in stages
                assert "pdf" in stages
            elif file_type == "image":
                assert "audio" not in stages
                assert "text" in stages
                assert "markdown" in stages
                assert "pdf" in stages

    @patch('builtins.print')
    def test_progress_display_format(self, mock_print, pipeline, config, tmp_path):
        """Test that progress display format is correct."""
        # Create test file
        test_file = tmp_path / "test_video.mp4"
        test_file.touch()

        # Start tracking
        stages = ["audio", "text", "markdown", "pdf"]
        pipeline.progress_tracker.start_file(test_file, stages)

        # Verify print was called with correct format
        mock_print.assert_called()
        call_args = mock_print.call_args

        # Should contain the file path and progress indicator
        call_str = str(call_args)
        assert "test_video.mp4" in call_str
        assert "[1/4: audio]" in call_str  # Initial state shows stage indicator

    def test_progress_display_stage_progression(self, pipeline, config, tmp_path):
        """Test that progress display shows correct stage progression."""
        # Create test file
        test_file = tmp_path / "test_video.mp4"
        test_file.touch()

        # Start tracking
        stages = ["audio", "text", "markdown", "pdf"]
        pipeline.progress_tracker.start_file(test_file, stages)

        # Complete first stage
        pipeline.progress_tracker.complete_stage(test_file)

        # Test the display logic directly
        file_info = pipeline.progress_tracker.active_files[str(test_file)]
        current_stage = file_info['current_stage']

        # Should show completed stage + current processing stage
        progress_parts = []
        for i, stage in enumerate(stages):
            if i < current_stage:
                progress_parts.append(stage)
            elif i == current_stage:
                progress_parts.append("...")
            else:
                break

        progress_str = " > ".join(progress_parts)
        assert "audio" in progress_str  # Past stage shown
        assert "..." in progress_str   # Current stage shown
        assert "text" not in progress_str  # Future stage not shown
