"""Expanded tests for monitor module - additional test coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import httpx

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
def test_config_multiple_disks():
    """Create test configuration with multiple disks."""
    return Config(
        glances_base_url="http://localhost:61208",
        glances_timeout=5,
        thresholds=ThresholdConfig(
            ram_percent=80.0,
            cpu_percent=80.0,
            disk_percent=85.0
        ),
        disk=DiskConfig(
            mounts=["/", "/home", "/var"],
            exclude_types=["tmpfs", "devtmpfs"]
        )
    )


# ========================================
# Additional RAM Tests
# ========================================

@pytest.mark.asyncio
async def test_check_ram_exactly_at_threshold(test_config):
    """Test RAM check when exactly at threshold (should be OK)."""
    mock_ram = {"percent": 80.0}
    
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_ram)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_ram()
            assert result.ok is True
            assert result.value == 80.0


@pytest.mark.asyncio
async def test_check_ram_timeout(test_config):
    """Test RAM check handles timeout errors."""
    async def mock_get(*args, **kwargs):
        raise httpx.TimeoutException("Request timeout")
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_ram()
            assert result.ok is False
            assert result.error is not None


@pytest.mark.asyncio
async def test_check_ram_invalid_json(test_config):
    """Test RAM check handles invalid JSON response."""
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = Mock(side_effect=ValueError("Invalid JSON"))
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_ram()
            assert result.ok is False


# ========================================
# Additional CPU Tests
# ========================================

@pytest.mark.asyncio
async def test_check_cpu_exactly_at_threshold(test_config):
    """Test CPU check when exactly at threshold (should be OK)."""
    mock_cpu = {"total": 80.0}
    
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_cpu)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_cpu()
            assert result.ok is True
            assert result.value == 80.0


@pytest.mark.asyncio
async def test_check_cpu_high_precision(test_config):
    """Test CPU check with high precision floating point value."""
    mock_cpu = {"total": 67.89123456}
    
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_cpu)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_cpu()
            assert result.ok is True
            assert result.value == pytest.approx(67.89, rel=0.01)


@pytest.mark.asyncio
async def test_check_cpu_connection_error(test_config):
    """Test CPU check handles connection errors."""
    async def mock_get(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_cpu()
            assert result.ok is False


# ========================================
# Additional Disk Tests
# ========================================

@pytest.mark.asyncio
async def test_check_disk_multiple_mounts(test_config_multiple_disks):
    """Test disk check with multiple mount points."""
    mock_disks = [
        {"mnt_point": "/", "percent": 50.0, "size": 500_000_000_000, "used": 250_000_000_000, "free": 250_000_000_000, "fs_type": "ext4"},
        {"mnt_point": "/home", "percent": 60.0, "size": 1_000_000_000_000, "used": 600_000_000_000, "free": 400_000_000_000, "fs_type": "ext4"},
        {"mnt_point": "/var", "percent": 70.0, "size": 200_000_000_000, "used": 140_000_000_000, "free": 60_000_000_000, "fs_type": "ext4"}
    ]
    
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_disks)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config_multiple_disks) as monitor:
            result = await monitor.check_disk()
            assert result.ok is True
            assert len(result.disks) == 3


@pytest.mark.asyncio
async def test_check_disk_mixed_status(test_config_multiple_disks):
    """Test disk check with some OK and some exceeding."""
    mock_disks = [
        {"mnt_point": "/", "percent": 50.0, "size": 500_000_000_000, "used": 250_000_000_000, "free": 250_000_000_000, "fs_type": "ext4"},
        {"mnt_point": "/home", "percent": 90.0, "size": 1_000_000_000_000, "used": 900_000_000_000, "free": 100_000_000_000, "fs_type": "ext4"},
        {"mnt_point": "/var", "percent": 70.0, "size": 200_000_000_000, "used": 140_000_000_000, "free": 60_000_000_000, "fs_type": "ext4"}
    ]
    
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_disks)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config_multiple_disks) as monitor:
            result = await monitor.check_disk()
            # Overall should fail if any disk exceeds
            assert result.ok is False
            assert result.disks[1]["ok"] is False


@pytest.mark.asyncio
async def test_check_disk_size_calculations(test_config):
    """Test disk size GB calculations."""
    mock_disks = [
        {"mnt_point": "/", "percent": 50.0, "size": 1_000_000_000_000, "used": 500_000_000_000, "free": 500_000_000_000, "fs_type": "ext4"}
    ]
    
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_disks)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_disk()
            disk = result.disks[0]
            # Check GB calculations are reasonable
            assert disk["size_gb"] > 900  # ~931 GB
            assert disk["used_gb"] > 450  # ~466 GB


# ========================================
# Status Tests with Multiple Failures
# ========================================

@pytest.mark.asyncio
async def test_check_status_multiple_failures(test_config):
    """Test status check when multiple metrics exceed thresholds."""
    responses = {
        "/api/4/mem": {"percent": 90.0},
        "/api/4/cpu": {"total": 95.0},
        "/api/4/fs": [{"mnt_point": "/", "percent": 92.0, "size": 500_000_000_000, "used": 460_000_000_000, "free": 40_000_000_000, "fs_type": "ext4"}]
    }
    
    async def mock_get(url, *args, **kwargs):
        mock_response = AsyncMock()
        for key in responses:
            if key in url:
                mock_response.json = MagicMock(return_value=responses[key])
                break
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.check_status()
            assert result.ok is False


# ========================================
# Custom Configuration Tests
# ========================================

@pytest.mark.asyncio
async def test_monitor_with_strict_thresholds():
    """Test monitor with very strict thresholds."""
    strict_config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(ram_percent=10.0, cpu_percent=10.0, disk_percent=10.0),
        disk=DiskConfig(mounts=["/"])
    )
    
    mock_ram = {"percent": 50.0}
    
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_ram)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(strict_config) as monitor:
            result = await monitor.check_ram()
            # Should fail with strict threshold
            assert result.ok is False
            assert result.threshold == 10.0


@pytest.mark.asyncio
async def test_monitor_with_lenient_thresholds():
    """Test monitor with very lenient thresholds."""
    lenient_config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(ram_percent=99.0, cpu_percent=99.0, disk_percent=99.0),
        disk=DiskConfig(mounts=["/"])
    )
    
    mock_ram = {"percent": 95.0}
    
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=mock_ram)
        mock_response.raise_for_status = AsyncMock()
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(lenient_config) as monitor:
            result = await monitor.check_ram()
            # Should pass with lenient threshold
            assert result.ok is True
            assert result.threshold == 99.0


# ========================================
# Connection Tests
# ========================================

@pytest.mark.asyncio
async def test_connection_test_non_200_status(test_config):
    """Test connection test with non-200 HTTP status."""
    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("500 Server Error", request=None, response=None))
        return mock_response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(test_config) as monitor:
            result = await monitor.test_connection()
            assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
