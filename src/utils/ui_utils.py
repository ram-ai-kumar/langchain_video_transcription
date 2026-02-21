"""UI utility functions for user interface and progress display."""

import sys
import time
import threading
from typing import Callable, Any, Optional

# Processing steps mapping for different file types
PROCESSING_STEPS = {
    "video": ["audio", "transcript", "study_material", "pdf"],
    "audio": ["transcript", "study_material", "pdf"],
    "text": ["transcript", "study_material", "pdf"],
    "image": ["transcript", "study_material", "pdf"]
}


class Spinner:
    """A lightweight CLI spinner for long-running operations."""

    def __init__(self, prefix: str = "", spinner_chars: Optional[list] = None):
        self.prefix = prefix
        self.spinner_chars = spinner_chars or ["|", "/", "-", "\\"]
        self._done = False
        self._result = None
        self._exception = None
        self._thread = None

    def __call__(self, run_func: Callable, *args, **kwargs) -> Any:
        """Run function with spinner display."""
        self._done = False
        self._result = None
        self._exception = None

        # Start worker thread
        self._thread = threading.Thread(target=self._run_target, args=(run_func, args, kwargs))
        self._thread.start()

        # Show spinner
        self._show_spinner()

        # Wait for completion
        self._thread.join()

        # Clean up display
        sys.stdout.write(f"\r{self.prefix}\n")
        sys.stdout.flush()

        # Handle result or exception
        if self._exception:
            raise self._exception

        return self._result

    def _run_target(self, run_func: Callable, args: tuple, kwargs: dict) -> None:
        """Target function for worker thread."""
        try:
            self._result = run_func(*args, **kwargs)
        except Exception as e:
            self._exception = e
        finally:
            self._done = True

    def _show_spinner(self) -> None:
        """Display spinner while operation is running."""
        i = 0
        while not self._done and self._thread.is_alive():
            char = self.spinner_chars[i % len(self.spinner_chars)]
            sys.stdout.write(f"\r{self.prefix} {char}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1


class ProgressReporter:
    """Reports progress with fixed-width progress bar."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.current_file = ""
        self.current_step = 0
        self.total_steps = 0
        self.steps = []
        self.processing = False
        self.bar_width = 28  # Fixed width inside brackets

    def start_processing(self, file_path: str, steps: list) -> None:
        """Start processing a file with given steps."""
        self.current_file = file_path
        self.steps = steps
        self.total_steps = len(steps)
        self.current_step = 0
        self.processing = True

        # Show initial progress line
        self._show_progress()

    def next_step(self) -> None:
        """Move to next step."""
        if self.processing and self.current_step < self.total_steps:
            self.current_step += 1
            self._show_progress()

    def complete_processing(self, success: bool = True) -> None:
        """Complete processing."""
        if self.processing:
            # Show final progress
            self._show_progress()

            # Move to next line for next file
            print()

            # If error, show error message
            if not success:
                print(ColorFormatter.error(f"[{self._get_progress_bar()}] {self.current_file} Error: Processing failed"))

            self.processing = False

    def _show_progress(self) -> None:
        """Show current progress on same line."""
        if not self.processing:
            return

        # Clear the entire line first
        sys.stdout.write("\r" + " " * 120 + "\r")

        # Generate progress bar
        progress_bar = self._get_progress_bar()

        # Show on same line
        progress_line = f"[{progress_bar}] {self.current_file}"
        sys.stdout.write(f"\r{progress_line}")
        sys.stdout.flush()

    def _get_progress_bar(self) -> str:
        """Generate fixed-width progress bar."""
        if self.total_steps == 0:
            return "-" * self.bar_width

        percentage = (self.current_step / self.total_steps)
        completed_chars = int(self.bar_width * percentage)
        remaining_chars = self.bar_width - completed_chars

        return "#" * completed_chars + "-" * remaining_chars

    def get_progress_string(self) -> str:
        """Get current progress as string."""
        if self.total_steps > 0:
            return f"Step {self.current_step}/{self.total_steps}"
        else:
            return "Processing..."

    def format_pipeline_steps(self, steps: list) -> str:
        """Format pipeline steps for display."""
        return " > ".join(steps)


class ColorFormatter:
    """Provides color formatting for terminal output."""

    COLORS = {
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'reset': '\033[0m',
        'bold': '\033[1m',
        'underline': '\033[4m'
    }

    @classmethod
    def format(cls, text: str, color: str) -> str:
        """Format text with specified color."""
        if color in cls.COLORS:
            return f"{cls.COLORS[color]}{text}{cls.COLORS['reset']}"
        return text

    @classmethod
    def error(cls, text: str) -> str:
        """Format error message."""
        return cls.format(text, 'red')

    @classmethod
    def success(cls, text: str) -> str:
        """Format success message."""
        return cls.format(text, 'green')

    @classmethod
    def warning(cls, text: str) -> str:
        """Format warning message."""
        return cls.format(text, 'yellow')

    @classmethod
    def info(cls, text: str) -> str:
        """Format info message."""
        return cls.format(text, 'blue')

    @classmethod
    def bold(cls, text: str) -> str:
        """Format bold text."""
        return cls.format(text, 'bold')


class StatusReporter:
    """Reports status messages with different levels."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def info(self, message: str, prefix: str = "[INFO]") -> None:
        """Report info message."""
        if self.verbose:
            print(f"    {prefix} {message}")

    def warning(self, message: str, prefix: str = "[WARN]") -> None:
        """Report warning message."""
        if self.verbose:
            print(ColorFormatter.warning(f"    {prefix} {message}"))

    def error(self, message: str, prefix: str = "[ERROR]") -> None:
        """Report error message."""
        print(ColorFormatter.error(f"    {prefix} {message}"))

    def success(self, message: str, prefix: str = "[SUCCESS]") -> None:
        """Report success message."""
        if self.verbose:
            print(ColorFormatter.success(f"    {prefix} {message}"))

    def debug(self, message: str, prefix: str = "[DEBUG]") -> None:
        """Report debug message."""
        if self.verbose:
            print(f"    {prefix} {message}")


# Convenience function for backward compatibility
def spinner(prefix: str, run_func: Callable, *args, **kwargs) -> Any:
    """Convenience function for spinner usage."""
    return Spinner(prefix)(run_func, *args, **kwargs)
