"""UI utility functions for user interface and progress display."""

import logging
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


from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from src.utils.progress_subprocess import ProgressType

class ProgressReporter:
    """Reports progress cleanly for concurrent execution using Rich."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            expand=True
        )
        self.tasks = {}
        self.task_progress = {}  # Store detailed progress info
        self.started = False

    def start_processing(self, file_path: str, steps: list, prefix: str = "") -> None:
        """Start processing a file with given steps."""
        with self._lock:
            if not self.started:
                # Ensure Rich doesn't interfere with subprocess outputs
                import os
                os.environ['RICH_FORCE_TERMINAL'] = 'true'
                os.environ['RICH_USE_COLOR'] = 'true'

                self.progress.start()
                self.started = True

            task_id = self.progress.add_task(
                description=f"{prefix}{file_path}",
                total=len(steps)
            )
            self.tasks[file_path] = task_id

    def next_step(self, file_path: str, skipped: bool = False) -> None:
        """Move to next step for a specific file."""
        with self._lock:
            if file_path in self.tasks:
                self.progress.update(self.tasks[file_path], advance=1)

    def update_task_progress(self, file_path: str, progress_percentage: float, description: str = "") -> None:
        """Update task progress with simple percentage and description."""
        with self._lock:
            if file_path in self.tasks:
                task_id = self.tasks[file_path]

                # Get current step progress
                current_step = self.progress.tasks[task_id].completed or 0
                total_steps = self.progress.tasks[task_id].total

                # Calculate progress within current step
                step_progress = progress_percentage / 100.0

                # Overall progress = (completed steps) + (current step progress)
                overall_progress = current_step + step_progress

                # Update Rich progress bar
                full_description = f"{file_path}"
                if description:
                    full_description += f" ({description})"

                self.progress.update(task_id, description=full_description, completed=overall_progress)

    def update_task_progress_legacy(self, file_path: str, progress_info) -> None:
        """Legacy method for backward compatibility with existing progress info objects."""
        with self._lock:
            if file_path in self.tasks:
                task_id = self.tasks[file_path]
                self.task_progress[file_path] = progress_info

                # Get current step progress
                current_step = self.progress.tasks[task_id].completed or 0

                # Handle different progress types
                if hasattr(progress_info, 'percentage'):
                    # Real-time progress object
                    step_progress = progress_info.percentage / 100.0
                    overall_progress = current_step + step_progress
                    description = f"{file_path} ({progress_info.description})"
                    self.progress.update(task_id, description=description, completed=overall_progress)
                elif hasattr(progress_info, 'type'):
                    # Legacy progress info object
                    if progress_info.type.value == 'percentage':
                        step_progress = progress_info.value / 100.0
                        overall_progress = current_step + step_progress
                        description = f"{file_path} ({progress_info.description})"
                        self.progress.update(task_id, description=description, completed=overall_progress)
                    elif progress_info.type.value == 'frame_count':
                        # For frame-based progress, just update description
                        description = f"{file_path} ({progress_info.description})"
                        self.progress.update(task_id, description=description)
                else:
                    # Fallback - just update description
                    description = f"{file_path} (Processing...)"
                    self.progress.update(task_id, description=description)

    def complete_processing(self, success: bool = True, file_path: str = "", prefix: str = "", skipped: bool = False) -> None:
        """Complete processing for a specific file."""
        with self._lock:
            if file_path in self.tasks:
                task_id = self.tasks[file_path]
                if not success:
                    self.progress.update(task_id, description=f"{prefix}[red]✗ {file_path}[/red]", completed=self.progress.tasks[task_id].total)
                elif skipped:
                    self.progress.update(task_id, description=f"{prefix}[yellow]⏭  {file_path}[/yellow]", completed=self.progress.tasks[task_id].total)
                else:
                    self.progress.update(task_id, description=f"{prefix}[green]✓ {file_path}[/green]", completed=self.progress.tasks[task_id].total)

                # Clean up progress info
                self.task_progress.pop(file_path, None)

    def stop(self):
        """Stop the progress display."""
        with self._lock:
            if self.started:
                self.progress.stop()
                self.started = False

    def get_progress_string(self) -> str:
        """Get current progress as string."""
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
        self.logger = logging.getLogger(__name__)

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
