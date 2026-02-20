"""Media utility functions for media type detection and processing."""

from pathlib import Path
from typing import List, Tuple, Optional

from src.core.config import PipelineConfig


class MediaTypeDetector:
    """Detects and categorizes media file types."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    def get_media_type(self, file_path: Path) -> str:
        """Get the media type of a file."""
        if self.config.is_video_file(file_path):
            return "video"
        elif self.config.is_audio_file(file_path):
            return "audio"
        elif self.config.is_text_file(file_path):
            return "text"
        elif self.config.is_image_file(file_path):
            return "image"
        else:
            return "unknown"
    
    def categorize_files(self, files: List[Path]) -> dict:
        """Categorize files by media type."""
        categories = {
            "video": [],
            "audio": [],
            "text": [],
            "image": [],
            "unknown": []
        }
        
        for file_path in files:
            media_type = self.get_media_type(file_path)
            categories[media_type].append(file_path)
        
        return categories
    
    def get_primary_media_type(self, files: List[Path]) -> str:
        """Get the primary media type from a list of files."""
        categories = self.categorize_files(files)
        
        # Priority order: video > audio > text > image
        if categories["video"]:
            return "video"
        elif categories["audio"]:
            return "audio"
        elif categories["text"]:
            return "text"
        elif categories["image"]:
            return "image"
        else:
            return "unknown"
    
    def filter_by_type(self, files: List[Path], media_type: str) -> List[Path]:
        """Filter files by media type."""
        return [f for f in files if self.get_media_type(f) == media_type]


class MediaProcessorFactory:
    """Factory for creating appropriate media processors."""
    
    def __init__(self, config):
        self.config = config
        self._processors = {}
    
    def get_processor(self, media_type: str):
        """Get appropriate processor for media type."""
        if media_type not in self._processors:
            self._processors[media_type] = self._create_processor(media_type)
        return self._processors[media_type]
    
    def _create_processor(self, media_type: str):
        """Create processor for specific media type."""
        if media_type == "audio":
            from src.processors.audio_processor import AudioProcessor
            return AudioProcessor(self.config)
        elif media_type == "image":
            from src.processors.image_processor import ImageProcessor
            return ImageProcessor(self.config)
        elif media_type == "text":
            from src.processors.text_processor import TextProcessor
            return TextProcessor(self.config)
        elif media_type == "llm":
            from src.processors.llm_processor import LLMProcessor
            return LLMProcessor(self.config)
        else:
            raise ValueError(f"Unknown media type: {media_type}")


class MediaFileValidator:
    """Validates media files for processing."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    def validate_file(self, file_path: Path) -> Tuple[bool, str]:
        """Validate a single media file."""
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"
        
        if not file_path.is_file():
            return False, f"Path is not a file: {file_path}"
        
        # Check file size
        if file_path.stat().st_size == 0:
            return False, f"File is empty: {file_path}"
        
        # Check file extension
        media_type = MediaTypeDetector(self.config).get_media_type(file_path)
        if media_type == "unknown":
            return False, f"Unsupported file type: {file_path.suffix}"
        
        return True, ""
    
    def validate_files(self, files: List[Path]) -> Tuple[List[Path], List[str]]:
        """Validate multiple files and return valid files and error messages."""
        valid_files = []
        errors = []
        
        for file_path in files:
            is_valid, error = self.validate_file(file_path)
            if is_valid:
                valid_files.append(file_path)
            else:
                errors.append(error)
        
        return valid_files, errors
    
    def get_file_info(self, file_path: Path) -> dict:
        """Get detailed information about a media file."""
        detector = MediaTypeDetector(self.config)
        
        info = {
            "path": str(file_path),
            "name": file_path.name,
            "stem": file_path.stem,
            "extension": file_path.suffix,
            "size": file_path.stat().st_size,
            "media_type": detector.get_media_type(file_path),
            "exists": file_path.exists(),
            "is_file": file_path.is_file()
        }
        
        # Add size in human readable format
        size_bytes = info["size"]
        if size_bytes < 1024:
            info["size_human"] = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            info["size_human"] = f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            info["size_human"] = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            info["size_human"] = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        
        return info


class ProcessingPathGenerator:
    """Generates processing paths for media files."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    def get_processing_chain(self, start_type: str, source_path: Path) -> List[str]:
        """Get the processing chain for a given start type."""
        chains = {
            "video": ["video", "audio", "transcript", "study material", "PDF"],
            "audio": ["audio", "transcript", "study material", "PDF"],
            "text": ["transcript", "study material", "PDF"],
            "images": ["images", "transcript", "study material", "PDF"]
        }
        
        base_chain = chains.get(start_type, [])
        
        # Remove PDF if not generating PDFs
        if not self.config.generate_pdf:
            base_chain = [step for step in base_chain if step != "PDF"]
        
        return base_chain
    
    def get_output_filename(self, source_path: Path, output_type: str, suffix: str = "") -> Path:
        """Generate output filename for different output types."""
        base = source_path.stem
        dir_path = source_path.parent
        
        if self.config.output_dir:
            dir_path = self.config.output_dir
        
        filename_mapping = {
            "audio": f"{base}.mp3",
            "transcript": f"{base}{suffix}.txt",
            "study": f"{base}_study.md",
            "pdf": f"{base}.pdf"
        }
        
        filename = filename_mapping.get(output_type, f"{base}{suffix}.txt")
        return dir_path / filename
