"""Custom exceptions for the video transcription pipeline."""


class VideoTranscriptionError(Exception):
    """Base exception for video transcription pipeline."""
    pass


class ProcessingError(VideoTranscriptionError):
    """Raised when file processing fails."""

    def __init__(self, message: str, file_path: str = None, processor: str = None):
        super().__init__(message)
        self.file_path = file_path
        self.processor = processor


class ConfigurationError(VideoTranscriptionError):
    """Raised when configuration is invalid."""
    pass


class ModelLoadError(VideoTranscriptionError):
    """Raised when AI model loading fails."""
    pass


class PDFGenerationError(VideoTranscriptionError):
    """Raised when PDF generation fails."""

    def __init__(self, message: str, processor: str = None):
        super().__init__(message)
        self.processor = processor


class OCRProcessingError(ProcessingError):
    """Raised when OCR processing fails."""
    pass


class TranscriptionError(ProcessingError):
    """Raised when audio transcription fails."""
    pass


class LLMProcessingError(ProcessingError):
    """Raised when LLM processing fails."""
    pass
