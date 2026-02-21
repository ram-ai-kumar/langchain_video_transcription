"""Text processor for handling existing text files."""

from pathlib import Path
from typing import List

from src.core.config import PipelineConfig
from src.core.exceptions import ProcessingError
from src.processors.base import BaseProcessor, ProcessResult


class TextProcessor(BaseProcessor):
    """Handles text file processing (validation and copying)."""

    def __init__(self, config: PipelineConfig):
        super().__init__(config)

    def can_process(self, file_path: Path) -> bool:
        """Check if processor can handle the file type."""
        return self.config.is_text_file(file_path)

    def _read_text_file(self, file_path: Path) -> str:
        """Read content from text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                raise ProcessingError(
                    f"Failed to read text file {file_path.name}: {e}",
                    processor="TextProcessor"
                )

    def process(self, text_path: Path, output_path: Path) -> ProcessResult:
        """Process text file (validate, read, and optionally copy)."""
        try:
            self.validate_input(text_path)

            # Read text file
            content = self._read_text_file(text_path)
            file_type = "text"
            metadata = {
                "text_length": len(content),
                "original_path": str(text_path),
                "file_type": "text"
            }

            # If output path is different from input, write content
            if text_path != output_path:
                self.ensure_output_dir(output_path)

                with open(output_path, "w", encoding="utf-8") as dst:
                    dst.write(content)

                message = f"Processed {file_type} file: {text_path.name}"
                actual_output_path = output_path
            else:
                message = f"Using existing {file_type} file: {text_path.name}"
                actual_output_path = text_path

            return ProcessResult(
                success=True,
                output_path=actual_output_path,
                message=message,
                metadata=metadata
            )

        except Exception as e:
            raise ProcessingError(
                f"Failed to process text file {text_path.name}: {e}",
                file_path=str(text_path),
                processor="TextProcessor"
            )

    def validate_text_content(self, text_path: Path) -> bool:
        """Validate that text file contains readable content."""
        try:
            content = text_path.read_text(encoding="utf-8")
            return len(content.strip()) > 0
        except Exception:
            return False

    def get_text_stats(self, text_path: Path) -> dict:
        """Get statistics about the text file."""
        try:
            content = text_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            words = content.split()

            return {
                "character_count": len(content),
                "line_count": len(lines),
                "word_count": len(words),
                "has_content": len(content.strip()) > 0
            }
        except Exception as e:
            return {"error": str(e)}
