"""Comprehensive tests for pipeline.py to achieve 100% coverage."""

import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.core.pipeline import VideoTranscriptionPipeline, setup_logging
from src.core.config import PipelineConfig
from src.core.exceptions import VideoTranscriptionError, ProcessingError
from src.processors.base import ProcessResult


@pytest.fixture
def config(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Test prompt")
    header = tmp_path / "header.tex"
    header.write_text("Test header")
    return PipelineConfig(
        prompt_file=prompt,
        header_file=header,
        whisper_model="tiny",
        llm_model="test",
        generate_pdf=False,
        target="text",
        verbose=False,
    )


@pytest.fixture
def pipeline(config):
    return VideoTranscriptionPipeline(config)


class TestSetupLogging:
    def test_setup_logging_default(self):
        setup_logging(verbose=False)
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_setup_logging_verbose(self):
        setup_logging(verbose=True)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_setup_logging_clears_handlers(self):
        setup_logging(verbose=False)
        root = logging.getLogger()
        assert len(root.handlers) >= 1


class TestProcessPath:
    def test_process_path_file(self, pipeline, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("test content")
        with patch.object(pipeline, 'process_single_file', return_value=ProcessResult(success=True)) as mock_f:
            result = pipeline.process_path(f)
            assert result.success is True
            mock_f.assert_called_once()

    def test_process_path_directory(self, pipeline, tmp_path):
        d = tmp_path / "testdir"
        d.mkdir()
        with patch.object(pipeline, 'process_directory', return_value=ProcessResult(success=True)) as mock_d:
            result = pipeline.process_path(d)
            assert result.success is True
            mock_d.assert_called_once()

    def test_process_path_nonexistent(self, pipeline, tmp_path):
        non_existent = tmp_path / "nonexistent"
        result = pipeline.process_path(non_existent)
        assert result.success is False
        assert "neither a file nor a directory" in result.message


class TestProcessSingleFile:
    def test_process_single_file_not_found(self, pipeline, tmp_path):
        non_existent = tmp_path / "nonexistent.txt"
        result = pipeline.process_single_file(non_existent)
        assert result.success is False
        assert "Failed to process file" in result.message

    @patch('src.core.pipeline.VideoTranscriptionPipeline._process_media_groups')
    @patch('src.core.pipeline.VideoTranscriptionPipeline._process_image_groups')
    def test_process_single_file_success(self, mock_img, mock_media, pipeline, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("test content")
        mock_media.return_value = 1
        mock_img.return_value = 0
        result = pipeline.process_single_file(f)
        assert result.success is True
        assert result.metadata["items_processed"] == 1

    @patch('src.core.pipeline.VideoTranscriptionPipeline._process_media_groups')
    @patch('src.core.pipeline.VideoTranscriptionPipeline._process_image_groups')
    def test_process_single_file_with_errors(self, mock_img, mock_media, pipeline, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("test content")
        mock_media.return_value = 0
        mock_img.return_value = 0
        pipeline.error_summary["test_error"] = 1
        result = pipeline.process_single_file(f)
        assert result.success is False
        assert "errors" in result.message
        pipeline.error_summary.clear()


class TestProcessDirectory:
    def test_empty_directory(self, pipeline, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        result = pipeline.process_directory(d)
        assert result.success is True
        assert "No supported files found" in result.message

    def test_directory_not_found(self, pipeline, tmp_path):
        non_existent = tmp_path / "nonexistent"
        with pytest.raises(VideoTranscriptionError):
            pipeline.process_directory(non_existent)

    @patch('src.core.pipeline.VideoTranscriptionPipeline._process_media_groups')
    @patch('src.core.pipeline.VideoTranscriptionPipeline._process_image_groups')
    @patch('src.core.pipeline.VideoTranscriptionPipeline._process_loose_images')
    def test_directory_success(self, mock_loose, mock_img, mock_media, pipeline, tmp_path):
        d = tmp_path / "testdir"
        d.mkdir()
        f = d / "test.txt"
        f.write_text("test content")
        mock_media.return_value = 1
        mock_img.return_value = 0
        mock_loose.return_value = 0
        result = pipeline.process_directory(d)
        assert result.success is True
        assert result.metadata["groups_processed"] == 1


class TestProcessMediaGroups:
    def test_process_media_groups_success(self, pipeline, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        file_groups = {"test": [f]}
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.find_primary_source.return_value = (f, "text")
        with patch.object(pipeline, 'process_single_source', return_value=ProcessResult(success=True)):
            count = pipeline._process_media_groups(file_groups, tmp_path)
        assert count == 1

    def test_process_media_groups_failure(self, pipeline, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        file_groups = {"test": [f]}
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.find_primary_source.return_value = (f, "text")
        with patch.object(pipeline, 'process_single_source', return_value=ProcessResult(success=False, message="Failed")):
            count = pipeline._process_media_groups(file_groups, tmp_path)
        assert count == 0
        assert "text_processing" in pipeline.error_summary

    def test_process_media_groups_exception(self, pipeline, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        file_groups = {"test": [f]}
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.find_primary_source.return_value = (f, "text")
        with patch.object(pipeline, 'process_single_source', side_effect=Exception("Boom")):
            count = pipeline._process_media_groups(file_groups, tmp_path)
        assert count == 0
        assert "text_error" in pipeline.error_summary

    def test_process_media_groups_no_source(self, pipeline, tmp_path):
        f = tmp_path / "test.txt"
        file_groups = {"test": [f]}
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.find_primary_source.return_value = (None, None)
        count = pipeline._process_media_groups(file_groups, tmp_path)
        assert count == 0


class TestProcessImageGroups:
    def test_process_image_groups_no_images(self, pipeline, tmp_path):
        f = tmp_path / "test.txt"
        file_groups = {"test": [f]}
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.separate_image_files.return_value = []
        count = pipeline._process_image_groups(file_groups, tmp_path)
        assert count == 0

    def test_process_image_groups_success(self, pipeline, tmp_path):
        img = tmp_path / "slide1.png"
        img.write_bytes(b"fake image")
        file_groups = {"test": [img]}
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.separate_image_files.return_value = [img]
        with patch.object(pipeline, 'image_processor') as mock_img_proc, \
             patch.object(pipeline, 'process_single_source', return_value=ProcessResult(success=True)):
            mock_img_proc.process.return_value = ProcessResult(success=True)
            count = pipeline._process_image_groups(file_groups, tmp_path)
        assert count == 1

    def test_process_image_groups_transcript_exists(self, pipeline, tmp_path):
        img = tmp_path / "slide1.png"
        img.write_bytes(b"fake image")
        transcript = tmp_path / "test.txt"
        transcript.write_text("existing transcript")
        file_groups = {"test": [img]}
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.separate_image_files.return_value = [img]
        with patch.object(pipeline, 'process_single_source', return_value=ProcessResult(success=True)):
            count = pipeline._process_image_groups(file_groups, tmp_path)
        assert count == 1

    def test_process_image_groups_image_processing_fails(self, pipeline, tmp_path):
        img = tmp_path / "slide1.png"
        img.write_bytes(b"fake image")
        file_groups = {"test": [img]}
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.separate_image_files.return_value = [img]
        with patch.object(pipeline, 'image_processor') as mock_img_proc:
            mock_img_proc.process.return_value = ProcessResult(success=False, message="OCR failed")
            count = pipeline._process_image_groups(file_groups, tmp_path)
        assert count == 0
        assert "image_processing" in pipeline.error_summary

    def test_process_image_groups_study_generation_fails(self, pipeline, tmp_path):
        img = tmp_path / "slide1.png"
        img.write_bytes(b"fake image")
        file_groups = {"test": [img]}
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.separate_image_files.return_value = [img]
        with patch.object(pipeline, 'image_processor') as mock_img_proc, \
             patch.object(pipeline, 'process_single_source', return_value=ProcessResult(success=False, message="Study gen failed")):
            mock_img_proc.process.return_value = ProcessResult(success=True)
            count = pipeline._process_image_groups(file_groups, tmp_path)
        assert count == 0
        assert "study_generation" in pipeline.error_summary

    def test_process_image_groups_exception(self, pipeline, tmp_path):
        img = tmp_path / "slide1.png"
        img.write_bytes(b"fake image")
        file_groups = {"test": [img]}
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.separate_image_files.return_value = [img]
        with patch.object(pipeline, 'image_processor') as mock_img_proc:
            mock_img_proc.process.side_effect = Exception("Boom")
            count = pipeline._process_image_groups(file_groups, tmp_path)
        assert count == 0
        assert "image_error" in pipeline.error_summary


class TestProcessLooseImages:
    def test_no_loose_images(self, pipeline, tmp_path):
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.discover_files.return_value = []
        pipeline.config = Mock()
        pipeline.config.is_image_file.return_value = False
        count = pipeline._process_loose_images(tmp_path)
        assert count == 0

    def test_all_images_already_processed(self, pipeline, tmp_path):
        img = tmp_path / "slide1.png"
        img.write_bytes(b"fake")
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.discover_files.return_value = [img]
        pipeline.config = Mock()
        pipeline.config.is_image_file.return_value = True
        pipeline.processed_stems.add("slide1")
        count = pipeline._process_loose_images(tmp_path)
        assert count == 0

    def test_loose_images_success(self, pipeline, tmp_path):
        img = tmp_path / "slide1.png"
        img.write_bytes(b"fake")
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.discover_files.return_value = [img]
        pipeline.config = Mock()
        pipeline.config.is_image_file.return_value = True
        with patch.object(pipeline, 'image_processor') as mock_img_proc, \
             patch.object(pipeline, 'process_single_source', return_value=ProcessResult(success=True)):
            mock_img_proc.process.return_value = ProcessResult(success=True)
            count = pipeline._process_loose_images(tmp_path)
        assert count == 1

    def test_loose_images_transcript_exists(self, pipeline, tmp_path):
        img = tmp_path / "slide1.png"
        img.write_bytes(b"fake")
        transcript = tmp_path / f"{tmp_path.name}.txt"
        transcript.write_text("existing")
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.discover_files.return_value = [img]
        pipeline.config = Mock()
        pipeline.config.is_image_file.return_value = True
        with patch.object(pipeline, 'process_single_source', return_value=ProcessResult(success=True)):
            count = pipeline._process_loose_images(tmp_path)
        assert count == 1

    def test_loose_images_processing_fails(self, pipeline, tmp_path):
        img = tmp_path / "slide1.png"
        img.write_bytes(b"fake")
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.discover_files.return_value = [img]
        pipeline.config = Mock()
        pipeline.config.is_image_file.return_value = True
        with patch.object(pipeline, 'image_processor') as mock_img_proc:
            mock_img_proc.process.return_value = ProcessResult(success=False, message="Failed")
            count = pipeline._process_loose_images(tmp_path)
        assert count == 0
        assert "loose_image_processing" in pipeline.error_summary

    def test_loose_images_study_gen_fails(self, pipeline, tmp_path):
        img = tmp_path / "slide1.png"
        img.write_bytes(b"fake")
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.discover_files.return_value = [img]
        pipeline.config = Mock()
        pipeline.config.is_image_file.return_value = True
        with patch.object(pipeline, 'image_processor') as mock_img_proc, \
             patch.object(pipeline, 'process_single_source', return_value=ProcessResult(success=False, message="Study failed")):
            mock_img_proc.process.return_value = ProcessResult(success=True)
            count = pipeline._process_loose_images(tmp_path)
        assert count == 0
        assert "study_generation" in pipeline.error_summary

    def test_loose_images_exception(self, pipeline, tmp_path):
        img = tmp_path / "slide1.png"
        img.write_bytes(b"fake")
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.discover_files.return_value = [img]
        pipeline.config = Mock()
        pipeline.config.is_image_file.return_value = True
        with patch.object(pipeline, 'image_processor') as mock_img_proc:
            mock_img_proc.process.side_effect = Exception("Boom")
            count = pipeline._process_loose_images(tmp_path)
        assert count == 0
        assert "loose_image_error" in pipeline.error_summary


class TestMigrateLegacyFiles:
    def test_no_migration_needed(self, pipeline, tmp_path):
        source = tmp_path / "test.txt"
        source.write_text("content")
        paths = {"audio_file": tmp_path / "test.mp3"}
        pipeline._migrate_legacy_unsanitized_files(source, paths)
        # Should not raise or rename anything

    def test_migration_with_unicode_stem(self, pipeline, tmp_path):
        source = tmp_path / "Test\u202fFile.txt"
        source.write_text("content")
        sanitized_audio = tmp_path / "Test File.mp3"
        legacy_audio = tmp_path / "Test\u202fFile.mp3"
        legacy_audio.write_bytes(b"audio")
        paths = {"audio_file": sanitized_audio, "transcript_file": None, "study_file": None, "pdf_file": None}
        pipeline._migrate_legacy_unsanitized_files(source, paths)
        assert sanitized_audio.exists()
        assert not legacy_audio.exists()


class TestGetProcessingStages:
    def test_video_stages_with_pdf(self, config):
        config.generate_pdf = True
        config.target = "pdf"
        pipeline = VideoTranscriptionPipeline(config)
        stages = pipeline._get_processing_stages("video")
        assert "audio" in stages
        assert "text" in stages
        assert "markdown" in stages
        assert "pdf" in stages

    def test_video_stages_without_pdf(self, config):
        config.generate_pdf = False
        config.target = "markdown"
        pipeline = VideoTranscriptionPipeline(config)
        stages = pipeline._get_processing_stages("video")
        assert "audio" in stages
        assert "text" in stages
        assert "markdown" in stages
        assert "pdf" not in stages

    def test_audio_stages(self, config):
        config.generate_pdf = False
        config.target = "text"
        pipeline = VideoTranscriptionPipeline(config)
        stages = pipeline._get_processing_stages("audio")
        assert "audio" not in stages
        assert "text" in stages

    def test_text_stages(self, config):
        config.generate_pdf = False
        config.target = "text"
        pipeline = VideoTranscriptionPipeline(config)
        stages = pipeline._get_processing_stages("text")
        assert "text" in stages

    def test_image_stages(self, config):
        config.generate_pdf = False
        config.target = "markdown"
        pipeline = VideoTranscriptionPipeline(config)
        stages = pipeline._get_processing_stages("images")
        assert "text" in stages
        assert "markdown" in stages

    def test_target_markdown_with_pdf(self, config):
        config.generate_pdf = True
        config.target = "markdown"
        pipeline = VideoTranscriptionPipeline(config)
        stages = pipeline._get_processing_stages("video")
        assert "pdf" not in stages


class TestProcessSingleSource:
    def test_process_text_target_text(self, pipeline, tmp_path):
        """Test processing a text file with target=text."""
        f = tmp_path / "test.txt"
        f.write_text("test content")
        with patch.object(pipeline, 'text_processor') as mock_tp:
            mock_tp.process.return_value = ProcessResult(success=True)
            result = pipeline.process_single_source(f, "text")
        assert result.success is True
        assert result.metadata["target_reached"] == "text"

    def test_process_video_target_audio(self, config, tmp_path):
        """Test early exit when target is 'audio'."""
        config.target = "audio"
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.mp4"
        f.write_bytes(b"fake video")
        with patch.object(pipeline, 'audio_processor') as mock_ap:
            mock_ap.extract_audio_from_video.return_value = ProcessResult(success=True)
            result = pipeline.process_single_source(f, "video")
        assert result.success is True
        assert result.metadata["target_reached"] == "audio"

    def test_process_video_audio_extraction_fails(self, config, tmp_path):
        """Test video processing when audio extraction fails."""
        config.target = "pdf"
        config.generate_pdf = False
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.mp4"
        f.write_bytes(b"fake video")
        with patch.object(pipeline, 'audio_processor') as mock_ap:
            mock_ap.extract_audio_from_video.return_value = ProcessResult(success=False, message="Failed")
            result = pipeline.process_single_source(f, "video")
        assert result.success is False

    def test_process_video_audio_exists(self, config, tmp_path):
        """Test video processing when audio file already exists."""
        config.target = "audio"
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.mp4"
        f.write_bytes(b"fake video")
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"fake audio")
        result = pipeline.process_single_source(f, "video")
        assert result.success is True
        assert result.metadata["target_reached"] == "audio"

    def test_process_text_transcription_fails(self, config, tmp_path):
        """Test text processing when transcription fails."""
        config.target = "pdf"
        config.generate_pdf = False
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.txt"
        f.write_text("content")
        with patch.object(pipeline, 'text_processor') as mock_tp:
            mock_tp.process.return_value = ProcessResult(success=False, message="Failed")
            result = pipeline.process_single_source(f, "text")
        assert result.success is False

    def test_process_audio_transcription_fails(self, config, tmp_path):
        """Test audio processing when transcription fails."""
        config.target = "pdf"
        config.generate_pdf = False
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.wav"
        f.write_bytes(b"fake audio")
        with patch.object(pipeline, 'audio_processor') as mock_ap:
            mock_ap.process.return_value = ProcessResult(success=False, message="Failed")
            result = pipeline.process_single_source(f, "audio")
        assert result.success is False

    def test_process_text_target_markdown(self, config, tmp_path):
        """Test text processing with target=markdown."""
        config.target = "markdown"
        config.generate_pdf = False
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.txt"
        f.write_text("content")
        transcript = tmp_path / "test.txt"
        study = tmp_path / "test.md"
        study.write_text("study content")
        with patch.object(pipeline, 'text_processor') as mock_tp, \
             patch.object(pipeline, 'study_generator') as mock_sg:
            mock_tp.process.return_value = ProcessResult(success=True)
            mock_sg.generate.return_value = ProcessResult(success=True, output_path=study)
            result = pipeline.process_single_source(f, "text")
        assert result.success is True
        assert result.metadata["target_reached"] == "markdown"

    def test_process_study_generation_fails(self, config, tmp_path):
        """Test when study material generation fails."""
        config.target = "pdf"
        config.generate_pdf = False
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.txt"
        f.write_text("content")
        with patch.object(pipeline, 'text_processor') as mock_tp, \
             patch.object(pipeline, 'study_generator') as mock_sg:
            mock_tp.process.return_value = ProcessResult(success=True)
            mock_sg.generate.return_value = ProcessResult(success=False, message="LLM failed")
            result = pipeline.process_single_source(f, "text")
        assert result.success is False

    def test_process_with_pdf_generation(self, config, tmp_path):
        """Test full pipeline including PDF generation."""
        config.target = "pdf"
        config.generate_pdf = True
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.txt"
        f.write_text("content")
        study = tmp_path / "test.md"
        study.write_text("study content")
        with patch.object(pipeline, 'text_processor') as mock_tp, \
             patch.object(pipeline, 'study_generator') as mock_sg:
            mock_tp.process.return_value = ProcessResult(success=True)
            mock_sg.generate.return_value = ProcessResult(success=True, output_path=study)
            mock_sg.generate_pdf_only.return_value = ProcessResult(success=True)
            result = pipeline.process_single_source(f, "text")
        assert result.success is True

    def test_process_target_pdf_but_no_pdf_generation(self, config, tmp_path):
        """Test target=pdf but generate_pdf=False - skips PDF, reaches line 551."""
        config.target = "pdf"
        config.generate_pdf = False
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.txt"
        f.write_text("content")
        study = tmp_path / "test.md"
        study.write_text("study content")
        with patch.object(pipeline, 'text_processor') as mock_tp, \
             patch.object(pipeline, 'study_generator') as mock_sg:
            mock_tp.process.return_value = ProcessResult(success=True)
            mock_sg.generate.return_value = ProcessResult(success=True, output_path=study)
            result = pipeline.process_single_source(f, "text")
        assert result.success is True

    def test_process_pdf_generation_fails(self, config, tmp_path):
        """Test when PDF generation fails (should still succeed)."""
        config.target = "pdf"
        config.generate_pdf = True
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.txt"
        f.write_text("content")
        study = tmp_path / "test.md"
        study.write_text("study content")
        with patch.object(pipeline, 'text_processor') as mock_tp, \
             patch.object(pipeline, 'study_generator') as mock_sg:
            mock_tp.process.return_value = ProcessResult(success=True)
            mock_sg.generate.return_value = ProcessResult(success=True, output_path=study)
            mock_sg.generate_pdf_only.return_value = ProcessResult(success=False, message="PDF failed")
            result = pipeline.process_single_source(f, "text")
        assert result.success is True

    def test_process_pdf_already_exists(self, config, tmp_path):
        """Test when PDF file already exists."""
        config.target = "pdf"
        config.generate_pdf = True
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.txt"
        f.write_text("content")
        study = tmp_path / "test.md"
        study.write_text("study content")
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        with patch.object(pipeline, 'text_processor') as mock_tp, \
             patch.object(pipeline, 'study_generator') as mock_sg:
            mock_tp.process.return_value = ProcessResult(success=True)
            mock_sg.generate.return_value = ProcessResult(success=True, output_path=study)
            result = pipeline.process_single_source(f, "text")
        assert result.success is True

    def test_process_transcript_already_exists(self, config, tmp_path):
        """Test when transcript file already exists."""
        config.target = "markdown"
        config.generate_pdf = False
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.txt"
        f.write_text("content")
        transcript = tmp_path / "test.txt"
        study = tmp_path / "test.md"
        study.write_text("study content")
        with patch.object(pipeline, 'study_generator') as mock_sg:
            mock_sg.generate.return_value = ProcessResult(success=True, output_path=study)
            result = pipeline.process_single_source(f, "text")
        assert result.success is True
        assert result.metadata["target_reached"] == "markdown"

    def test_process_study_already_exists(self, config, tmp_path):
        """Test when study file already exists."""
        config.target = "markdown"
        config.generate_pdf = False
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.txt"
        f.write_text("content")
        study = tmp_path / "test.md"
        study.write_text("study content")
        result = pipeline.process_single_source(f, "text")
        assert result.success is True
        assert result.metadata["target_reached"] == "markdown"

    def test_process_exception(self, pipeline, tmp_path):
        """Test exception handling in process_single_source."""
        f = tmp_path / "test.txt"
        f.write_text("content")
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.get_output_paths.side_effect = Exception("Boom")
        with pytest.raises(ProcessingError):
            pipeline.process_single_source(f, "text")

    def test_process_audio_target_text(self, config, tmp_path):
        """Test audio processing with target=text."""
        config.target = "text"
        config.generate_pdf = False
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "test.wav"
        f.write_bytes(b"fake audio")
        with patch.object(pipeline, 'audio_processor') as mock_ap:
            mock_ap.process.return_value = ProcessResult(success=True)
            result = pipeline.process_single_source(f, "audio")
        assert result.success is True
        assert result.metadata["target_reached"] == "text"

    def test_process_text_with_text_processor_when_transcript_missing(self, config, tmp_path):
        """Test text processing path when transcript doesn't exist and start_type is text."""
        config.target = "markdown"
        config.generate_pdf = False
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "source.txt"
        f.write_text("content")
        study = tmp_path / "source.md"
        study.write_text("study content")
        # Mock output paths so transcript_file doesn't exist
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.get_output_paths.return_value = {
            "audio_file": tmp_path / "source.mp3",
            "transcript_file": tmp_path / "transcript_output.txt",
            "study_file": study,
            "pdf_file": tmp_path / "source.pdf",
        }
        with patch.object(pipeline, 'text_processor') as mock_tp, \
             patch.object(pipeline, 'study_generator') as mock_sg:
            mock_tp.process.return_value = ProcessResult(success=True)
            mock_sg.generate.return_value = ProcessResult(success=True, output_path=study)
            result = pipeline.process_single_source(f, "text")
        assert result.success is True

    def test_process_text_with_text_processor_fails(self, config, tmp_path):
        """Test text processing path when text_processor fails (lines 494-497)."""
        config.target = "text"
        config.generate_pdf = False
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "source.txt"
        f.write_text("content")
        # Mock output paths so transcript_file doesn't exist
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.get_output_paths.return_value = {
            "audio_file": tmp_path / "source.mp3",
            "transcript_file": tmp_path / "transcript_output.txt",  # Different from source
            "study_file": tmp_path / "source.md",
            "pdf_file": tmp_path / "source.pdf",
        }
        with patch.object(pipeline, 'text_processor') as mock_tp:
            mock_tp.process.return_value = ProcessResult(success=False, message="Text processing failed")
            result = pipeline.process_single_source(f, "text")
        assert result.success is False

    def test_process_images_start_type(self, config, tmp_path):
        """Test processing with start_type='images' uses text_processor."""
        config.target = "text"
        config.generate_pdf = False
        pipeline = VideoTranscriptionPipeline(config)
        f = tmp_path / "source.txt"
        f.write_text("content")
        # Mock output paths so transcript_file doesn't exist
        pipeline.file_discovery = Mock()
        pipeline.file_discovery.get_output_paths.return_value = {
            "audio_file": tmp_path / "source.mp3",
            "transcript_file": tmp_path / "transcript_output.txt",
            "study_file": tmp_path / "source.md",
            "pdf_file": tmp_path / "source.pdf",
        }
        with patch.object(pipeline, 'text_processor') as mock_tp:
            mock_tp.process.return_value = ProcessResult(success=True)
            result = pipeline.process_single_source(f, "images")
        assert result.success is True
        assert result.metadata["target_reached"] == "text"


class TestLoadWhisperModel:
    @patch('src.core.pipeline.whisper')
    def test_load_model_cpu(self, mock_whisper, pipeline):
        mock_torch = Mock()
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch.cuda.is_available.return_value = False
        mock_model = Mock()
        mock_whisper.load_model.return_value = mock_model
        with patch.dict('sys.modules', {'torch': mock_torch}):
            model = pipeline._load_whisper_model()
        assert model is mock_model
        assert pipeline.whisper_model is mock_model

    @patch('src.core.pipeline.whisper')
    def test_load_model_cached(self, mock_whisper, pipeline):
        mock_model = Mock()
        pipeline.whisper_model = mock_model
        model = pipeline._load_whisper_model()
        assert model is mock_model
        mock_whisper.load_model.assert_not_called()

    @patch('src.core.pipeline.whisper')
    def test_load_model_mps(self, mock_whisper, pipeline):
        mock_torch = Mock()
        mock_torch.backends.mps.is_available.return_value = True
        mock_model = Mock()
        mock_whisper.load_model.return_value = mock_model
        with patch.dict('sys.modules', {'torch': mock_torch}):
            model = pipeline._load_whisper_model()
        assert model is mock_model

    @patch('src.core.pipeline.whisper')
    def test_load_model_cuda(self, mock_whisper, pipeline):
        mock_torch = Mock()
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch.cuda.is_available.return_value = True
        mock_model = Mock()
        mock_whisper.load_model.return_value = mock_model
        with patch.dict('sys.modules', {'torch': mock_torch}):
            model = pipeline._load_whisper_model()
        assert model is mock_model

    @patch('src.core.pipeline.whisper')
    def test_load_model_no_mps_attr(self, mock_whisper, pipeline):
        """Test device selection when torch has no mps attribute."""
        mock_torch = Mock()
        del mock_torch.backends.mps  # Remove mps attribute
        mock_torch.cuda.is_available.return_value = False
        mock_model = Mock()
        mock_whisper.load_model.return_value = mock_model
        with patch.dict('sys.modules', {'torch': mock_torch}):
            model = pipeline._load_whisper_model()
        assert model is mock_model

    @patch('src.core.pipeline.whisper')
    def test_load_model_failure(self, mock_whisper, pipeline):
        mock_torch = Mock()
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch.cuda.is_available.return_value = False
        mock_whisper.load_model.side_effect = Exception("Load failed")
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with pytest.raises(VideoTranscriptionError) as exc_info:
                pipeline._load_whisper_model()
        assert "Failed to load Whisper model" in str(exc_info.value)


class TestValidatePrerequisites:
    def test_validate_prerequisites(self, pipeline):
        with patch('src.core.pipeline.whisper'), \
             patch.object(pipeline.study_generator, 'validate_prerequisites', return_value={"llm_available": True}):
            validation = pipeline.validate_prerequisites()
        assert "whisper_model" in validation
        assert "overall_ready" in validation

    def test_validate_prerequisites_whisper_missing(self, pipeline):
        with patch.dict('sys.modules', {'whisper': None}):
            validation = pipeline.validate_prerequisites()
        assert validation["whisper_model"] is False
        assert validation["overall_ready"] is False


class TestGetPipelineInfo:
    def test_get_pipeline_info(self, pipeline):
        info = pipeline.get_pipeline_info()
        assert "config" in info
        assert "components" in info
        assert "processed_stems" in info
        assert info["config"]["whisper_model"] == "tiny"
