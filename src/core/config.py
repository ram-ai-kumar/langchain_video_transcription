"""Configuration management for the video transcription pipeline."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class PipelineConfig:
    """Configuration object for pipeline settings."""
    
    # Model settings
    llm_model: str = "gemma3"
    whisper_model: str = "medium"
    
    # Output settings
    generate_pdf: bool = True
    output_dir: Optional[Path] = None
    
    # File extensions
    video_extensions: List[str] = field(default_factory=lambda: [".mp4", ".mkv", ".avi", ".mov"])
    audio_extensions: List[str] = field(default_factory=lambda: [".mp3", ".wav", ".m4a", ".aac"])
    text_extensions: List[str] = field(default_factory=lambda: [".txt"])
    image_extensions: List[str] = field(default_factory=lambda: [
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp"
    ])
    
    # Processing settings
    ffmpeg_audio_quality: int = 2  # libmp3lame quality setting
    ocr_language: str = "eng"
    transcription_language: str = "en"
    
    # UI settings
    show_spinner: bool = True
    verbose: bool = False
    
    # Paths
    prompt_file: Optional[Path] = None
    header_file: Optional[Path] = None
    
    def __post_init__(self):
        """Initialize derived paths and validate configuration."""
        if self.prompt_file is None:
            self.prompt_file = Path(__file__).parent.parent.parent / "config" / "study_prompt.txt"
        
        if self.header_file is None:
            self.header_file = Path(__file__).parent.parent.parent / "config" / "header.tex"
        
        # Validate that required files exist
        if not self.prompt_file.exists():
            raise ConfigurationError(f"Prompt file not found: {self.prompt_file}")
        
        if not self.header_file.exists():
            raise ConfigurationError(f"Header file not found: {self.header_file}")
    
    def get_all_extensions(self) -> List[str]:
        """Get all supported file extensions."""
        return (
            self.video_extensions + 
            self.audio_extensions + 
            self.text_extensions + 
            self.image_extensions
        )
    
    def is_video_file(self, file_path: Path) -> bool:
        """Check if file is a video file."""
        return file_path.suffix.lower() in self.video_extensions
    
    def is_audio_file(self, file_path: Path) -> bool:
        """Check if file is an audio file."""
        return file_path.suffix.lower() in self.audio_extensions
    
    def is_text_file(self, file_path: Path) -> bool:
        """Check if file is a text file."""
        return file_path.suffix.lower() in self.text_extensions
    
    def is_image_file(self, file_path: Path) -> bool:
        """Check if file is an image file."""
        return file_path.suffix.lower() in self.image_extensions
