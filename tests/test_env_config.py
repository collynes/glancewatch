"""Tests for environment variable configuration."""

import pytest
import os
from unittest.mock import patch

from app.config import ConfigLoader, Config


def test_load_from_env_glances_settings():
    """Test loading Glances settings from environment variables."""
    with patch.dict(os.environ, {
        'GLANCES_BASE_URL': 'http://test-server:8080',
        'GLANCES_TIMEOUT': '10'
    }):
        env_config = ConfigLoader.load_from_env()
        assert env_config['glances_base_url'] == 'http://test-server:8080'
        assert env_config['glances_timeout'] == 10


def test_load_from_env_server_settings():
    """Test loading server settings from environment variables."""
    with patch.dict(os.environ, {
        'HOST': '192.168.1.100',
        'PORT': '9000'
    }):
        env_config = ConfigLoader.load_from_env()
        assert env_config['host'] == '192.168.1.100'
        assert env_config['port'] == 9000


def test_load_from_env_thresholds():
    """Test loading threshold settings from environment variables."""
    with patch.dict(os.environ, {
        'RAM_THRESHOLD': '85.5',
        'CPU_THRESHOLD': '75.0',
        'DISK_THRESHOLD': '90.0'
    }):
        env_config = ConfigLoader.load_from_env()
        assert 'thresholds' in env_config
        assert env_config['thresholds']['ram_percent'] == 85.5
        assert env_config['thresholds']['cpu_percent'] == 75.0
        assert env_config['thresholds']['disk_percent'] == 90.0


def test_load_from_env_disk_mounts():
    """Test loading disk mount configuration from environment variables."""
    with patch.dict(os.environ, {
        'DISK_MOUNTS': '/, /home, /var'
    }):
        env_config = ConfigLoader.load_from_env()
        assert 'disk' in env_config
        assert '/' in env_config['disk']['mounts']
        assert '/home' in env_config['disk']['mounts']
        assert '/var' in env_config['disk']['mounts']


def test_load_from_env_disk_mounts_all():
    """Test loading disk mount configuration with 'all' option."""
    with patch.dict(os.environ, {
        'DISK_MOUNTS': 'all'
    }):
        env_config = ConfigLoader.load_from_env()
        assert 'disk' in env_config
        assert env_config['disk']['mounts'] == ['all']


def test_load_from_env_disk_exclude_types():
    """Test loading disk exclude types from environment variables."""
    with patch.dict(os.environ, {
        'DISK_EXCLUDE_TYPES': 'tmpfs, squashfs, overlay'
    }):
        env_config = ConfigLoader.load_from_env()
        assert 'disk' in env_config
        assert 'tmpfs' in env_config['disk']['exclude_types']
        assert 'squashfs' in env_config['disk']['exclude_types']
        assert 'overlay' in env_config['disk']['exclude_types']


def test_load_from_env_error_handling():
    """Test loading return_http_on_failure from environment variables."""
    with patch.dict(os.environ, {
        'RETURN_HTTP_ON_FAILURE': '503'
    }):
        env_config = ConfigLoader.load_from_env()
        assert env_config['return_http_on_failure'] == 503


def test_load_from_env_log_level():
    """Test loading log level from environment variables."""
    with patch.dict(os.environ, {
        'LOG_LEVEL': 'DEBUG'
    }):
        env_config = ConfigLoader.load_from_env()
        assert env_config['log_level'] == 'DEBUG'


def test_load_from_env_empty():
    """Test loading from environment when no relevant vars are set."""
    # Clear all relevant env vars
    env_vars_to_clear = [
        'GLANCES_BASE_URL', 'GLANCES_TIMEOUT', 'HOST', 'PORT',
        'RAM_THRESHOLD', 'CPU_THRESHOLD', 'DISK_THRESHOLD',
        'DISK_MOUNTS', 'DISK_EXCLUDE_TYPES', 'RETURN_HTTP_ON_FAILURE', 'LOG_LEVEL'
    ]
    
    with patch.dict(os.environ, {}, clear=False):
        for var in env_vars_to_clear:
            os.environ.pop(var, None)
        
        env_config = ConfigLoader.load_from_env()
        assert env_config == {}


def test_load_merges_yaml_and_env():
    """Test that load() merges YAML and environment variables."""
    import tempfile
    from pathlib import Path
    
    # Create a temp config file
    config_data = """
glances_base_url: http://localhost:61208
host: 127.0.0.1
port: 8000
thresholds:
  ram_percent: 80.0
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_data)
        temp_path = Path(f.name)
    
    try:
        # Mock get_config_path to return our temp file
        with patch.object(ConfigLoader, 'get_config_path', return_value=temp_path):
            with patch.dict(os.environ, {
                'PORT': '9000',  # Override port
                'CPU_THRESHOLD': '85.0'  # Add CPU threshold
            }):
                config = ConfigLoader.load()
                
                # Should have base URL from YAML
                assert config.glances_base_url == 'http://localhost:61208'
                # Should have host from YAML
                assert config.host == '127.0.0.1'
                # Should have port from ENV (override)
                assert config.port == 9000
                # Should have RAM threshold from YAML
                assert config.thresholds.ram_percent == 80.0
                # Should have CPU threshold from ENV
                assert config.thresholds.cpu_percent == 85.0
    finally:
        os.unlink(temp_path)


def test_config_validation_invalid_log_level():
    """Test that invalid log level raises validation error."""
    with pytest.raises(ValueError, match="Log level must be one of"):
        Config(
            glances_base_url="http://localhost:61208",
            log_level="INVALID"
        )


def test_threshold_validation_out_of_range():
    """Test that threshold validation catches out-of-range values."""
    from app.config import ThresholdConfig
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ThresholdConfig(ram_percent=150.0)

    with pytest.raises(ValidationError):
        ThresholdConfig(cpu_percent=-10.0)


def test_disk_config_validation_empty_mounts():
    """Test that DiskConfig validates mount points."""
    from app.config import DiskConfig
    
    with pytest.raises(ValueError, match="At least one mount point must be specified"):
        DiskConfig(mounts=[])


def test_config_in_docker_environment():
    """Test that config path is different in Docker environment."""
    # Mock /.dockerenv file existence
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = True
        path = ConfigLoader.get_config_path()
        assert str(path) == "/var/lib/glancewatch/config.yaml"


def test_config_normal_environment():
    """Test that config path uses home directory in normal environment."""
    with patch('os.path.exists', return_value=False):
        path = ConfigLoader.get_config_path()
        assert ".config" in str(path)
        assert "glancewatch" in str(path)
        assert "config.yaml" in str(path)
