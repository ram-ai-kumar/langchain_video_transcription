
import pytest
import threading
import time
from unittest.mock import MagicMock, patch
from src.utils.resource_manager import ResourceManager
from src.core.pipeline import VideoTranscriptionPipeline
from src.core.config import PipelineConfig

def test_resource_manager_stats():
    """Test that ResourceManager returns plausible system stats."""
    rm = ResourceManager()
    stats = rm.get_system_stats()
    
    assert "ram_total_gb" in stats
    assert "ram_available_gb" in stats
    assert stats["ram_total_gb"] > 0
    assert stats["cpu_count"] > 0

def test_resource_manager_recommendation():
    """Test that ResourceManager provides recommendations with 25% buffer."""
    rm = ResourceManager()
    stats = rm.get_system_stats()
    recommendation = rm.get_concurrency_recommendation(heavy_task_memory_gb=8.0)
    
    # Calculate expected useable RAM
    buffer_ram = stats["ram_total_gb"] * 0.25
    expected_useable = max(0.5, stats["ram_available_gb"] - buffer_ram)
    expected_heavy = max(1, int(expected_useable // 8.0))
    
    assert recommendation["max_heavy_tasks"] == expected_heavy

@patch('src.core.pipeline.ResourceManager')
def test_pipeline_initializes_with_dynamic_resources(mock_rm_class):
    """Test that the pipeline correctly uses ResourceManager recommendations."""
    # Setup mock recommendation
    mock_rm_instance = MagicMock()
    mock_rm_instance.get_concurrency_recommendation.return_value = {
        "max_heavy_tasks": 2,
        "max_total_tasks": 3,
        "window_size": 6
    }
    mock_rm_class.return_value = mock_rm_instance
    
    config = MagicMock(spec=PipelineConfig)
    config.max_workers = None # Trigger auto-detection
    config.verbose = False
    
    with patch('src.core.pipeline.FileDiscovery'), \
         patch('src.core.pipeline.StudyMaterialGenerator'), \
         patch('src.core.pipeline.AudioProcessor'), \
         patch('src.core.pipeline.ImageProcessor'), \
         patch('src.core.pipeline.TextProcessor'):
        
        pipeline = VideoTranscriptionPipeline(config)
        
        assert pipeline.concurrency == 3
        assert pipeline.window_size == 6
        # Check if semaphore was created with correct value
        # We can't easily check the value of a semaphore once created, but we can verify it exists
        assert hasattr(pipeline, 'heavy_task_semaphore')
