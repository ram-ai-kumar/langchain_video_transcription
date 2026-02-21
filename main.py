#!/usr/bin/env python3
"""
Main entry point for the Video Transcription & Study Material Generator.

This script provides a command-line interface for processing videos, audio,
text files, and images into comprehensive study materials with PDF generation.
"""

import sys
from pathlib import Path
from src.cli.main import main

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Main entry point
if __name__ == "__main__":
    main()
