#!/usr/bin/env python3
"""Simple test to debug the endless run issue."""

import sys
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.processors.audio_processor import AudioProcessor
from src.core.config import PipelineConfig


def test_audio_extraction():
    """Test audio extraction in isolation."""
    print("Testing audio extraction...")
    
    # Create config
    config = PipelineConfig()
    
    # Create processor
    processor = AudioProcessor(config)
    
    # Test paths
    video_path = Path("/tmp/test_progress/016 How to and where to develop the cloud healthcare solution 1 .mp4")
    audio_path = Path("/tmp/test_progress/test_audio.mp3")
    
    print(f"Extracting audio from {video_path}")
    print(f"Output: {audio_path}")
    
    start_time = time.time()
    
    try:
        result = processor.extract_audio_from_video(video_path, audio_path)
        end_time = time.time()
        
        print(f"Result: {result.success}")
        print(f"Message: {result.message}")
        print(f"Duration: {end_time - start_time:.2f} seconds")
        
        if result.success and audio_path.exists():
            print(f"Audio file created: {audio_path.stat().st_size} bytes")
        else:
            print("Audio file not created")
            
    except Exception as e:
        end_time = time.time()
        print(f"Error after {end_time - start_time:.2f} seconds: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_audio_extraction()
