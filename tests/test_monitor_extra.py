"""Additional monitor tests to reach 90% coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.config import Config, ThresholdConfig, DiskConfig
from app.monitor import GlancesMonitor


@pytest.mark.asyncio
async def test_monitor_general_exception_handling():
    """Test monitor handling general exceptions."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(),
        disk=DiskConfig(mounts=["/"])
    )
    
    async def mock_get(*args, **kwargs):
        raise Exception("Unexpected error")
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_ram()
            assert not result.ok
            assert result.error is not None


@pytest.mark.asyncio
async def test_monitor_test_connection_success():
    """Test successful connection test."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(),
        disk=DiskConfig(mounts=["/"])
    )
    
    async def mock_get(*args, **kwargs):
        response = AsyncMock()
        response.raise_for_status = AsyncMock()
        return response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.test_connection()
            assert result is True


@pytest.mark.asyncio
async def test_monitor_test_connection_failure():
    """Test failed connection test."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(),
        disk=DiskConfig(mounts=["/"])
    )
    
    async def mock_get(*args, **kwargs):
        raise httpx.ConnectError("Connection failed")
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.test_connection()
            assert result is False


@pytest.mark.asyncio
async def test_disk_with_all_mounts():
    """Test disk check with 'all' mounts option."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(disk_percent=85.0),
        disk=DiskConfig(mounts=["all"])
    )
    
    mock_disks = [
        {"mnt_point": "/", "percent": 50.0, "size": 1000000000000, "used": 500000000000, "free": 500000000000, "fs_type": "ext4"},
        {"mnt_point": "/home", "percent": 60.0, "size": 2000000000000, "used": 1200000000000, "free": 800000000000, "fs_type": "ext4"},
    ]
    
    async def mock_get(*args, **kwargs):
        response = AsyncMock()
        response.json = MagicMock(return_value=mock_disks)
        response.raise_for_status = AsyncMock()
        return response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_disk()
            # With 'all', should include all disks (not filtered by tmpfs)
            assert len(result.disks) == 2


@pytest.mark.asyncio
async def test_disk_not_in_monitored_mounts():
    """Test that disks not in monitored mounts are excluded."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(disk_percent=85.0),
        disk=DiskConfig(mounts=["/", "/home"])
    )
    
    mock_disks = [
        {"mnt_point": "/", "percent": 50.0, "size": 1000000000000, "used": 500000000000, "free": 500000000000, "fs_type": "ext4"},
        {"mnt_point": "/home", "percent": 60.0, "size": 2000000000000, "used": 1200000000000, "free": 800000000000, "fs_type": "ext4"},
        {"mnt_point": "/var", "percent": 70.0, "size": 500000000000, "used": 350000000000, "free": 150000000000, "fs_type": "ext4"},
    ]
    
    async def mock_get(*args, **kwargs):
        response = AsyncMock()
        response.json = MagicMock(return_value=mock_disks)
        response.raise_for_status = AsyncMock()
        return response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_disk()
            # Should only include / and /home, not /var
            assert len(result.disks) == 2
            mounts = [d["mount_point"] for d in result.disks]
            assert "/" in mounts
            assert "/home" in mounts
            assert "/var" not in mounts


@pytest.mark.asyncio
async def test_status_check_with_all_ok():
    """Test status check when all metrics are OK."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(ram_percent=80.0, cpu_percent=80.0, disk_percent=85.0),
        disk=DiskConfig(mounts=["/"])
    )
    
    async def mock_get(*args, **kwargs):
        if "/mem" in str(args):
            response_data = {"percent": 50.0}
        elif "/cpu" in str(args):
            response_data = {"total": 45.0}
        else:  # /fs
            response_data = [{"mnt_point": "/", "percent": 60.0, "size": 1000000000000, "used": 600000000000, "free": 400000000000, "fs_type": "ext4"}]
        
        response = AsyncMock()
        response.json = MagicMock(return_value=response_data)
        response.raise_for_status = AsyncMock()
        return response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_status()
            assert result.ok is True
            assert "ram" in result.model_dump()
            assert "cpu" in result.model_dump()
            assert "disk" in result.model_dump()


@pytest.mark.asyncio
async def test_status_check_with_failure():
    """Test status check when one metric fails."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(ram_percent=80.0, cpu_percent=80.0, disk_percent=85.0),
        disk=DiskConfig(mounts=["/"])
    )
    
    async def mock_get(*args, **kwargs):
        if "/mem" in str(args):
            response_data = {"percent": 90.0}  # Above threshold
        elif "/cpu" in str(args):
            response_data = {"total": 45.0}
        else:  # /fs
            response_data = [{"mnt_point": "/", "percent": 60.0, "size": 1000000000000, "used": 600000000000, "free": 400000000000, "fs_type": "ext4"}]
        
        response = AsyncMock()
        response.json = MagicMock(return_value=response_data)
        response.raise_for_status = AsyncMock()
        return response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_status()
            assert result.ok is False  # Should be false because RAM is above threshold


@pytest.mark.asyncio
async def test_cpu_missing_total_field():
    """Test CPU check when total field is missing."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(),
        disk=DiskConfig(mounts=["/"])
    )
    
    async def mock_get(*args, **kwargs):
        response = AsyncMock()
        response.json = MagicMock(return_value={"idle": 50.0, "system": 30.0})  # No 'total' field
        response.raise_for_status = AsyncMock()
        return response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_cpu()
            # Should default to 0.0 when total is missing
            assert result.value == 0.0


@pytest.mark.asyncio
async def test_disk_with_missing_fields():
    """Test disk check with missing size/used/free fields."""
    config = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(disk_percent=85.0),
        disk=DiskConfig(mounts=["/"])
    )
    
    mock_disks = [
        {"mnt_point": "/", "percent": 50.0, "fs_type": "ext4"},  # Missing size, used, free
    ]
    
    async def mock_get(*args, **kwargs):
        response = AsyncMock()
        response.json = MagicMock(return_value=mock_disks)
        response.raise_for_status = AsyncMock()
        return response
    
    with patch('httpx.AsyncClient.get', new=mock_get):
        async with GlancesMonitor(config) as monitor:
            result = await monitor.check_disk()
            # Should still work, using default values for missing fields
            assert len(result.disks) >= 1
            # Check that defaults are applied
            assert result.disks[0]["size_gb"] == 0.0
            assert result.disks[0]["used_gb"] == 0.0
            assert result.disks[0]["free_gb"] == 0.0
