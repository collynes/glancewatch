"""Additional tests to boost code coverage to 90%+"""

import pytest
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from app.config import Config, ThresholdConfig, DiskConfig, ConfigLoader
from app.monitor import GlancesMonitor
from app.models import MetricResponse, DiskMetricResponse


# ========================================
# Config Tests - Boost config.py coverage
# ========================================

def test_config_default_values():
    """Test Config with default values."""
    config = Config(glances_base_url="http://localhost:61208")
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.log_level == "INFO"
    assert config.glances_timeout == 5


def test_threshold_config_defaults():
    """Test ThresholdConfig default values."""
    thresholds = ThresholdConfig()
    assert thresholds.ram_percent == 80.0
    assert thresholds.cpu_percent == 80.0
    assert thresholds.disk_percent == 85.0


def test_disk_config_defaults():
    """Test DiskConfig default values."""
    disk = DiskConfig()
    assert disk.mounts == ["/"]
    assert "tmpfs" in disk.exclude_types
    assert "devtmpfs" in disk.exclude_types


def test_get_default_config_path():
    """Test default config path generation."""
    path = ConfigLoader.get_config_path()
    assert "glancewatch" in str(path).lower()
    assert "config.yaml" in str(path)


def test_load_config_nonexistent_file():
    """Test loading config from nonexistent file returns empty dict."""
    result = ConfigLoader.load_from_yaml(Path("/nonexistent/path/config.yaml"))
    assert result == {}


def test_load_config_invalid_yaml():
    """Test loading config with invalid YAML."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("invalid: yaml: content: [[[")
        temp_path = f.name
    
    try:
        result = ConfigLoader.load_from_yaml(Path(temp_path))
        assert result == {}
    finally:
        os.unlink(temp_path)


def test_load_config_valid_yaml():
    """Test loading valid config from YAML."""
    config_data = """
glances_base_url: http://localhost:61208
host: 127.0.0.1
port: 9000
log_level: DEBUG
thresholds:
  ram_percent: 90.0
  cpu_percent: 85.0
  disk_percent: 95.0
disk:
  mounts:
    - /
    - /home
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_data)
        temp_path = f.name
    
    try:
        config_dict = ConfigLoader.load_from_yaml(Path(temp_path))
        assert config_dict is not None
        assert config_dict["host"] == "127.0.0.1"
        assert config_dict["port"] == 9000
        # Create Config from dict
        config = Config(**config_dict)
        assert config.log_level == "DEBUG"
        assert config.thresholds.ram_percent == 90.0
        assert "/home" in config.disk.mounts
    finally:
        os.unlink(temp_path)


def test_save_and_load_config():
    """Test saving and loading config to/from YAML file."""
    config = Config(
        glances_base_url="http://localhost:61208",
        host="192.168.1.1",
        port=8080,
        thresholds=ThresholdConfig(ram_percent=75.0),
        disk=DiskConfig(mounts=["/", "/var"])
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.yaml"
        ConfigLoader.save(config, config_path)
        
        # Verify file was created
        assert config_path.exists()
        
        # Load it back and verify
        loaded_dict = ConfigLoader.load_from_yaml(config_path)
        loaded = Config(**loaded_dict)
        assert loaded is not None
        assert loaded.host == "192.168.1.1"
        assert loaded.port == 8080
        assert loaded.thresholds.ram_percent == 75.0
        assert "/var" in loaded.disk.mounts


def test_config_with_return_http_on_failure():
    """Test Config with return_http_on_failure set."""
    config = Config(
        glances_base_url="http://localhost:61208",
        return_http_on_failure=503
    )
    assert config.return_http_on_failure == 503


def test_config_validation_port_range():
    """Test that Config accepts valid port numbers."""
    config = Config(glances_base_url="http://localhost:61208", port=8080)
    assert config.port == 8080
    
    config2 = Config(glances_base_url="http://localhost:61208", port=65535)
    assert config2.port == 65535


# ========================================
# Monitor Error Handling Tests
# ========================================

@pytest.mark.asyncio
async def test_monitor_timeout_error():
    """Test monitor handling timeout errors."""
    import httpx
    
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(),
        disk=DiskConfig(mounts=["/"])
    )
    
    async def mock_get(*args, **kwargs):
        raise httpx.TimeoutException("Connection timeout")
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_ram()
            assert not result.ok
            assert "timeout" in result.error.lower() or "failed" in result.error.lower()


@pytest.mark.asyncio
async def test_monitor_connection_error():
    """Test monitor handling connection errors."""
    import httpx
    
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(),
        disk=DiskConfig(mounts=["/"])
    )
    
    async def mock_get(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_ram()
            assert not result.ok
            assert result.error is not None


@pytest.mark.asyncio
async def test_monitor_http_error_500():
    """Test monitor handling HTTP 500 errors."""
    import httpx
    
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(),
        disk=DiskConfig(mounts=["/"])
    )
    
    async def mock_get(*args, **kwargs):
        response = AsyncMock()
        response.status_code = 500
        raise httpx.HTTPStatusError("Server Error", request=MagicMock(), response=response)
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_cpu()
            assert not result.ok


@pytest.mark.asyncio
async def test_monitor_missing_percent_field():
    """Test monitor handling missing percent field in response."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(),
        disk=DiskConfig(mounts=["/"])
    )
    
    # RAM response without 'percent' field
    async def mock_get(*args, **kwargs):
        response = AsyncMock()
        response.json = MagicMock(return_value={"total": 16000000000, "used": 8000000000})
        response.raise_for_status = AsyncMock()
        return response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_ram()
            # Should default to 0.0 when percent is missing
            assert result.value == 0.0


@pytest.mark.asyncio
async def test_monitor_disk_filter_by_type():
    """Test disk monitoring filters out excluded filesystem types."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(disk_percent=85.0),
        disk=DiskConfig(mounts=["/"], exclude_types=["tmpfs", "devtmpfs"])
    )
    
    mock_disks = [
        {"mnt_point": "/", "percent": 50.0, "size": 1000000000000, "used": 500000000000, "free": 500000000000, "fs_type": "ext4"},
        {"mnt_point": "/dev", "percent": 90.0, "size": 100000000, "used": 90000000, "free": 10000000, "fs_type": "tmpfs"},
        {"mnt_point": "/run", "percent": 95.0, "size": 100000000, "used": 95000000, "free": 5000000, "fs_type": "devtmpfs"}
    ]
    
    async def mock_get(*args, **kwargs):
        response = AsyncMock()
        response.json = MagicMock(return_value=mock_disks)
        response.raise_for_status = AsyncMock()
        return response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_disk()
            # Should only include / (ext4), not tmpfs or devtmpfs
            assert len(result.disks) == 1
            assert result.disks[0]["mount_point"] == "/"


@pytest.mark.asyncio
async def test_monitor_disk_empty_response():
    """Test disk monitoring with empty response."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(),
        disk=DiskConfig(mounts=["/"])
    )
    
    async def mock_get(*args, **kwargs):
        response = AsyncMock()
        response.json = MagicMock(return_value=[])
        response.raise_for_status = AsyncMock()
        return response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_disk()
            assert len(result.disks) == 0
            assert result.ok  # No disks is not an error


@pytest.mark.asyncio
async def test_monitor_without_context_manager():
    """Test that using monitor without context manager raises error."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(),
        disk=DiskConfig(mounts=["/"])
    )
    
    monitor = GlancesMonitor(config)
    # Without context manager, monitor is not initialized — check_ram returns error MetricResponse
    result = await monitor.check_ram()
    assert result.ok is False
    assert result.error is not None and "not initialized" in result.error


# ========================================
# Models Tests
# ========================================

def test_metric_response_creation():
    """Test MetricResponse model creation."""
    response = MetricResponse(
        ok=True,
        value=45.5,
        threshold=80.0,
        unit="%",
        error=None
    )
    assert response.ok is True
    assert response.value == 45.5
    assert response.threshold == 80.0


def test_disk_metric_response_creation():
    """Test DiskMetricResponse model creation."""
    disks = [
        {"mount": "/", "percent": 50.0, "size_gb": 100.0, "used_gb": 50.0, "free_gb": 50.0, "ok": True},
        {"mount": "/home", "percent": 70.0, "size_gb": 500.0, "used_gb": 350.0, "free_gb": 150.0, "ok": True}
    ]
    
    response = DiskMetricResponse(
        ok=True,
        disks=disks,
        threshold=85.0,
        error=None
    )
    
    assert response.ok is True
    assert len(response.disks) == 2
    assert response.threshold == 85.0


# ========================================
# Integration Tests
# ========================================

@pytest.mark.asyncio
async def test_monitor_api_v4_fallback():
    """Test that monitor falls back to API v4 when v3 returns 404."""
    import httpx
    
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(),
        disk=DiskConfig(mounts=["/"])
    )
    
    call_count = 0

    async def mock_get(self_arg, url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        response = AsyncMock()

        if "/api/4/" in url:
            # First call to v4 - return 404 to trigger fallback
            response.status_code = 404
            raise httpx.HTTPStatusError("Not Found", request=MagicMock(), response=response)
        else:
            # Second call to v3 - return success
            response.json = MagicMock(return_value={"percent": 50.0})
            response.raise_for_status = MagicMock()
            response.status_code = 200
            return response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_ram()
            # Should have tried twice (v3 then v4)
            assert call_count == 2
            assert result.ok


def test_config_yaml_serialization():
    """Test that Config can be serialized to YAML properly."""
    config = Config(
        glances_base_url="http://test:8080",
        host="1.2.3.4",
        port=9999,
        log_level="WARNING",
        glances_timeout=10,
        return_http_on_failure=503,
        thresholds=ThresholdConfig(
            ram_percent=70.0,
            cpu_percent=75.0,
            disk_percent=80.0
        ),
        disk=DiskConfig(
            mounts=["/", "/home", "/var"],
            exclude_types=["tmpfs"]
        )
    )
    
    # Convert to dict
    config_dict = config.model_dump()
    
    assert config_dict["glances_base_url"] == "http://test:8080"
    assert config_dict["host"] == "1.2.3.4"
    assert config_dict["port"] == 9999
    assert config_dict["thresholds"]["ram_percent"] == 70.0
    assert "/var" in config_dict["disk"]["mounts"]
