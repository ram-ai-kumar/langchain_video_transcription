"""Abstract base processor for all media processors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from src.core.config import PipelineConfig


@dataclass
class ProcessResult:
    """Result of a processing operation."""
    success: bool
    output_path: Optional[Path] = None
    message: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseProcessor(ABC):
    """Abstract base class for all media processors."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    @abstractmethod
    def can_process(self, file_path: Path) -> bool:
        """Check if processor can handle the file type."""
        pass
    
    @abstractmethod
    def process(self, *args, **kwargs) -> ProcessResult:
        """Process the file(s) and return result."""
        pass
    
    def get_output_path(self, input_path: Path, suffix: str = "") -> Path:
        """Generate output path for processed file."""
        if self.config.output_dir:
            output_dir = self.config.output_dir
        else:
            output_dir = input_path.parent
        
        base_name = input_path.stem + suffix
        return output_dir / f"{base_name}.txt"
    
    def validate_input(self, file_path: Path) -> None:
        """Validate input file exists and is accessible."""
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
    
    def ensure_output_dir(self, output_path: Path) -> None:
        """Ensure output directory exists."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
