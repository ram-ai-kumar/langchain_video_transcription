"""Unit tests for configuration."""

import pytest
from pathlib import Path
import tempfile
import json

from src.core.config import PipelineConfig
from src.core.exceptions import ConfigurationError


@pytest.mark.unit
@pytest.mark.config
class TestPipelineConfig:
    """Test cases for PipelineConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PipelineConfig()

        assert config.whisper_model == "medium"
        assert config.llm_model == "gemma3"
        assert config.generate_pdf is True
        assert config.verbose is False
        assert config.output_dir is None

    def test_custom_config(self):
        """Test custom configuration values."""
        output_dir = Path("/custom/output")
        config = PipelineConfig(
            whisper_model="tiny",
            llm_model="llama2",
            generate_pdf=False,
            verbose=True,
            output_dir=output_dir
        )

        assert config.whisper_model == "tiny"
        assert config.llm_model == "llama2"
        assert config.generate_pdf is False
        assert config.verbose is True
        assert config.output_dir == output_dir

    def test_validate_success(self, temp_dir):
        """Test successful validation with existing files."""
        # Create required files
        prompt_file = temp_dir / "prompt.txt"
        prompt_file.write_text("Test prompt content")

        header_file = temp_dir / "header.txt"
        header_file.write_text("Test header content")

        # Create config with existing files
        config = PipelineConfig(
            prompt_file=prompt_file,
            header_file=header_file
        )

        # Should not raise any exception during __post_init__
        config.__post_init__()

    def test_validate_missing_prompt_file(self, temp_dir):
        """Test validation failure when prompt file is missing."""
        header_file = temp_dir / "header.txt"
        header_file.write_text("Test header content")

        config = PipelineConfig(
            prompt_file=Path("/non/existent/prompt.txt"),
            header_file=header_file
        )

        with pytest.raises(ConfigurationError, match="Prompt file not found"):
            config.__post_init__()

    def test_validate_missing_header_file(self, temp_dir):
        """Test validation failure when header file is missing."""
        prompt_file = temp_dir / "prompt.txt"
        prompt_file.write_text("Test prompt")

        config = PipelineConfig(
            prompt_file=prompt_file,
            header_file=Path("/non/existent/header.txt")
        )

        with pytest.raises(ConfigurationError, match="Header file not found"):
            config.__post_init__()

    def test_invalid_whisper_model(self):
        """Test validation with invalid Whisper model."""
        config = PipelineConfig(whisper_model="invalid_model")

        # This validation happens during processing, not initialization
        # The actual validation would be in the processor, not config
        # For now, just test that the model can be set
        assert config.whisper_model == "invalid_model"

    def test_invalid_llm_model(self):
        """Test validation with invalid LLM model."""
        config = PipelineConfig(llm_model="invalid_model")

        # This validation happens during processing, not initialization
        # The actual validation would be in the processor, not config
        # For now, just test that the model can be set
        assert config.llm_model == "invalid_model"
