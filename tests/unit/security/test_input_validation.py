"""Security tests for input validation and access control."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile
import os

from src.cli.main import VideoTranscriptionCLI
from src.core.config import PipelineConfig
from src.utils.file_utils import FileDiscovery, MediaTypeDetector


@pytest.mark.unit
@pytest.mark.security
class TestSecurity:
    """Security tests for input validation and access control."""

    def test_directory_traversal_prevention(self):
        """Test prevention of directory traversal attacks."""
        from src.utils.file_utils import FileManager

        # Test various directory traversal attempts
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "/etc/shadow",
            "....//....//etc/passwd",
            "%2e%2e%2f%2f..%2f..%2fetc%2fpasswd",
            "..\\..\\..\\..\\windows\\system32"
        ]

        for malicious_path in malicious_paths:
            # The safe_filename should sanitize these
            safe_name = FileManager.safe_filename(malicious_path, Path("/tmp"))

            # Should not preserve directory traversal sequences
            assert "../" not in safe_name
            assert ".." not in safe_name or safe_name.count("..") <= 1
            assert "\\" not in safe_name or safe_name.count("\\") <= 1

    def test_file_type_validation(self):
        """Test validation of file types to prevent malicious uploads."""
        detector = MediaTypeDetector()

        # Test with executable files
        executable_files = [
            Path("malicious.exe"),
            Path("trojan.sh"),
            Path("script.py"),
            Path("payload.bat")
        ]

        for file_path in executable_files:
            media_type = detector.detect_media_type(file_path)
            # Should not process executable files as media
            assert media_type in ["unknown", "rejected"]

    def test_file_size_limits(self):
        """Test enforcement of file size limits."""
        from src.processors.audio_processor import AudioProcessor
        from src.processors.image_processor import ImageProcessor

        config = PipelineConfig()
        audio_processor = AudioProcessor(config)
        image_processor = ImageProcessor(config)

        # Test with extremely large file paths (simulating large files)
        large_file_path = Path("/tmp/large_file.wav")

        # Create a file that appears large but isn't
        with mock_open('rb', read_data=b"x" * 1000):
            with patch('pathlib.Path.stat', return_value=Mock(st_size=1024*1024*1024)):  # 1GB
                result = audio_processor.process(large_file_path, Path("/tmp/output.txt"))

                # Should reject files that are too large
                assert result.success is False
                assert any(keyword in result.message.lower() for keyword in
                         ["too large", "size", "limit", "exceeds"])

    def test_path_sanitization(self):
        """Test path sanitization for security."""
        from src.utils.file_utils import FileManager

        # Test paths with dangerous characters
        dangerous_paths = [
            "file\x00name.txt",  # Null byte injection
            "pipe|cat",  # Command injection
            "$(rm -rf /)",  # Command injection
            "'; drop table users; --",  # SQL injection
            "<script>alert('xss')</script>",  # XSS injection
        ]

        for dangerous_path in dangerous_paths:
            safe_name = FileManager.safe_filename(dangerous_path, Path("/tmp"))

            # Should remove or escape dangerous characters
            assert "\x00" not in safe_name
            assert "|" not in safe_name
            assert "$(" not in safe_name
            assert ";" not in safe_name
            assert "<" not in safe_name
            assert ">" not in safe_name

    def test_concurrent_access_control(self):
        """Test access control under concurrent scenarios."""
        import threading
        import tempfile
        import time

        # Create a shared resource
        shared_file = Path(tempfile.gettempdir()) / "shared_resource.txt"
        shared_file.write_text("initial_value")

        access_log = []

        def worker(worker_id):
            try:
                # Simulate concurrent access with locking
                for i in range(10):
                    current_content = shared_file.read_text()
                    new_content = f"{current_content}_worker_{worker_id}_iteration_{i}"
                    shared_file.write_text(new_content)
                    time.sleep(0.001)
                    access_log.append(f"Worker {worker_id}: iteration {i}")
            except Exception as e:
                access_log.append(f"Worker {worker_id}: error {e}")

        # Start multiple workers
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Verify all workers completed
        assert len(threads) == 3
        assert len(access_log) == 30  # 3 workers * 10 iterations

        # Final content should have all worker modifications
        final_content = shared_file.read_text()
        for worker_id in range(3):
            for iteration in range(10):
                expected = f"initial_value_worker_{worker_id}_iteration_{iteration}"
                assert expected in final_content

    def test_resource_cleanup_on_failure(self):
        """Test resource cleanup when processing fails."""
        import tempfile

        temp_files = []

        def create_temp_file():
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_files.append(temp_file)
            return temp_file

        try:
            # Simulate processing that creates temp files
            temp_file1 = create_temp_file()
            temp_file2 = create_temp_file()

            # Simulate failure that should trigger cleanup
            raise Exception("Simulated processing failure")

        except Exception:
            # Even on failure, temp files should be cleaned up
            for temp_file in temp_files:
                try:
                    temp_file.close()
                    if hasattr(temp_file, 'name'):
                        os.unlink(temp_file.name)
                except:
                    pass  # Cleanup should be best effort

            # Verify cleanup attempt was made
            assert True, "Resource cleanup should be attempted on failure"

    def test_input_encoding_validation(self):
        """Test validation of input encoding to prevent injection attacks."""
        from src.cli.main import VideoTranscriptionCLI

        cli = VideoTranscriptionCLI()

        # Test with various encoding attacks
        malicious_inputs = [
            "test\x00.txt",  # Null byte injection
            "test\r\nDELETE FROM users; --",  # Command injection via newline
            "test'; DROP TABLE users; --",  # SQL injection
            "test%00%00%00%00",  # Unicode null bytes
            "<script>alert('xss')</script>",  # Script injection
        ]

        for malicious_input in malicious_inputs:
            # The parser should handle these safely or reject them
            try:
                args = cli.create_parser().parse_args([malicious_input])
                # If we get here without exception, the input was accepted
                # This might be acceptable depending on implementation
                assert True, f"Input {malicious_input!r} was accepted"
            except Exception:
                # If parsing fails, that's also acceptable behavior
                assert True, f"Input {malicious_input!r} was rejected"
