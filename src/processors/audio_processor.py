"""Audio processor for transcribing audio files using Whisper."""

import logging
import subprocess
from pathlib import Path
from typing import Optional

import whisper

from src.core.config import PipelineConfig
from src.core.exceptions import TranscriptionError, ModelLoadError
from src.processors.base import BaseProcessor, ProcessResult


class AudioProcessor(BaseProcessor):
    """Handles audio transcription using Whisper."""

    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        self.model: Optional[whisper.Whisper] = None
        self.logger = logging.getLogger(__name__)

    def can_process(self, file_path: Path) -> bool:
        """Check if processor can handle the file type."""
        return self.config.is_audio_file(file_path)

    def _load_model(self) -> whisper.Whisper:
        """Load Whisper model if not already loaded."""
        if self.model is None:
            try:
                from src.utils.whisper_utils import load_whisper_model_silent
                self.model = load_whisper_model_silent(
                    self.config.whisper_model,
                    device="auto"
                )
            except Exception as e:
                raise ModelLoadError(f"Failed to load Whisper model '{self.config.whisper_model}': {e}")
        return self.model

    def process(self, audio_path: Path, transcript_path: Path) -> ProcessResult:
        """Transcribe audio to text."""
        try:
            self.validate_input(audio_path)
            self.ensure_output_dir(transcript_path)

            # Load model
            model = self._load_model()

            # Transcribe audio with progress callback
            from src.utils.whisper_utils import transcribe_silent

            def progress_callback(progress_info):
                # This will be called with progress updates
                # The pipeline will handle displaying this
                pass

            result = transcribe_silent(
                model,
                str(audio_path),
                language=self.config.transcription_language,
                progress_callback=progress_callback
            )

            # Write transcript
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(result["text"])

            return ProcessResult(
                success=True,
                output_path=transcript_path,
                message=f"Successfully transcribed {audio_path.name}",
                metadata={
                    "duration": result.get("duration"),
                    "language": result.get("language"),
                    "text_length": len(result["text"])
                }
            )

        except Exception as e:
            raise TranscriptionError(
                f"Failed to transcribe {audio_path.name}: {e}",
                file_path=str(audio_path),
                processor="AudioProcessor"
            )

    def extract_audio_from_video(self, video_path: Path, audio_path: Path) -> ProcessResult:
        """Extract audio from video file using ffmpeg."""
        try:
            self.validate_input(video_path)
            self.ensure_output_dir(audio_path)

            # Use ffmpeg to extract audio (simple version without progress parsing)
            import subprocess

            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-vn",  # No video
                "-c:a", "libmp3lame",
                "-q:a", str(self.config.ffmpeg_audio_quality),
                "-y",  # Overwrite output without asking
                str(audio_path)
            ]

            # Run ffmpeg silently
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            return ProcessResult(
                success=True,
                output_path=audio_path,
                message=f"Successfully extracted audio from {video_path.name}",
                metadata={"source_video": str(video_path)}
            )

        except subprocess.CalledProcessError as e:
            raise TranscriptionError(
                f"Failed to extract audio from {video_path.name}: {str(e)}",
                file_path=str(video_path),
                processor="AudioProcessor"
            )
        except Exception as e:
            raise TranscriptionError(
                f"Unexpected error extracting audio from {video_path.name}: {e}",
                file_path=str(video_path),
                processor="AudioProcessor"
            )
