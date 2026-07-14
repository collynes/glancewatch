"""Core monitoring logic for GlanceWatch."""

import asyncio
import logging
import sys
from typing import Dict, List, Optional, Any

import httpx

from .config import Config
from .models import MetricResponse, DiskMetricResponse, StatusResponse

logger = logging.getLogger(__name__)


class GlancesMonitor:
    """Monitor system metrics via Glances API."""

    def __init__(self, config: Config):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.config.glances_base_url,
            timeout=self.config.glances_timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _fetch(self, endpoint: str) -> Optional[Any]:
        """Fetch data from Glances API, trying v4 then v3 on 404."""
        if not self.client:
            raise RuntimeError("Monitor not initialized. Use 'async with' context manager.")

        for api_version in ("4", "3"):
            url = f"/api/{api_version}/{endpoint}"
            try:
                response = await self.client.get(url)
                if response.status_code == 404 and api_version == "4":
                    continue  # fall through to v3
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code if e.response is not None else 0
                if status_code == 404 and api_version == "4":
                    continue  # fall through to v3
                if api_version == "3":
                    logger.error(f"HTTP {status_code} from Glances API: {endpoint}")
                    return None
            except httpx.TimeoutException:
                logger.error(f"Timeout connecting to Glances at {self.config.glances_base_url}")
                return None
            except httpx.RequestError as e:
                logger.error(f"Request error fetching {endpoint}: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error fetching {endpoint}: {e}")
                raise  # re-raise so callers can surface the message

        return None

    async def check_ram(self) -> MetricResponse:
        """Check RAM usage against threshold."""
        threshold = self.config.thresholds.ram_percent
        try:
            data = await self._fetch("mem")
        except Exception as e:
            return MetricResponse(ok=False, value=0.0, threshold=threshold, unit="%",
                                  error=str(e))
        if data is None:
            return MetricResponse(ok=False, value=0.0, threshold=threshold, unit="%",
                                  error=f"Failed to fetch RAM data from {self.config.glances_base_url}")
        value = data.get("percent", 0.0)
        return MetricResponse(ok=value <= threshold, value=value, threshold=threshold, unit="%")

    async def check_cpu(self) -> MetricResponse:
        """Check CPU usage against threshold."""
        threshold = self.config.thresholds.cpu_percent
        try:
            data = await self._fetch("cpu")
        except Exception as e:
            return MetricResponse(ok=False, value=0.0, threshold=threshold, unit="%",
                                  error=str(e))
        if data is None:
            return MetricResponse(ok=False, value=0.0, threshold=threshold, unit="%",
                                  error="Failed to fetch CPU data")
        value = data.get("total", 0.0)
        return MetricResponse(ok=value <= threshold, value=value, threshold=threshold, unit="%")

    async def check_disk(self) -> DiskMetricResponse:
        """Check disk usage against threshold."""
        threshold = self.config.thresholds.disk_percent
        try:
            data = await self._fetch("fs")
        except Exception as e:
            return DiskMetricResponse(ok=False, disks=[], threshold=threshold, error=str(e))
        if data is None:
            return DiskMetricResponse(ok=False, disks=[], threshold=threshold,
                                      error="Failed to fetch disk data")

        monitored, all_ok = [], True
        for fs in data:
            mount = fs.get("mnt_point", "")
            fs_type = fs.get("fs_type", "")

            if fs_type in self.config.disk.exclude_types:
                continue
            if "all" not in self.config.disk.mounts and mount not in self.config.disk.mounts:
                continue

            pct = fs.get("percent", 0.0)
            ok = pct <= threshold
            if not ok:
                all_ok = False

            monitored.append({
                "mount_point": mount,
                "fs_type": fs_type,
                "percent_used": round(pct, 2),
                "size_gb": round(fs.get("size", 0) / 1024**3, 2),
                "used_gb": round(fs.get("used", 0) / 1024**3, 2),
                "free_gb": round(fs.get("free", 0) / 1024**3, 2),
                "ok": ok,
            })

        return DiskMetricResponse(ok=all_ok, disks=monitored, threshold=threshold)

    async def check_status(self) -> StatusResponse:
        """Check overall system status (all metrics concurrently)."""
        ram, cpu, disk = await asyncio.gather(
            self.check_ram(), self.check_cpu(), self.check_disk()
        )
        errors = [f"{label}: {r.error}" for label, r in (("RAM", ram), ("CPU", cpu), ("Disk", disk)) if r.error]
        return StatusResponse(
            ok=ram.ok and cpu.ok and disk.ok,
            ram=ram.model_dump(),
            cpu=cpu.model_dump(),
            disk=disk.model_dump(),
            error="; ".join(errors) or None,
        )

    async def get_system_info(self) -> Dict[str, Any]:
        """Get supplementary system info (uptime, load, network, system)."""
        system, uptime, load, network = await asyncio.gather(
            self._fetch("system"),
            self._fetch("uptime"),
            self._fetch("load"),
            self._fetch("network"),
        )
        info = {}
        if system:  info["system"]  = system
        if uptime:  info["uptime"]  = uptime
        if load:    info["load"]    = load
        if network: info["network"] = network
        info["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        return info

    async def test_connection(self) -> bool:
        """Test connection to Glances API."""
        try:
            return await self._fetch("status") is not None
        except Exception:
            return False

