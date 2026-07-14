"""Tests for FastAPI endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.config import Config, ThresholdConfig, DiskConfig
from app.models import MetricResponse, DiskMetricResponse, StatusResponse


@pytest.fixture
def test_config():
    """Create test configuration."""
    return Config(
        glances_base_url="http://localhost:61208",
        host="0.0.0.0",
        port=8000,
        log_level="INFO",
        thresholds=ThresholdConfig(
            ram_percent=80.0,
            cpu_percent=80.0,
            disk_percent=85.0
        ),
        disk=DiskConfig(mounts=["/"]),
        return_http_on_failure=None
    )


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# ========================================
# Root & Health Endpoints
# ========================================

def test_root_endpoint(client):
    """Test root endpoint returns service info or HTML."""
    response = client.get("/")
    
    assert response.status_code == 200
    # Could be HTML (FileResponse) or JSON
    if response.headers.get("content-type", "").startswith("text/html"):
        assert len(response.content) > 0
    else:
        data = response.json()
        assert data["service"] == "GlanceWatch"
        assert "version" in data
        assert "endpoints" in data


def test_health_endpoint(client, test_config):
    """Test health check endpoint."""
    with patch('app.main.app_config', test_config):
        with patch('app.monitor.GlancesMonitor.test_connection', new_callable=AsyncMock) as mock_test:
            mock_test.return_value = True
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "version" in data
            assert "glances_connected" in data
            assert data["glances_url"] == "http://localhost:61208"


def test_health_endpoint_glances_down(client, test_config):
    """Test health check when Glances is unreachable."""
    with patch('app.main.app_config', test_config):
        with patch('app.monitor.GlancesMonitor.test_connection', new_callable=AsyncMock) as mock_test:
            mock_test.return_value = False
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["glances_connected"] is False


# ========================================
# RAM Endpoint Tests
# ========================================

def test_ram_endpoint_ok(client, test_config):
    """Test RAM endpoint when usage is below threshold."""
    mock_result = MetricResponse(
        ok=True,
        value=50.0,
        threshold=80.0,
        unit="%"
    )
    
    with patch('app.main.app_config', test_config):
        with patch('app.monitor.GlancesMonitor.check_ram', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result
            response = client.get("/ram")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["value"] == 50.0
            assert data["threshold"] == 80.0


def test_ram_endpoint_threshold_exceeded(client):
    """Test RAM endpoint when usage exceeds threshold."""
    test_config_with_failure = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(ram_percent=80.0, cpu_percent=80.0, disk_percent=85.0),
        disk=DiskConfig(mounts=["/"]),
        return_http_on_failure=503
    )
    
    mock_result = MetricResponse(
        ok=False,
        value=90.0,
        threshold=80.0,
        unit="%"
    )
    
    with patch('app.main.app_config', test_config_with_failure):
        with patch('app.monitor.GlancesMonitor.check_ram', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result
            response = client.get("/ram")
            
            assert response.status_code == 503
            data = response.json()
            assert data["ok"] is False
            assert data["value"] == 90.0


def test_ram_endpoint_no_http_failure_code(client, test_config):
    """Test RAM endpoint returns 200 even on threshold exceeded when no failure code set."""
    mock_result = MetricResponse(
        ok=False,
        value=90.0,
        threshold=80.0,
        unit="%"
    )
    
    with patch('app.main.app_config', test_config):
        with patch('app.monitor.GlancesMonitor.check_ram', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result
            response = client.get("/ram")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is False


# ========================================
# CPU Endpoint Tests
# ========================================

def test_cpu_endpoint_ok(client, test_config):
    """Test CPU endpoint when usage is below threshold."""
    mock_result = MetricResponse(
        ok=True,
        value=45.5,
        threshold=80.0,
        unit="%"
    )
    
    with patch('app.main.app_config', test_config):
        with patch('app.monitor.GlancesMonitor.check_cpu', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result
            response = client.get("/cpu")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["value"] == 45.5


def test_cpu_endpoint_threshold_exceeded(client):
    """Test CPU endpoint when usage exceeds threshold."""
    test_config_fail = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(ram_percent=80.0, cpu_percent=80.0, disk_percent=85.0),
        disk=DiskConfig(mounts=["/"]),
        return_http_on_failure=503
    )
    
    mock_result = MetricResponse(
        ok=False,
        value=95.0,
        threshold=80.0,
        unit="%"
    )
    
    with patch('app.main.app_config', test_config_fail):
        with patch('app.monitor.GlancesMonitor.check_cpu', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result
            response = client.get("/cpu")
            
            assert response.status_code == 503
            data = response.json()
            assert data["ok"] is False


# ========================================
# Disk Endpoint Tests
# ========================================

def test_disk_endpoint_ok(client, test_config):
    """Test disk endpoint when usage is below threshold."""
    mock_result = DiskMetricResponse(
        ok=True,
        disks=[{
            "mount_point": "/",
            "percent_used": 50.0,
            "size_gb": 500.0,
            "used_gb": 250.0,
            "free_gb": 250.0,
            "ok": True
        }],
        threshold=85.0
    )
    
    with patch('app.main.app_config', test_config):
        with patch('app.monitor.GlancesMonitor.check_disk', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result
            response = client.get("/disk")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert len(data["disks"]) == 1
            assert data["disks"][0]["mount_point"] == "/"


def test_disk_endpoint_threshold_exceeded(client):
    """Test disk endpoint when usage exceeds threshold."""
    test_config_fail = Config(
        glances_base_url="http://localhost:61208",
        thresholds=ThresholdConfig(ram_percent=80.0, cpu_percent=80.0, disk_percent=85.0),
        disk=DiskConfig(mounts=["/"]),
        return_http_on_failure=503
    )
    
    mock_result = DiskMetricResponse(
        ok=False,
        disks=[{
            "mount_point": "/",
            "percent_used": 90.0,
            "size_gb": 500.0,
            "used_gb": 450.0,
            "free_gb": 50.0,
            "ok": False
        }],
        threshold=85.0
    )
    
    with patch('app.main.app_config', test_config_fail):
        with patch('app.monitor.GlancesMonitor.check_disk', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result
            response = client.get("/disk")
            
            assert response.status_code == 503
            data = response.json()
            assert data["ok"] is False


# ========================================
# Status Endpoint Tests
# ========================================

def test_status_endpoint_all_ok(client, test_config):
    """Test overall status endpoint when all metrics OK."""
    mock_result = StatusResponse(
        ok=True,
        ram={"ok": True, "value": 50.0, "threshold": 80.0},
        cpu={"ok": True, "value": 45.0, "threshold": 80.0},
        disk={"ok": True, "threshold": 85.0, "disks": []}
    )
    
    with patch('app.main.app_config', test_config):
        with patch('app.monitor.GlancesMonitor.check_status', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result
            response = client.get("/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert "ram" in data
            assert "cpu" in data
            assert "disk" in data


def test_status_endpoint_threshold_exceeded(client, test_config):
    """Test status endpoint returns 503 when any metric exceeds threshold."""
    mock_result = StatusResponse(
        ok=False,
        ram={"ok": False, "value": 90.0, "threshold": 80.0},
        cpu={"ok": True, "value": 45.0, "threshold": 80.0},
        disk={"ok": True, "threshold": 85.0, "disks": []}
    )
    
    with patch('app.main.app_config', test_config):
        with patch('app.monitor.GlancesMonitor.check_status', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result
            response = client.get("/status")
            
            assert response.status_code == 503
            data = response.json()
            assert data["ok"] is False


# ========================================
# Configuration Endpoints Tests
# ========================================

def test_config_endpoint_get(client, test_config):
    """Test GET /config endpoint."""
    with patch('app.main.app_config', test_config):
        response = client.get("/config")
        
        assert response.status_code == 200
        data = response.json()
        assert data["glances_base_url"] == "http://localhost:61208"
        assert "thresholds" in data
        assert data["thresholds"]["ram_percent"] == 80.0
        assert data["thresholds"]["cpu_percent"] == 80.0
        assert data["thresholds"]["disk_percent"] == 85.0
        assert "disk_mounts" in data


def test_thresholds_endpoint_get(client, test_config):
    """Test GET /thresholds endpoint."""
    with patch('app.main.app_config', test_config):
        response = client.get("/thresholds")
        
        assert response.status_code == 200
        data = response.json()
        assert "thresholds" in data
        assert data["thresholds"]["ram_percent"] == 80.0
        assert data["thresholds"]["cpu_percent"] == 80.0
        assert data["thresholds"]["disk_percent"] == 85.0


def test_config_endpoint_update(client, test_config):
    """Test PUT /config endpoint."""
    update_data = {
        "thresholds": {
            "ram_percent": 90,
            "cpu_percent": 85,
            "disk_percent": 95
        }
    }
    
    with patch('app.main.app_config', test_config):
        with patch('app.config.ConfigLoader.get_config_path', return_value="/tmp/test_config.yaml"):
            with patch('builtins.open', MagicMock()):
                response = client.put("/config", json=update_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert data["thresholds"]["ram_percent"] == 90.0
                assert data["thresholds"]["cpu_percent"] == 85.0


def test_thresholds_endpoint_update(client, test_config):
    """Test PUT /thresholds endpoint."""
    update_data = {
        "thresholds": {
            "ram_percent": 70,
            "cpu_percent": 75,
            "disk_percent": 80
        }
    }
    
    with patch('app.main.app_config', test_config):
        with patch('app.config.ConfigLoader.get_config_path', return_value="/tmp/test_config.yaml"):
            with patch('builtins.open', MagicMock()):
                response = client.put("/config", json=update_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert data["thresholds"]["ram_percent"] == 70.0


def test_config_update_partial(client, test_config):
    """Test partial threshold update."""
    update_data = {
        "thresholds": {
            "ram_percent": 95
        }
    }
    
    with patch('app.main.app_config', test_config):
        with patch('app.config.ConfigLoader.get_config_path', return_value="/tmp/test_config.yaml"):
            with patch('builtins.open', MagicMock()):
                response = client.put("/config", json=update_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["thresholds"]["ram_percent"] == 95.0
                # Others should remain unchanged
                assert data["thresholds"]["cpu_percent"] == 80.0


# ========================================
# Error Handling Tests
# ========================================

def test_error_handling_ram(client, test_config):
    """Test error handling when RAM monitor raises exception."""
    with patch('app.main.app_config', test_config):
        with patch('app.monitor.GlancesMonitor.check_ram', new_callable=AsyncMock) as mock_check:
            mock_check.side_effect = Exception("Test error")
            response = client.get("/ram")
            
            # Should return 200 with error in response by default
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is False
            assert "error" in data


def test_error_handling_cpu(client, test_config):
    """Test error handling when CPU monitor raises exception."""
    with patch('app.main.app_config', test_config):
        with patch('app.monitor.GlancesMonitor.check_cpu', new_callable=AsyncMock) as mock_check:
            mock_check.side_effect = Exception("Connection timeout")
            response = client.get("/cpu")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is False


def test_error_handling_status(client, test_config):
    """Test error handling when status check raises exception."""
    with patch('app.main.app_config', test_config):
        with patch('app.monitor.GlancesMonitor.check_status', new_callable=AsyncMock) as mock_check:
            mock_check.side_effect = Exception("Glances unreachable")
            response = client.get("/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is False


def test_config_update_error_handling(client, test_config):
    """Test config update error handling."""
    update_data = {
        "thresholds": {
            "ram_percent": "invalid"  # Invalid type
        }
    }
    
    with patch('app.main.app_config', test_config):
        response = client.put("/config", json=update_data)
        
        # FastAPI should return 422 for validation error
        assert response.status_code == 422


# ========================================
# Integration Tests
# ========================================

def test_full_workflow(client, test_config):
    """Test complete workflow: check status, update config, check again."""
    # Initial status check
    mock_result_1 = StatusResponse(
        ok=True,
        ram={"ok": True, "value": 50.0, "threshold": 80.0},
        cpu={"ok": True, "value": 45.0, "threshold": 80.0},
        disk={"ok": True, "threshold": 85.0, "disks": []}
    )
    
    with patch('app.main.app_config', test_config):
        with patch('app.monitor.GlancesMonitor.check_status', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result_1
            response = client.get("/status")
            assert response.status_code == 200
            
        # Update threshold
        with patch('app.config.ConfigLoader.get_config_path', return_value="/tmp/test.yaml"):
            with patch('builtins.open', MagicMock()):
                update_response = client.put("/config", json={
                    "thresholds": {"ram_percent": 60}
                })
                assert update_response.status_code == 200
                
        # Check status again (should now fail with higher RAM usage)
        mock_result_2 = StatusResponse(
            ok=False,
            ram={"ok": False, "value": 65.0, "threshold": 60.0},
            cpu={"ok": True, "value": 45.0, "threshold": 80.0},
            disk={"ok": True, "threshold": 85.0, "disks": []}
        )
        
        with patch('app.monitor.GlancesMonitor.check_status', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result_2
            response = client.get("/status")
            assert response.status_code == 503  # Now fails
            data = response.json()
            assert data["ok"] is False


# ========================================
# API Documentation Tests
# ========================================

def test_openapi_docs_available(client):
    """Test that OpenAPI docs are available at /api."""
    response = client.get("/api")
    assert response.status_code == 200
    # Should return HTML with Swagger UI


def test_openapi_json_available(client):
    """Test that OpenAPI JSON schema is available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert data["info"]["title"] == "GlanceWatch"

