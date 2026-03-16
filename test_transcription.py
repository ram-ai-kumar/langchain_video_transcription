#!/usr/bin/env python3
"""Test transcription in isolation."""

import sys
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.processors.audio_processor import AudioProcessor
from src.core.config import PipelineConfig


def test_transcription():
    """Test transcription in isolation."""
    print("Testing transcription...")
    
    # Create config
    config = PipelineConfig()
    config.whisper_model = "tiny"  # Use tiny model for faster testing
    
    # Create processor
    processor = AudioProcessor(config)
    
    # Test paths
    audio_path = Path("/tmp/test_progress/test_audio.mp3")
    transcript_path = Path("/tmp/test_progress/test_transcript.txt")
    
    print(f"Transcribing {audio_path}")
    print(f"Output: {transcript_path}")
    
    start_time = time.time()
    
    try:
        result = processor.process(audio_path, transcript_path)
        end_time = time.time()
        
        print(f"Result: {result.success}")
        print(f"Message: {result.message}")
        print(f"Duration: {end_time - start_time:.2f} seconds")
        
        if result.success and transcript_path.exists():
            with open(transcript_path, 'r') as f:
                content = f.read()
            print(f"Transcript length: {len(content)} characters")
            print(f"First 100 chars: {content[:100]}...")
        else:
            print("Transcript file not created")
            
    except Exception as e:
        end_time = time.time()
        print(f"Error after {end_time - start_time:.2f} seconds: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_transcription()
