"""Configuration management for GlanceWatch."""

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class ThresholdConfig(BaseModel):
    """Threshold configuration for monitoring."""

    ram_percent: float = Field(default=80.0, ge=0.0, le=100.0)
    cpu_percent: float = Field(default=80.0, ge=0.0, le=100.0)
    disk_percent: float = Field(default=85.0, ge=0.0, le=100.0)


class DiskConfig(BaseModel):
    """Disk monitoring configuration."""

    mounts: List[str] = Field(default_factory=lambda: ["/"])
    exclude_types: List[str] = Field(
        default_factory=lambda: ["tmpfs", "devtmpfs", "overlay", "squashfs"]
    )

    @field_validator('mounts')
    @classmethod
    def validate_mounts(cls, v):
        if not v:
            raise ValueError("At least one mount point must be specified")
        return v


class Config(BaseModel):
    """Main application configuration."""
    
    # Glances connection
    glances_base_url: str = Field(default="http://localhost:61208")
    glances_timeout: int = Field(default=5, ge=1, le=60)
    
    # Server settings
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    
    # Monitoring thresholds
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    
    # Disk configuration
    disk: DiskConfig = Field(default_factory=DiskConfig)
    
    # Error handling
    return_http_on_failure: Optional[int] = Field(default=None, ge=100, le=599)
    
    # Logging
    log_level: str = Field(default="INFO")
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper


class ConfigLoader:
    """Load and manage application configuration."""
    
    @staticmethod
    def get_config_path() -> Path:
        """Get the configuration file path."""
        # Check if running in Docker
        if os.path.exists("/.dockerenv"):
            return Path("/var/lib/glancewatch/config.yaml")
        
        # Local development
        config_dir = Path.home() / ".config" / "glancewatch"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.yaml"
    
    @staticmethod
    def load_from_yaml(config_path: Optional[Path] = None) -> dict:
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = ConfigLoader.get_config_path()
        
        if not config_path.exists():
            return {}
        
        with open(config_path, "r") as f:
            try:
                return yaml.safe_load(f) or {}
            except yaml.YAMLError:
                return {}
    
    @staticmethod
    def load_from_env() -> dict:
        """Load configuration from environment variables."""
        config = {}
        
        # Glances settings
        if url := os.getenv("GLANCES_BASE_URL"):
            config["glances_base_url"] = url
        if timeout := os.getenv("GLANCES_TIMEOUT"):
            config["glances_timeout"] = int(timeout)
        
        # Server settings
        if host := os.getenv("HOST"):
            config["host"] = host
        if port := os.getenv("PORT"):
            config["port"] = int(port)
        
        # Thresholds
        thresholds = {}
        if ram := os.getenv("RAM_THRESHOLD"):
            thresholds["ram_percent"] = float(ram)
        if cpu := os.getenv("CPU_THRESHOLD"):
            thresholds["cpu_percent"] = float(cpu)
        if disk := os.getenv("DISK_THRESHOLD"):
            thresholds["disk_percent"] = float(disk)
        if thresholds:
            config["thresholds"] = thresholds
        
        # Disk configuration
        disk_config = {}
        if mounts := os.getenv("DISK_MOUNTS"):
            if mounts.lower() == "all":
                disk_config["mounts"] = ["all"]
            else:
                disk_config["mounts"] = [m.strip() for m in mounts.split(",")]
        if exclude := os.getenv("DISK_EXCLUDE_TYPES"):
            disk_config["exclude_types"] = [t.strip() for t in exclude.split(",")]
        if disk_config:
            config["disk"] = disk_config
        
        # Error handling
        if http_code := os.getenv("RETURN_HTTP_ON_FAILURE"):
            config["return_http_on_failure"] = int(http_code)
        
        # Logging
        if log_level := os.getenv("LOG_LEVEL"):
            config["log_level"] = log_level
        
        return config
    
    @staticmethod
    def load() -> Config:
        """Load configuration from all sources (YAML + env vars)."""
        # Start with YAML
        config_data = ConfigLoader.load_from_yaml()
        
        # Override with environment variables
        env_config = ConfigLoader.load_from_env()
        
        # Deep merge
        if "thresholds" in env_config:
            if "thresholds" not in config_data:
                config_data["thresholds"] = {}
            config_data["thresholds"].update(env_config["thresholds"])
            env_config.pop("thresholds")
        
        if "disk" in env_config:
            if "disk" not in config_data:
                config_data["disk"] = {}
            config_data["disk"].update(env_config["disk"])
            env_config.pop("disk")
        
        config_data.update(env_config)
        
        return Config(**config_data)
    
    @staticmethod
    def save(config: Config, config_path: Optional[Path] = None) -> None:
        """Save configuration to YAML file."""
        if config_path is None:
            config_path = ConfigLoader.get_config_path()
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, "w") as f:
            yaml.dump(config.model_dump(), f, default_flow_style=False)
