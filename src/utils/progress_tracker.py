"""Simple progress tracker for file processing stages."""

import shutil
from pathlib import Path
from typing import Dict


class ProgressTracker:
    """Tracks and displays progress for files being processed."""

    def __init__(self):
        self.active_files: Dict[str, Dict] = {}
        self.completed_files: Dict[str, Dict] = {}
        self.file_lines: Dict[str, int] = {}
        self.max_line_length: Dict[str, int] = {}

    def start_file(self, file_path: Path, stages: list[str]) -> None:
        """Start tracking a new file through its processing stages."""
        file_key = str(file_path)
        self.active_files[file_key] = {
            'path': file_path,
            'stages': stages,
            'current_stage': 0,
        }
        self.file_lines[file_key] = len(self.file_lines)
        self.max_line_length[file_key] = 0
        self._update_display(file_key)

    def complete_stage(self, file_path: Path) -> None:
        """Mark the current stage as complete and move to the next."""
        file_key = str(file_path)
        if file_key in self.active_files:
            self.active_files[file_key]['current_stage'] += 1
            self._update_display(file_key)

    def complete_file(self, file_path: Path) -> None:
        """Mark a file as completely processed."""
        file_key = str(file_path)
        if file_key in self.active_files:
            self.completed_files[file_key] = self.active_files[file_key].copy()
            del self.active_files[file_key]
            self._update_display(file_key, is_complete=True)

    def _terminal_width(self) -> int:
        return shutil.get_terminal_size((80, 24)).columns

    def _format_path(self, file_path: Path, max_len: int) -> str:
        """Return parent/filename, truncating with middle-ellipsis if needed."""
        parts = file_path.parts
        filename = parts[-1] if parts else str(file_path)
        parent = parts[-2] if len(parts) >= 2 else ""

        candidate = f"{parent}/{filename}" if parent else filename
        if len(candidate) <= max_len:
            return candidate

        # Try filename alone
        if len(filename) <= max_len:
            return filename

        # Middle-ellipsis truncation of filename
        half = max(1, (max_len - 3) // 2)
        return filename[:half] + "..." + filename[-(max_len - half - 3):]

    def _build_line(
        self,
        file_path: Path,
        stages: list[str],
        current_stage: int,
        is_complete: bool,
        terminal_width: int,
    ) -> str:
        if is_complete:
            # Full pipeline chain on completion
            stage_str = " > ".join(stages)
            prefix = "✓ "
        else:
            # Compact indicator during processing: [N/Total: stage_name]
            total = len(stages)
            stage_name = stages[current_stage] if current_stage < total else stages[-1]
            stage_str = f"[{current_stage + 1}/{total}: {stage_name}]"
            prefix = "  "

        # Reserve: prefix (2) + 2 separating spaces + stage_str + 1 margin
        path_budget = terminal_width - len(prefix) - 2 - len(stage_str) - 1
        path_budget = max(10, path_budget)

        display_path = self._format_path(file_path, path_budget)
        return f"{prefix}{display_path}  {stage_str}"

    def _update_display(self, file_key: str, is_complete: bool = False) -> None:
        """Update the display line for a file, capped to terminal width."""
        if file_key in self.active_files:
            file_info = self.active_files[file_key]
        elif file_key in self.completed_files:
            file_info = self.completed_files[file_key]
        else:
            return

        tw = self._terminal_width()
        line = self._build_line(
            file_info['path'],
            file_info['stages'],
            file_info['current_stage'],
            is_complete,
            tw,
        )

        # Pad to erase any leftover characters from a previous longer line
        prev_max = self.max_line_length.get(file_key, 0)
        self.max_line_length[file_key] = max(prev_max, len(line))
        padding = " " * max(0, prev_max - len(line))

        if is_complete:
            print(f"\r{line}{padding}")
        else:
            print(f"\r{line}{padding}", end="", flush=True)

    def clear_all(self) -> None:
        """Clear all active file tracking."""
        self.active_files.clear()
        self.completed_files.clear()
        self.file_lines.clear()
        self.max_line_length.clear()
