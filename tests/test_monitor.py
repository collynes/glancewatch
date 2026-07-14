"""Tests for GlancesMonitor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import Config, ThresholdConfig, DiskConfig
from app.monitor import GlancesMonitor


@pytest.fixture
def test_config():
    """Create test configuration."""
    return Config(
        glances_base_url="http://localhost:61208",
        glances_timeout=5,
        thresholds=ThresholdConfig(
            ram_percent=80.0,
            cpu_percent=80.0,
            disk_percent=85.0
        ),
        disk=DiskConfig(
            mounts=["/"],
            exclude_types=["tmpfs", "devtmpfs"]
        )
    )


@pytest.fixture
def mock_glances_ram_response():
    """Mock Glances RAM response."""
    return {
        "total": 16777216000,
        "available": 8388608000,
        "percent": 50.0,
        "used": 8388608000,
        "free": 8388608000
    }


@pytest.fixture
def mock_glances_cpu_response():
    """Mock Glances CPU response."""
    return {
        "total": 45.5,
        "user": 25.2,
        "system": 15.3,
        "idle": 54.5
    }


@pytest.fixture
def mock_glances_disk_response():
    """Mock Glances disk response."""
    return [
        {
            "device_name": "/dev/sda1",
            "fs_type": "ext4",
            "mnt_point": "/",
            "size": 500000000000,
            "used": 250000000000,
            "free": 250000000000,
            "percent": 50.0
        },
        {
            "device_name": "tmpfs",
            "fs_type": "tmpfs",
            "mnt_point": "/dev",
            "size": 1000000000,
            "used": 100000000,
            "free": 900000000,
            "percent": 10.0
        }
    ]


@pytest.mark.asyncio
async def test_check_ram_ok(test_config, mock_glances_ram_response):
    """Test RAM check when usage is below threshold."""
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_glances_ram_response)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_ram()
            
            assert result.ok is True
            assert result.value == 50.0
            assert result.threshold == 80.0
            assert result.unit == "%"
            assert result.error is None


@pytest.mark.asyncio
async def test_check_ram_threshold_exceeded(test_config, mock_glances_ram_response):
    """Test RAM check when usage exceeds threshold."""
    mock_glances_ram_response["percent"] = 90.0
    
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_glances_ram_response)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_ram()
            
            assert result.ok is False
            assert result.value == 90.0
            assert result.threshold == 80.0


@pytest.mark.asyncio
async def test_check_cpu_ok(test_config, mock_glances_cpu_response):
    """Test CPU check when usage is below threshold."""
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_glances_cpu_response)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_cpu()
            
            assert result.ok is True
            assert result.value == 45.5
            assert result.threshold == 80.0
            assert result.unit == "%"


@pytest.mark.asyncio
async def test_check_disk_ok(test_config, mock_glances_disk_response):
    """Test disk check when usage is below threshold."""
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_glances_disk_response)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_disk()
            
            assert result.ok is True
            assert len(result.disks) == 1  # tmpfs should be excluded
            assert result.disks[0]["mount_point"] == "/"
            assert result.disks[0]["percent_used"] == 50.0
            assert result.threshold == 85.0


@pytest.mark.asyncio
async def test_check_disk_threshold_exceeded(test_config, mock_glances_disk_response):
    """Test disk check when usage exceeds threshold."""
    mock_glances_disk_response[0]["percent"] = 90.0
    
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_glances_disk_response)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_disk()
            
            assert result.ok is False
            assert result.disks[0]["ok"] is False


@pytest.mark.asyncio
async def test_connection_failure(test_config):
    """Test handling of connection failures."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_ram()
            
            assert result.ok is False
            assert result.error is not None
            assert "Connection refused" in result.error or "Unexpected error" in result.error


@pytest.mark.asyncio
async def test_check_status(test_config, mock_glances_ram_response, 
                           mock_glances_cpu_response, mock_glances_disk_response):
    """Test overall status check."""
    responses = {
        "/api/4/mem": mock_glances_ram_response,
        "/api/4/cpu": mock_glances_cpu_response,
        "/api/4/fs": mock_glances_disk_response
    }
    
    async def mock_get(url, *args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=responses.get(url, {}))
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_status()
            
            assert result.ok is True
            assert result.ram["ok"] is True
            assert result.cpu["ok"] is True
            assert result.disk["ok"] is True


@pytest.mark.asyncio
async def test_test_connection_success(test_config):
    """Test successful connection test."""
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value={"status": "ok"})
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.test_connection()
            
            assert result is True


@pytest.mark.asyncio
async def test_test_connection_failure(test_config):
    """Test failed connection test."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.test_connection()
            
            assert result is False
