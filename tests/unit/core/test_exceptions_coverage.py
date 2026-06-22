"""Comprehensive tests for exceptions to achieve 100% coverage."""

import pytest
from pathlib import Path

from src.core.exceptions import (
    VideoTranscriptionError,
    ProcessingError,
    ConfigurationError,
    ModelLoadError,
    PDFGenerationError,
    OCRProcessingError,
    TranscriptionError,
    LLMProcessingError,
)


class TestVideoTranscriptionError:
    def test_basic_message(self):
        error = VideoTranscriptionError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_is_exception(self):
        error = VideoTranscriptionError("test")
        assert isinstance(error, Exception)


class TestProcessingError:
    def test_with_all_params(self):
        error = ProcessingError("Processing failed", file_path="/tmp/test.txt", processor="AudioProcessor")
        assert str(error) == "Processing failed"
        assert error.file_path == "/tmp/test.txt"
        assert error.processor == "AudioProcessor"

    def test_with_defaults(self):
        error = ProcessingError("Processing failed")
        assert str(error) == "Processing failed"
        assert error.file_path is None
        assert error.processor is None

    def test_is_video_transcription_error(self):
        error = ProcessingError("test")
        assert isinstance(error, VideoTranscriptionError)


class TestConfigurationError:
    def test_basic(self):
        error = ConfigurationError("Bad config")
        assert str(error) == "Bad config"
        assert isinstance(error, VideoTranscriptionError)


class TestModelLoadError:
    def test_basic(self):
        error = ModelLoadError("Model failed")
        assert str(error) == "Model failed"
        assert isinstance(error, VideoTranscriptionError)


class TestPDFGenerationError:
    def test_with_processor(self):
        error = PDFGenerationError("PDF failed", processor="PDFGenerator")
        assert str(error) == "PDF failed"
        assert error.processor == "PDFGenerator"

    def test_without_processor(self):
        error = PDFGenerationError("PDF failed")
        assert str(error) == "PDF failed"
        assert error.processor is None

    def test_is_video_transcription_error(self):
        error = PDFGenerationError("test")
        assert isinstance(error, VideoTranscriptionError)


class TestOCRProcessingError:
    def test_basic(self):
        error = OCRProcessingError("OCR failed")
        assert str(error) == "OCR failed"
        assert isinstance(error, ProcessingError)

    def test_with_params(self):
        error = OCRProcessingError("OCR failed", file_path="/tmp/img.png", processor="ImageProcessor")
        assert error.file_path == "/tmp/img.png"
        assert error.processor == "ImageProcessor"


class TestTranscriptionError:
    def test_basic(self):
        error = TranscriptionError("Transcription failed")
        assert str(error) == "Transcription failed"
        assert isinstance(error, ProcessingError)

    def test_with_params(self):
        error = TranscriptionError("Failed", file_path="/tmp/test.wav", processor="AudioProcessor")
        assert error.file_path == "/tmp/test.wav"
        assert error.processor == "AudioProcessor"


class TestLLMProcessingError:
    def test_basic(self):
        error = LLMProcessingError("LLM failed")
        assert str(error) == "LLM failed"
        assert isinstance(error, ProcessingError)

    def test_with_params(self):
        error = LLMProcessingError("Failed", file_path="/tmp/test.txt", processor="LLMProcessor")
        assert error.file_path == "/tmp/test.txt"
        assert error.processor == "LLMProcessor"


class TestExceptionInheritance:
    def test_all_inherit_from_base(self):
        exceptions = [
            ProcessingError("test"),
            ConfigurationError("test"),
            ModelLoadError("test"),
            PDFGenerationError("test"),
            OCRProcessingError("test"),
            TranscriptionError("test"),
            LLMProcessingError("test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, VideoTranscriptionError)

    def test_processing_error_subclasses(self):
        assert issubclass(OCRProcessingError, ProcessingError)
        assert issubclass(TranscriptionError, ProcessingError)
        assert issubclass(LLMProcessingError, ProcessingError)
