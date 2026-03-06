"""Integration tests for pipeline workflows."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.core.pipeline import VideoTranscriptionPipeline
from src.core.config import PipelineConfig
from src.processors.base import ProcessResult


class TestPipelineIntegration:
    """Integration tests for the main pipeline."""
    
    @patch('src.core.pipeline.whisper')
    @patch('src.core.pipeline.FileDiscovery')
    @patch('src.core.pipeline.StudyMaterialGenerator')
    def test_process_directory_empty(self, mock_whisper, mock_file_discovery, mock_study_gen, temp_dir):
        """Test processing empty directory."""
        mock_file_discovery.return_value.group_files_by_stem.return_value = {}
        
        pipeline = VideoTranscriptionPipeline(Mock())
        result = pipeline.process_directory(temp_dir)
        
        assert result.success is True
        assert result.message == "No media files found to process"
        assert "groups_found" in result.metadata
        assert result.metadata["groups_found"] == 0
    
    @patch('src.core.pipeline.whisper')
    @patch('src.core.pipeline.FileDiscovery')
    @patch('src.core.pipeline.StudyMaterialGenerator')
    def test_process_directory_success(self, mock_whisper, mock_file_discovery, mock_study_gen, temp_dir):
        """Test successful directory processing."""
        # Setup mocks
        mock_file_discovery.return_value.group_files_by_stem.return_value = {
            "lecture1": {
                "video": temp_dir / "lecture1.mp4",
                "audio": temp_dir / "lecture1.wav",
                "transcript": temp_dir / "lecture1.txt",
                "images": [temp_dir / "slide1.png", temp_dir / "slide2.png"]
            }
        }
        
        mock_whisper.load_model.return_value = Mock()
        mock_whisper.load_model.return_value.transcribe.return_value = {"text": "Transcribed content"}
        mock_study_gen.return_value.generate_study_material.return_value = "Generated study material"
        
        pipeline = VideoTranscriptionPipeline(Mock())
        result = pipeline.process_directory(temp_dir)
        
        assert result.success is True
        assert result.metadata["groups_processed"] == 1
        assert result.metadata["errors"] == 0
    
    @patch('src.core.pipeline.whisper')
    @patch('src.core.pipeline.FileDiscovery')
    @patch('src.core.pipeline.StudyMaterialGenerator')
    def test_process_directory_with_errors(self, mock_whisper, mock_file_discovery, mock_study_gen, temp_dir):
        """Test directory processing with some errors."""
        # Setup mocks with mixed success/failure
        mock_file_discovery.return_value.group_files_by_stem.return_value = {
            "lecture1": {
                "video": temp_dir / "lecture1.mp4",
                "audio": temp_dir / "lecture1.wav",
                "transcript": temp_dir / "lecture1.txt",
                "images": [temp_dir / "slide1.png"]
            },
            "lecture2": {
                "video": temp_dir / "lecture2.mp4",
                "audio": temp_dir / "lecture2.wav",
                "transcript": temp_dir / "lecture2.txt",
                "images": []
            }
        }
        
        # Mock successful processing for lecture1
        mock_whisper.load_model.return_value = Mock()
        mock_whisper.load_model.return_value.transcribe.return_value = {"text": "Transcribed content"}
        mock_study_gen.return_value.generate_study_material.return_value = "Generated study material"
        
        # Mock failed processing for lecture2
        mock_study_gen.return_value.generate_study_material.return_value = ProcessResult(
            success=False,
            message="Failed to generate study material"
        )
        
        pipeline = VideoTranscriptionPipeline(Mock())
        result = pipeline.process_directory(temp_dir)
        
        assert result.success is True  # Overall success despite partial failures
        assert result.metadata["groups_processed"] == 1
        assert result.metadata["errors"] == 1
    
    def test_validate_prerequisites_success(self, mock_whisper, mock_study_gen):
        """Test successful prerequisite validation."""
        mock_whisper.load_model.return_value = Mock()
        mock_study_gen.return_value.validate_prerequisites.return_value = {
            "whisper_model": True,
            "llm_available": True,
            "prompt_file": True,
            "overall_ready": True
        }
        
        pipeline = VideoTranscriptionPipeline(Mock())
        validation = pipeline.validate_prerequisites()
        
        assert validation["overall_ready"] is True
        assert all(validation.values())
    
    def test_validate_prerequisites_failure(self, mock_whisper, mock_study_gen):
        """Test prerequisite validation with failures."""
        mock_whisper.load_model.side_effect = Exception("Whisper not available")
        mock_study_gen.return_value.validate_prerequisites.return_value = {
            "whisper_model": False,
            "llm_available": True,
            "prompt_file": True,
            "overall_ready": False
        }
        
        pipeline = VideoTranscriptionPipeline(Mock())
        validation = pipeline.validate_prerequisites()
        
        assert validation["overall_ready"] is False
        assert validation["whisper_model"] is False
