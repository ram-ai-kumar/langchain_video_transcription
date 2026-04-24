"""Error logging utility for persistent error tracking."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class ErrorLogger:
    """Logger for persisting errors to a file for later analysis."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize error logger.
        
        Args:
            cache_dir: Custom cache directory. Defaults to ~/.cache/video_transcription
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "video_transcription"
        
        self.cache_dir = cache_dir
        self.error_log_path = cache_dir / "errors.txt"
        self.summary_path = cache_dir / "errors_summary.txt"
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def log_error(self, error_type: str, message: str, context: Optional[str] = None) -> None:
        """Log an error to the error file.
        
        Args:
            error_type: Category of error (e.g., "video_processing", "image_processing")
            message: Error message
            context: Additional context about when/where the error occurred
        """
        timestamp = datetime.now().isoformat()
        
        log_entry = f"[{timestamp}] [{error_type}]"
        if context:
            log_entry += f" Context: {context}"
        log_entry += f" Message: {message}\n"
        
        with open(self.error_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    
    def clear_errors(self) -> None:
        """Clear the error log file."""
        if self.error_log_path.exists():
            self.error_log_path.unlink()
    
    def get_error_count(self) -> int:
        """Get the number of errors logged.
        
        Returns:
            Number of error lines in the log file
        """
        if not self.error_log_path.exists():
            return 0
        
        with open(self.error_log_path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    
    def get_errors(self) -> str:
        """Read and return all errors from the log file.
        
        Returns:
            Contents of the error log file
        """
        if not self.error_log_path.exists():
            return ""
        
        with open(self.error_log_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def save_summary(self, summary: str) -> None:
        """Save the AI-generated error summary.
        
        Args:
            summary: Generated summary text
        """
        with open(self.summary_path, "w", encoding="utf-8") as f:
            f.write(summary)
    
    def get_summary(self) -> Optional[str]:
        """Read and return the saved error summary.
        
        Returns:
            Contents of the summary file, or None if it doesn't exist
        """
        if not self.summary_path.exists():
            return None
        
        with open(self.summary_path, "r", encoding="utf-8") as f:
            return f.read()
