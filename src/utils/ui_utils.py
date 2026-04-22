"""UI utility functions for user interface and progress display."""

import logging
import sys
import time
import threading
from typing import Callable, Any, Optional



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
