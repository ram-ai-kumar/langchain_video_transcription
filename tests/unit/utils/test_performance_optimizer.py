"""Smoke tests for performance_optimizer module."""

import pytest
from src.utils.performance_optimizer import (
    PerformanceOptimizer,
    DeviceType,
    DeviceInfo,
    get_performance_optimizer,
    optimize_for_current_system
)


@pytest.mark.unit
@pytest.mark.smoke
class TestPerformanceOptimizerSmoke:
    """Smoke tests for PerformanceOptimizer."""

    def test_initialization(self):
        """Test that PerformanceOptimizer can be initialized."""
        optimizer = PerformanceOptimizer()
        assert optimizer is not None
        assert optimizer._device_cache is None
        assert optimizer._optimal_workers is None

    def test_detect_available_devices(self):
        """Test that devices can be detected."""
        optimizer = PerformanceOptimizer()
        devices = optimizer.detect_available_devices()
        
        assert isinstance(devices, list)
        assert len(devices) > 0
        # At minimum, CPU should always be available
        assert any(d.device_type == DeviceType.CPU for d in devices)

    def test_get_optimal_device(self):
        """Test that optimal device can be selected."""
        optimizer = PerformanceOptimizer()
        device = optimizer.get_optimal_device("medium")
        
        assert isinstance(device, DeviceInfo)
        assert device.is_available is True

    def test_get_optimal_worker_count(self):
        """Test that optimal worker count can be calculated."""
        optimizer = PerformanceOptimizer()
        devices = optimizer.detect_available_devices()
        
        for device in devices:
            workers = optimizer.get_optimal_worker_count(device.device_type)
            assert isinstance(workers, int)
            assert workers >= 1

    def test_optimize_whisper_loading(self):
        """Test that whisper loading optimization works."""
        # This is a method in the class, but may not be accessible in all versions
        optimizer = PerformanceOptimizer()
        # Skip if method doesn't exist
        if not hasattr(optimizer, 'optimize_whisper_loading'):
            pytest.skip("optimize_whisper_loading method not available")
        
        device_str, env_vars = optimizer.optimize_whisper_loading("tiny")
        
        assert isinstance(device_str, str)
        assert isinstance(env_vars, dict)
        assert len(env_vars) > 0

    def test_global_optimizer_instance(self):
        """Test that global optimizer instance works."""
        optimizer = get_performance_optimizer()
        assert isinstance(optimizer, PerformanceOptimizer)

    def test_optimize_for_current_system(self):
        """Test that system optimization recommendations work."""
        # This is a standalone function, not a method
        from src.utils.performance_optimizer import optimize_for_current_system
        recommendations = optimize_for_current_system()
        
        assert isinstance(recommendations, dict)
        assert "available_devices" in recommendations
        assert "optimal_device" in recommendations
        assert "optimal_workers" in recommendations
        assert "optimizations" in recommendations


@pytest.mark.unit
@pytest.mark.smoke
class TestDeviceInfoSmoke:
    """Smoke tests for DeviceInfo."""

    def test_device_info_creation(self):
        """Test that DeviceInfo can be created."""
        info = DeviceInfo(
            device_type=DeviceType.CPU,
            device_id=None,
            memory_gb=16.0,
            compute_capability=None,
            is_available=True
        )
        
        assert info.device_type == DeviceType.CPU
        assert info.memory_gb == 16.0
        assert info.is_available is True
