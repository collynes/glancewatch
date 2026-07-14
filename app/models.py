"""Data models for GlanceWatch API."""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MetricResponse(BaseModel):
    """Standard response format for metric endpoints."""

    ok: bool = Field(description="Whether the metric is within threshold")
    value: float = Field(description="Current metric value")
    threshold: float = Field(description="Configured threshold")
    unit: str = Field(description="Unit of measurement (%, GB, etc)")
    last_check: datetime = Field(default_factory=_now, description="Timestamp of last check")
    error: Optional[str] = Field(default=None, description="Error message if check failed")


class DiskMetricResponse(BaseModel):
    """Response format for disk metrics with multiple mount points."""

    ok: bool = Field(description="Whether all disks are within threshold")
    disks: List[Dict[str, Any]] = Field(description="List of disk metrics")
    threshold: float = Field(description="Configured threshold")
    last_check: datetime = Field(default_factory=_now, description="Timestamp of last check")
    error: Optional[str] = Field(default=None, description="Error message if check failed")


class StatusResponse(BaseModel):
    """Overall system status response."""

    ok: bool = Field(description="Whether all metrics are within thresholds")
    ram: Dict[str, Any] = Field(description="RAM status")
    cpu: Dict[str, Any] = Field(description="CPU status")
    disk: Dict[str, Any] = Field(description="Disk status")
    last_check: datetime = Field(default_factory=_now, description="Timestamp of last check")
    error: Optional[str] = Field(default=None, description="Error message if check failed")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status (healthy/unhealthy)")
    version: str = Field(description="Application version")
    glances_connected: bool = Field(description="Whether Glances API is reachable")
    glances_url: str = Field(description="Configured Glances URL")
    uptime_seconds: float = Field(description="Service uptime in seconds")
    timestamp: datetime = Field(default_factory=_now, description="Current timestamp")


class ConfigResponse(BaseModel):
    """Configuration view response (read-only)."""

    glances_base_url: str = Field(description="Glances API base URL")
    thresholds: Dict[str, float] = Field(description="Configured thresholds")
    disk_mounts: List[str] = Field(description="Monitored disk mount points")
    timestamp: datetime = Field(default_factory=_now, description="Current timestamp")


class ErrorResponse(BaseModel):
    """Error response format."""

    ok: bool = Field(default=False, description="Always false for errors")
    error: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=_now, description="Error timestamp")
