"""UI utility functions for user interface and progress display."""

import sys
import time
import threading
from typing import Callable, Any, Optional


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
    """Reports progress for multi-step operations."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.current_step = 0
        self.total_steps = 0
        self.steps = []
    
    def set_steps(self, steps: list) -> None:
        """Set the list of processing steps."""
        self.steps = steps
        self.total_steps = len(steps)
        self.current_step = 0
    
    def start_step(self, step_name: str) -> None:
        """Start a new processing step."""
        self.current_step += 1
        if self.verbose:
            progress = f"[{self.current_step}/{self.total_steps}]" if self.total_steps > 0 else ""
            print(f"    {progress} Starting: {step_name}")
    
    def complete_step(self, step_name: str, success: bool = True, message: str = "") -> None:
        """Complete a processing step."""
        if self.verbose:
            status = "✓" if success else "✗"
            msg = f" - {message}" if message else ""
            print(f"    {status} {step_name}{msg}")
    
    def report_progress(self, message: str) -> None:
        """Report general progress message."""
        if self.verbose:
            print(f"    {message}")
    
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
