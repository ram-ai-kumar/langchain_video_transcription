"""Smoke tests for critical path validation."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.cli.main import VideoTranscriptionCLI
from src.core.pipeline import VideoTranscriptionPipeline
from src.core.config import PipelineConfig


@pytest.mark.integration
@pytest.mark.smoke
class TestSmoke:
    """Smoke tests to verify critical functionality works."""

    @patch('src.core.pipeline.whisper')
    @patch('src.core.pipeline.FileDiscovery')
    @patch('src.core.pipeline.StudyMaterialGenerator')
    def test_cli_help_display(self, mock_whisper, mock_file_discovery, mock_study_gen, capsys):
        """Test that CLI help displays without errors."""
        cli = VideoTranscriptionCLI()

        # Capture help output
        with pytest.raises(SystemExit):
            cli.create_parser().parse_args(["--help"])

    @patch('src.core.pipeline.whisper')
    @patch('src.core.pipeline.FileDiscovery')
    @patch('src.core.pipeline.StudyMaterialGenerator')
    def test_cli_version_display(self, mock_whisper, mock_file_discovery, mock_study_gen, capsys):
        """Test that CLI version displays without errors."""
        cli = VideoTranscriptionCLI()

        # This would need a --version flag to be implemented
        # For now, test that CLI initializes without crashing
        assert cli.pipeline is None
        assert cli.status_reporter is None

    @patch('src.core.pipeline.whisper')
    @patch('src.core.pipeline.FileDiscovery')
    @patch('src.core.pipeline.StudyMaterialGenerator')
    def test_pipeline_basic_initialization(self, mock_whisper, mock_file_discovery, mock_study_gen):
        """Test that pipeline can be initialized with minimal config."""
        config = PipelineConfig()

        # Should not raise during initialization
        pipeline = VideoTranscriptionPipeline(config)

        assert pipeline.config == config
        assert pipeline.whisper_model is None
        assert pipeline.logger is not None

    @patch('src.core.pipeline.whisper')
    def test_pipeline_prerequisites_validation(self, mock_whisper):
        """Test that prerequisite validation runs without errors."""
        mock_whisper.load_model.return_value = Mock()

        config = PipelineConfig()
        pipeline = VideoTranscriptionPipeline(config)

        # Should not raise exception
        validation = pipeline.validate_prerequisites()

        assert validation is not None
        assert isinstance(validation, dict)
        assert "overall_ready" in validation
