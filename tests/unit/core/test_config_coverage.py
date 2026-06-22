"""Comprehensive tests for config.py to achieve 100% coverage."""

import pytest
from pathlib import Path

from src.core.config import PipelineConfig
from src.core.exceptions import ConfigurationError


@pytest.fixture
def files(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Test prompt")
    header = tmp_path / "header.tex"
    header.write_text("Test header")
    return prompt, header


class TestDefaultConfig:
    def test_default_values(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.llm_model == "qwen2.5-coder:latest"
        assert config.whisper_model == "medium"
        assert config.generate_pdf is True
        assert config.target == "pdf"
        assert config.output_dir is None
        assert config.ffmpeg_audio_quality == 2
        assert config.ocr_language == "eng"
        assert config.transcription_language == "en"
        assert config.device is None
        assert config.verbose is False

    def test_default_extensions(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert ".mp4" in config.video_extensions
        assert ".mkv" in config.video_extensions
        assert ".mp3" in config.audio_extensions
        assert ".wav" in config.audio_extensions
        assert ".txt" in config.text_extensions
        assert ".png" in config.image_extensions
        assert ".jpg" in config.image_extensions

    def test_default_paths(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.prompt_file == prompt
        assert config.header_file == header


class TestPostInit:
    def test_missing_prompt_file(self, tmp_path):
        header = tmp_path / "header.tex"
        header.write_text("header")
        with pytest.raises(ConfigurationError, match="Prompt file not found"):
            PipelineConfig(
                prompt_file=Path("/non/existent/prompt.md"),
                header_file=header,
            )

    def test_missing_header_file(self, tmp_path):
        prompt = tmp_path / "prompt.md"
        prompt.write_text("prompt")
        with pytest.raises(ConfigurationError, match="Header file not found"):
            PipelineConfig(
                prompt_file=prompt,
                header_file=Path("/non/existent/header.tex"),
            )


class TestGetAllExtensions:
    def test_all_extensions(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        all_ext = config.get_all_extensions()
        assert ".mp4" in all_ext
        assert ".mp3" in all_ext
        assert ".txt" in all_ext
        assert ".png" in all_ext
        assert len(all_ext) == len(config.video_extensions) + len(config.audio_extensions) + len(config.text_extensions) + len(config.image_extensions)


class TestIsVideoFile:
    def test_mp4(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_video_file(Path("test.mp4")) is True

    def test_mkv(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_video_file(Path("test.mkv")) is True

    def test_non_video(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_video_file(Path("test.txt")) is False

    def test_case_insensitive(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_video_file(Path("test.MP4")) is True


class TestIsAudioFile:
    def test_mp3(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_audio_file(Path("test.mp3")) is True

    def test_wav(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_audio_file(Path("test.wav")) is True

    def test_non_audio(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_audio_file(Path("test.mp4")) is False

    def test_case_insensitive(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_audio_file(Path("test.WAV")) is True


class TestIsTextFile:
    def test_txt(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_text_file(Path("test.txt")) is True

    def test_non_text(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_text_file(Path("test.mp4")) is False

    def test_case_insensitive(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_text_file(Path("test.TXT")) is True


class TestIsImageFile:
    def test_png(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_image_file(Path("test.png")) is True

    def test_jpg(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_image_file(Path("test.jpg")) is True

    def test_jpeg(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_image_file(Path("test.jpeg")) is True

    def test_webp(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_image_file(Path("test.webp")) is True

    def test_non_image(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_image_file(Path("test.txt")) is False

    def test_case_insensitive(self, files):
        prompt, header = files
        config = PipelineConfig(prompt_file=prompt, header_file=header)
        assert config.is_image_file(Path("test.PNG")) is True


class TestCustomConfig:
    def test_custom_values(self, files):
        prompt, header = files
        config = PipelineConfig(
            prompt_file=prompt,
            header_file=header,
            whisper_model="tiny",
            llm_model="llama2",
            generate_pdf=False,
            target="text",
            verbose=True,
            ffmpeg_audio_quality=4,
            ocr_language="fra",
            transcription_language="fr",
            device="cpu",
        )
        assert config.whisper_model == "tiny"
        assert config.llm_model == "llama2"
        assert config.generate_pdf is False
        assert config.target == "text"
        assert config.verbose is True
        assert config.ffmpeg_audio_quality == 4
        assert config.ocr_language == "fra"
        assert config.transcription_language == "fr"
        assert config.device == "cpu"

    def test_custom_extensions(self, files):
        prompt, header = files
        config = PipelineConfig(
            prompt_file=prompt,
            header_file=header,
            video_extensions=[".mp4", ".webm"],
            audio_extensions=[".flac"],
        )
        assert ".webm" in config.video_extensions
        assert ".flac" in config.audio_extensions
        assert ".mkv" not in config.video_extensions
