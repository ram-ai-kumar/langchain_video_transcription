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
    
    def process(self, text_path: Path, output_path: Path) -> ProcessResult:
        """Process text file (validate and optionally copy to output location)."""
        try:
            self.validate_input(text_path)
            
            # If output path is different from input, copy the file
            if text_path != output_path:
                self.ensure_output_dir(output_path)
                
                with open(text_path, "r", encoding="utf-8") as src:
                    content = src.read()
                
                with open(output_path, "w", encoding="utf-8") as dst:
                    dst.write(content)
                
                message = f"Processed text file: {text_path.name}"
                actual_output_path = output_path
            else:
                message = f"Using existing text file: {text_path.name}"
                actual_output_path = text_path
            
            return ProcessResult(
                success=True,
                output_path=actual_output_path,
                message=message,
                metadata={
                    "text_length": len(text_path.read_text(encoding="utf-8")),
                    "original_path": str(text_path)
                }
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
