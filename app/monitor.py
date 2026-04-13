"""Core monitoring logic for GlanceWatch."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import httpx

from .config import Config
from .models import MetricResponse, DiskMetricResponse, StatusResponse

logger = logging.getLogger(__name__)


class GlancesMonitor:
    """Monitor system metrics via Glances API."""
    
    def __init__(self, config: Config):
        """Initialize the monitor with configuration."""
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self._last_error: Optional[str] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            base_url=self.config.glances_base_url,
            timeout=self.config.glances_timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def _fetch_glances_endpoint(self, endpoint: str) -> Optional[Any]:
        """Fetch data from Glances API endpoint."""
        if not self.client:
            raise RuntimeError("Monitor not initialized. Use 'async with' context manager.")
        
        try:
            # Try API v4 first (Glances 4.x), then fall back to v3 (Glances 3.x)
            if self.config.glances_base_url.endswith(("/api/3", "/api/4")):
                url = f"/{endpoint}"
            else:
                url = f"/api/4/{endpoint}"  # Try v4 first
            
            logger.debug(f"Fetching Glances endpoint: {url}")
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Received data from {endpoint}: {data}")
            return data
        except httpx.HTTPStatusError as e:
            # If 404 on v4, try API v3 (for older Glances versions)
            if e.response.status_code == 404 and "/api/4/" in url:
                try:
                    url = url.replace("/api/4/", "/api/3/")
                    logger.debug(f"Retrying with API v3: {url}")
                    response = await self.client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    logger.debug(f"Received data from {endpoint} (v3): {data}")
                    return data
                except Exception:
                    pass
            error_msg = f"HTTP error from Glances API: {e.response.status_code}"
            logger.error(error_msg)
            self._last_error = error_msg
            return None
        except httpx.TimeoutException:
            error_msg = f"Timeout connecting to Glances API at {self.config.glances_base_url}"
            logger.error(error_msg)
            self._last_error = error_msg
            return None
        except httpx.RequestError as e:
            error_msg = f"Request error connecting to Glances: {str(e)}"
            logger.error(error_msg)
            self._last_error = error_msg
            return None
        except Exception as e:
            error_msg = f"Unexpected error fetching {endpoint}: {str(e)}"
            logger.error(error_msg)
            self._last_error = error_msg
            return None
    
    async def check_ram(self) -> MetricResponse:
        """Check RAM usage against threshold."""
        data = await self._fetch_glances_endpoint("mem")
        
        if data is None:
            return MetricResponse(
                ok=False,
                value=0.0,
                threshold=self.config.thresholds.ram_percent,
                unit="%",
                error=self._last_error or "Failed to fetch RAM data"
            )
        
        # Glances returns 'percent' field for memory usage
        ram_percent = data.get("percent", 0.0)
        threshold = self.config.thresholds.ram_percent
        
        return MetricResponse(
            ok=ram_percent <= threshold,
            value=ram_percent,
            threshold=threshold,
            unit="%"
        )
    
    async def check_cpu(self) -> MetricResponse:
        """Check CPU usage against threshold."""
        data = await self._fetch_glances_endpoint("cpu")
        
        if data is None:
            return MetricResponse(
                ok=False,
                value=0.0,
                threshold=self.config.thresholds.cpu_percent,
                unit="%",
                error=self._last_error or "Failed to fetch CPU data"
            )
        
        # Glances returns 'total' field for overall CPU usage
        cpu_percent = data.get("total", 0.0)
        threshold = self.config.thresholds.cpu_percent
        
        return MetricResponse(
            ok=cpu_percent <= threshold,
            value=cpu_percent,
            threshold=threshold,
            unit="%"
        )
    
    async def check_disk(self) -> DiskMetricResponse:
        """Check disk usage against threshold."""
        data = await self._fetch_glances_endpoint("fs")
        
        if data is None:
            return DiskMetricResponse(
                ok=False,
                disks=[],
                threshold=self.config.thresholds.disk_percent,
                error=self._last_error or "Failed to fetch disk data"
            )
        
        threshold = self.config.thresholds.disk_percent
        monitored_disks = []
        all_ok = True
        
        # Filter filesystems based on configuration
        for fs in data:
            mount_point = fs.get("mnt_point", "")
            fs_type = fs.get("fs_type", "")
            
            # Skip excluded filesystem types
            if fs_type in self.config.disk.exclude_types:
                logger.debug(f"Skipping {mount_point} (type: {fs_type})")
                continue
            
            # Check if this mount point should be monitored
            if "all" not in self.config.disk.mounts:
                if mount_point not in self.config.disk.mounts:
                    logger.debug(f"Skipping {mount_point} (not in monitored mounts)")
                    continue
            
            # Extract disk metrics
            percent_used = fs.get("percent", 0.0)
            size_gb = fs.get("size", 0) / (1024**3)  # Convert to GB
            used_gb = fs.get("used", 0) / (1024**3)
            free_gb = fs.get("free", 0) / (1024**3)
            
            is_ok = percent_used <= threshold
            if not is_ok:
                all_ok = False
            
            disk_info = {
                "mount_point": mount_point,
                "fs_type": fs_type,
                "percent_used": round(percent_used, 2),
                "size_gb": round(size_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "ok": is_ok
            }
            monitored_disks.append(disk_info)
            logger.debug(f"Disk {mount_point}: {percent_used}% used (threshold: {threshold}%)")
        
        return DiskMetricResponse(
            ok=all_ok,
            disks=monitored_disks,
            threshold=threshold
        )
    
    async def check_status(self) -> StatusResponse:
        """Check overall system status."""
        # Run all checks concurrently
        ram_task = self.check_ram()
        cpu_task = self.check_cpu()
        disk_task = self.check_disk()
        
        ram_result, cpu_result, disk_result = await asyncio.gather(
            ram_task, cpu_task, disk_task
        )
        
        # Overall OK if all individual checks are OK
        overall_ok = ram_result.ok and cpu_result.ok and disk_result.ok
        
        # Collect any errors
        errors = []
        if ram_result.error:
            errors.append(f"RAM: {ram_result.error}")
        if cpu_result.error:
            errors.append(f"CPU: {cpu_result.error}")
        if disk_result.error:
            errors.append(f"Disk: {disk_result.error}")
        
        error_msg = "; ".join(errors) if errors else None
        
        return StatusResponse(
            ok=overall_ok,
            ram=ram_result.model_dump(),
            cpu=cpu_result.model_dump(),
            disk=disk_result.model_dump(),
            error=error_msg
        )
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get additional system information (uptime, load, network, system details)."""
        info = {}
        
        # Get system info (hostname, OS)
        system_data = await self._fetch_glances_endpoint("system")
        if system_data:
            info['system'] = system_data
        
        # Get uptime
        uptime_data = await self._fetch_glances_endpoint("uptime")
        if uptime_data:
            info['uptime'] = uptime_data
        
        # Get load average
        load_data = await self._fetch_glances_endpoint("load")
        if load_data:
            info['load'] = load_data
        
        # Get network stats
        network_data = await self._fetch_glances_endpoint("network")
        if network_data:
            info['network'] = network_data
        
        # Add Python version
        import sys
        info['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        return info
    
    async def test_connection(self) -> bool:
        """Test connection to Glances API."""
        try:
            data = await self._fetch_glances_endpoint("status")
            return data is not None
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
