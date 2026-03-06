"""Unit tests for CLI functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from src.cli.main import VideoTranscriptionCLI
from src.core.config import PipelineConfig
from src.core.exceptions import ConfigurationError, VideoTranscriptionError


@pytest.mark.unit
@pytest.mark.cli
class TestVideoTranscriptionCLI:
    """Test cases for VideoTranscriptionCLI."""

    def test_init(self):
        """Test CLI initialization."""
        cli = VideoTranscriptionCLI()

        assert cli.pipeline is None
        assert cli.status_reporter is None

    def test_create_parser(self):
        """Test argument parser creation."""
        cli = VideoTranscriptionCLI()
        parser = cli.create_parser()

        # Test that all expected arguments are present
        args = parser.parse_args(["/tmp/test"])

        assert args.directory == Path("/tmp/test")
        assert args.verbose is False
        assert args.whisper_model == "medium"
        assert args.llm_model == "gemma3"

    def test_parse_config_file_success(self, temp_dir):
        """Test successful config file parsing."""
        cli = VideoTranscriptionCLI()

        # Create a test config file
        config_data = {
            "whisper_model": "tiny",
            "llm_model": "llama2"
        }
        config_path = temp_dir / "test_config.json"
        config_path.write_text(json.dumps(config_data))

        result = cli.parse_config_file(config_path)

        assert result["whisper_model"] == "tiny"
        assert result["llm_model"] == "llama2"

    def test_parse_config_file_not_found(self, temp_dir):
        """Test config file not found error."""
        cli = VideoTranscriptionCLI()
        non_existent_path = temp_dir / "non_existent.json"

        with pytest.raises(SystemExit):
            cli.parse_config_file(non_existent_path)

    def test_parse_config_file_invalid_json(self, temp_dir):
        """Test invalid JSON in config file."""
        cli = VideoTranscriptionCLI()
        config_path = temp_dir / "invalid.json"
        config_path.write_text("{ invalid json }")

        with pytest.raises(SystemExit):
            cli.parse_config_file(config_path)

    def test_create_config_success(self, mock_config):
        """Test successful configuration creation."""
        cli = VideoTranscriptionCLI()

        # Mock args
        mock_args = Mock()
        mock_args.directory = Path("/tmp/test")
        mock_args.whisper_model = "tiny"
        mock_args.llm_model = "llama2"
        mock_args.verbose = True
        mock_args.no_pdf = True
        mock_args.output_dir = Path("/tmp/output")

        config = cli.create_config(mock_args)

        assert config.whisper_model == "tiny"
        assert config.llm_model == "llama2"
        assert config.verbose is True
        assert config.generate_pdf is False
        assert config.output_dir == Path("/tmp/output")

    def test_create_config_missing_files(self, temp_dir, mock_config):
        """Test configuration error when required files are missing."""
        cli = VideoTranscriptionCLI()

        # Mock missing files
        mock_config.prompt_file = Path("/non_existent/prompt.txt")
        mock_config.header_file = Path("/non_existent/header.txt")

        with pytest.raises(SystemExit):
            cli.create_config(Mock())

    @patch('src.cli.main.VideoTranscriptionPipeline')
    def test_check_dependencies_all_available(self, mock_pipeline_class):
        """Test dependency checking when all dependencies are available."""
        cli = VideoTranscriptionCLI()
        mock_config = Mock()
        mock_config.generate_pdf = True

        result = cli.check_dependencies(mock_config)

        assert result is True

    @patch('src.cli.main.VideoTranscriptionPipeline')
    def test_check_dependencies_missing_whisper(self, mock_pipeline_class):
        """Test dependency checking when Whisper is missing."""
        cli = VideoTranscriptionCLI()
        mock_config = Mock()

        # Mock import error
        def import_error():
            raise ImportError("No module named 'whisper'")

        with patch('builtins.__import__', side_effect=import_error):
            result = cli.check_dependencies(mock_config)

            assert result is False

    def test_validate_input_directory_success(self, temp_dir):
        """Test successful directory validation."""
        cli = VideoTranscriptionCLI()

        # Create test directory
        test_dir = temp_dir / "test_input"
        test_dir.mkdir()

        result = cli.validate_input_directory(test_dir)

        assert result is True

    def test_validate_input_directory_not_found(self, temp_dir):
        """Test directory validation when directory doesn't exist."""
        cli = VideoTranscriptionCLI()

        non_existent_dir = temp_dir / "non_existent"

        result = cli.validate_input_directory(non_existent_dir)

        assert result is False

    def test_validate_input_directory_not_directory(self, temp_dir):
        """Test directory validation when path is not a directory."""
        cli = VideoTranscriptionCLI()

        # Create a file instead of directory
        test_file = temp_dir / "not_a_directory.txt"
        test_file.write_text("test")

        result = cli.validate_input_directory(test_file)

        assert result is False
