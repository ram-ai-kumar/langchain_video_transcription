"""File utility functions for the video transcription pipeline."""

import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

from src.core.config import PipelineConfig


class FileDiscovery:
    """Handles file discovery and grouping for processing."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    def discover_files(self, directory: Path) -> List[Path]:
        """Discover all supported files in directory tree."""
        all_files = []
        
        for root, dirs, files in os.walk(directory):
            # Sort directories for consistent processing order
            dirs.sort(key=lambda d: d.lower())
            
            current_dir = Path(root)
            
            # Collect and sort files in current directory
            dir_files = [
                current_dir / f for f in files 
                if self._is_supported_file(current_dir / f)
            ]
            dir_files.sort(key=lambda f: f.name.lower())
            
            all_files.extend(dir_files)
        
        return all_files
    
    def group_files_by_stem(self, directory: Path) -> Dict[str, List[Path]]:
        """Group files by their stem (filename without extension) within each directory."""
        groups = {}
        
        for root, dirs, files in os.walk(directory):
            # Sort directories for consistent processing order
            dirs.sort(key=lambda d: d.lower())
            
            current_dir = Path(root)
            
            # Group files in current directory
            dir_groups = defaultdict(list)
            
            for file in files:
                file_path = current_dir / file
                if self._is_supported_file(file_path):
                    dir_groups[file_path.stem].append(file_path)
            
            # Add to overall groups with directory context
            for stem, file_list in dir_groups.items():
                # Create unique key combining directory and stem
                group_key = str(current_dir.relative_to(directory)) + "::" + stem
                if str(current_dir.relative_to(directory)) == ".":
                    group_key = stem
                groups[group_key] = sorted(file_list, key=lambda f: f.name.lower())
        
        return groups
    
    def get_media_priority_order(self, files: List[Path]) -> List[Path]:
        """Sort files by media type priority: video > audio > text > images."""
        priority_map = {
            'video': 1,
            'audio': 2,
            'text': 3,
            'image': 4
        }
        
        def get_priority(file_path: Path):
            if self.config.is_video_file(file_path):
                return priority_map['video']
            elif self.config.is_audio_file(file_path):
                return priority_map['audio']
            elif self.config.is_text_file(file_path):
                return priority_map['text']
            elif self.config.is_image_file(file_path):
                return priority_map['image']
            else:
                return 999
        
        return sorted(files, key=get_priority)
    
    def find_primary_source(self, files: List[Path]) -> Tuple[Path, str]:
        """Find the primary source file and its type from a group of files."""
        for file_path in self.get_media_priority_order(files):
            if self.config.is_video_file(file_path):
                return file_path, "video"
            elif self.config.is_audio_file(file_path):
                return file_path, "audio"
            elif self.config.is_text_file(file_path):
                return file_path, "text"
        
        # If no video/audio/text, return first image
        for file_path in files:
            if self.config.is_image_file(file_path):
                return file_path, "images"
        
        return None, None
    
    def separate_image_files(self, files: List[Path]) -> List[Path]:
        """Extract only image files from a list of files."""
        return [f for f in files if self.config.is_image_file(f)]
    
    def get_output_paths(self, source_path: Path, start_type: str) -> Dict[str, Path]:
        """Generate standard output paths for processing."""
        base = source_path.stem
        dir_path = source_path.parent
        
        paths = {
            "audio_file": dir_path / f"{base}.mp3",
            "transcript_file": dir_path / f"{base}.txt",
            "study_file": dir_path / f"{base}_study.md",
            "pdf_file": dir_path / f"{base}.pdf"
        }
        
        # Special handling for image groups
        if start_type == "images":
            paths["transcript_file"] = dir_path / f"{base}_images.txt"
        
        return paths
    
    def _is_supported_file(self, file_path: Path) -> bool:
        """Check if file is supported for processing."""
        return (
            self.config.is_video_file(file_path) or
            self.config.is_audio_file(file_path) or
            self.config.is_text_file(file_path) or
            self.config.is_image_file(file_path)
        )


class FileManager:
    """Manages file operations and validation."""
    
    @staticmethod
    def ensure_directory(path: Path) -> None:
        """Ensure directory exists."""
        path.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def safe_read_text(file_path: Path, encoding: str = "utf-8") -> str:
        """Safely read text file with error handling."""
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            # Try with different encodings
            for alt_encoding in ["latin-1", "cp1252"]:
                try:
                    return file_path.read_text(encoding=alt_encoding)
                except UnicodeDecodeError:
                    continue
            raise
    
    @staticmethod
    def safe_write_text(file_path: Path, content: str, encoding: str = "utf-8") -> None:
        """Safely write text file with error handling."""
        FileManager.ensure_directory(file_path.parent)
        file_path.write_text(content, encoding=encoding)
    
    @staticmethod
    def get_file_size(file_path: Path) -> int:
        """Get file size in bytes."""
        return file_path.stat().st_size if file_path.exists() else 0
    
    @staticmethod
    def is_file_empty(file_path: Path) -> bool:
        """Check if file is empty or contains only whitespace."""
        if not file_path.exists():
            return True
        return len(file_path.read_text(encoding="utf-8").strip()) == 0
