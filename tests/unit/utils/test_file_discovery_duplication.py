
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from src.utils.file_utils import FileDiscovery
from src.core.config import PipelineConfig

def test_group_files_by_stem_unifies_unicode_duplicates(tmp_path):
    """Test that group_files_by_stem treats files with \u202f as the same as standard spaces."""
    config = MagicMock(spec=PipelineConfig)
    # Mock _is_supported_file to return True for our test files
    discovery = FileDiscovery(config)
    discovery._is_supported_file = MagicMock(return_value=True)
    
    # Create two files that should be grouped together
    file1 = tmp_path / "Screenshot 2025-12-20 at 12.00.48\u202fPM.txt"
    file2 = tmp_path / "Screenshot 2025-12-20 at 12.00.48 PM.txt"
    
    file1.write_text("content1")
    file2.write_text("content2")
    
    groups = discovery.group_files_by_stem(tmp_path)
    
    # There should only be ONE group (one logical file)
    assert len(groups) == 1
    
    # Check that both files are in the same group
    group_key = list(groups.keys())[0]
    file_list = groups[group_key]
    assert len(file_list) == 2
    assert any("\u202f" in str(f) for f in file_list)
    assert any("\u202f" not in str(f) and "PM" in str(f) for f in file_list)
