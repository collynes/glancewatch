"""FastAPI application for GlanceWatch."""

import argparse
import logging
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
import yaml
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from . import __version__
from .config import Config, ConfigLoader
from .monitor import GlancesMonitor
from .models import (
    MetricResponse,
    DiskMetricResponse,
    StatusResponse,
    ConfigResponse,
    ErrorResponse
)
from .api.health import router as health_router

# Configure logging - Professional, minimal output by default
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Suppress noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Global config
app_config: Config = None
start_time: float = 0


def check_glances_running() -> bool:
    """Check if Glances is running"""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "glances"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def start_glances():
    """Start Glances in web mode"""
    try:
        subprocess.Popen(
            ["glances", "-w"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Wait for Glances to start
        time.sleep(3)
        return True
    except FileNotFoundError:
        logger.error("Glances not found. Please install: pip install glances")
        return False
    except Exception as e:
        logger.error(f"Failed to start Glances: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - runs startup and shutdown tasks."""
    global app_config, start_time
    
    start_time = time.time()
    
    # Startup - Load configuration
    app_config = ConfigLoader.load()
    
    # Mount UI at root
    ui_dir = Path(__file__).parent / "ui"
    if ui_dir.exists():
        app.mount("/static", StaticFiles(directory=str(ui_dir)), name="static")
        app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")
    else:
        logger.warning(f"UI directory not found: {ui_dir}")
    
    yield
    
    # Shutdown - No logging needed for clean exit


# Create FastAPI app
app = FastAPI(
    title="GlanceWatch",
    description="Lightweight monitoring adapter for Glances + Uptime Kuma",
    version=__version__,
    lifespan=lifespan,
    docs_url="/api",  # Changed from /docs
    redoc_url=None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)


def get_error_response(message: str, detail: str = None) -> dict:
    """Create standardized error response."""
    return ErrorResponse(ok=False, error=message, detail=detail).model_dump(mode="json")


async def handle_metric_error(metric_name: str, error: Exception):
    """Handle metric check errors with configurable HTTP status codes."""
    error_msg = f"Error checking {metric_name}"
    detail = str(error)
    logger.error(f"{error_msg}: {detail}")
    http_status = app_config.return_http_on_failure or status.HTTP_200_OK
    return JSONResponse(status_code=http_status, content=get_error_response(error_msg, detail))


@app.get("/", tags=["Info"])
async def root():
    """Root endpoint - serves the UI with dynamic version injection."""
    ui_file = Path(__file__).parent / "ui" / "index.html"
    if ui_file.exists():
        # Read HTML and inject version dynamically
        html_content = ui_file.read_text()
        html_content = html_content.replace("{{VERSION}}", __version__)
        return HTMLResponse(content=html_content)
    return {
        "service": "GlanceWatch",
        "version": __version__,
        "description": "Lightweight monitoring adapter for Glances + Uptime Kuma",
        "endpoints": {
            "ui": "/",
            "health": "/health",
            "status": "/status",
            "ram": "/ram",
            "cpu": "/cpu",
            "disk": "/disk",
            "config": "/config",
            "api_docs": "/api",
            "docs": "/docs"
        }
    }


@app.get("/docs", tags=["Info"])
async def docs():
    """Documentation page - how to add endpoints to Uptime Kuma."""
    docs_file = Path(__file__).parent / "ui" / "docs.html"
    if docs_file.exists():
        return FileResponse(docs_file)
    return {
        "error": "Documentation page not found",
        "message": "Please refer to the GitHub repository for setup instructions"
    }


@app.get("/status", response_model=StatusResponse, tags=["Monitoring"])
async def get_status(request: Request):
    """
    Get overall system status for all metrics.
    
    Returns combined RAM, CPU, and disk status with overall ok/not-ok status.
    Returns HTTP 503 when any threshold is exceeded (for Uptime Kuma alerting).
    """
    try:
        async with GlancesMonitor(app_config) as monitor:
            result = await monitor.check_status()
            
            # Return HTTP 503 when thresholds are exceeded
            if not result.ok:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content=result.model_dump(mode='json')
                )
            
            return result
    
    except Exception as e:
        return await handle_metric_error("status", e)


@app.get("/ram", response_model=MetricResponse, tags=["Monitoring"])
async def get_ram_status(request: Request):
    """Check RAM usage against configured threshold."""
    try:
        async with GlancesMonitor(app_config) as monitor:
            result = await monitor.check_ram()
            if not result.ok and app_config.return_http_on_failure:
                return JSONResponse(status_code=app_config.return_http_on_failure,
                                    content=result.model_dump(mode='json'))
            return result
    except Exception as e:
        return await handle_metric_error("RAM", e)


@app.get("/cpu", response_model=MetricResponse, tags=["Monitoring"])
async def get_cpu_status(request: Request):
    """Check CPU usage against configured threshold."""
    try:
        async with GlancesMonitor(app_config) as monitor:
            result = await monitor.check_cpu()
            if not result.ok and app_config.return_http_on_failure:
                return JSONResponse(status_code=app_config.return_http_on_failure,
                                    content=result.model_dump(mode='json'))
            return result
    except Exception as e:
        return await handle_metric_error("CPU", e)


@app.get("/disk", response_model=DiskMetricResponse, tags=["Monitoring"])
async def get_disk_status(request: Request):
    """Check disk usage against configured threshold."""
    try:
        async with GlancesMonitor(app_config) as monitor:
            result = await monitor.check_disk()
            if not result.ok and app_config.return_http_on_failure:
                return JSONResponse(status_code=app_config.return_http_on_failure,
                                    content=result.model_dump(mode='json'))
            return result
    except Exception as e:
        return await handle_metric_error("disk", e)


@app.get("/config", response_model=ConfigResponse, tags=["Configuration"])
async def get_config():
    """
    Get current configuration (read-only).
    
    Returns current thresholds and monitoring settings without exposing sensitive data.
    """
    return ConfigResponse(
        glances_base_url=app_config.glances_base_url,
        thresholds={
            "ram_percent": app_config.thresholds.ram_percent,
            "cpu_percent": app_config.thresholds.cpu_percent,
            "disk_percent": app_config.thresholds.disk_percent
        },
        disk_mounts=app_config.disk.mounts
    )


@app.get("/system-info", tags=["Monitoring"])
async def get_system_info():
    """
    Get additional system information (uptime, load average, network stats).
    
    Returns supplementary system metrics beyond CPU/RAM/Disk.
    """
    try:
        async with GlancesMonitor(app_config) as monitor:
            info = await monitor.get_system_info()
            return JSONResponse(content=info)
    except Exception as e:
        logger.error(f"Error fetching system info: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )


@app.get("/thresholds", response_model=dict, tags=["Configuration"])
async def get_thresholds():
    """
    Get current thresholds only (simpler endpoint).
    
    Returns just the threshold values without other config.
    """
    return {
        "thresholds": {
            "ram_percent": app_config.thresholds.ram_percent,
            "cpu_percent": app_config.thresholds.cpu_percent,
            "disk_percent": app_config.thresholds.disk_percent
        }
    }


class ThresholdValues(BaseModel):
    """Typed threshold values for validation."""
    ram_percent: Optional[float] = None
    cpu_percent: Optional[float] = None
    disk_percent: Optional[float] = None


class ThresholdUpdate(BaseModel):
    """Request model for updating thresholds."""
    thresholds: ThresholdValues


@app.put("/config", tags=["Configuration"])
async def update_config(update: ThresholdUpdate):
    """
    Update monitoring thresholds.
    
    Updates are applied in-memory immediately and persisted to config.yaml.
    """
    global app_config
    
    try:
        # Update thresholds
        new_thresholds = update.thresholds
        
        if new_thresholds.ram_percent is not None:
            app_config.thresholds.ram_percent = new_thresholds.ram_percent
        if new_thresholds.cpu_percent is not None:
            app_config.thresholds.cpu_percent = new_thresholds.cpu_percent
        if new_thresholds.disk_percent is not None:
            app_config.thresholds.disk_percent = new_thresholds.disk_percent

        # Persist to config.yaml
        config_path = ConfigLoader.get_config_path()
        config_data = {
            "thresholds": {
                "ram_percent": app_config.thresholds.ram_percent,
                "cpu_percent": app_config.thresholds.cpu_percent,
                "disk_percent": app_config.thresholds.disk_percent
            }
        }
        
        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        logger.info(f"Configuration updated: {new_thresholds}")
        
        return {
            "ok": True,
            "message": "Configuration updated successfully",
            "thresholds": {
                "ram_percent": app_config.thresholds.ram_percent,
                "cpu_percent": app_config.thresholds.cpu_percent,
                "disk_percent": app_config.thresholds.disk_percent
            }
        }
    
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"ok": False, "error": f"Failed to update configuration: {str(e)}"}
        )


def cli():
    """CLI entry point for glancewatch command."""
    parser = argparse.ArgumentParser(
        description="GlanceWatch - Lightweight monitoring adapter for Glances + Uptime Kuma",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--ignore-glances",
        action="store_true",
        help="Skip automatic Glances installation and startup check"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Override the port number (default: from config.yaml or 8000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        help="Override the host address (default: from config.yaml or 0.0.0.0)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (shows all HTTP requests)"
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet mode (only show errors)"
    )
    
    args = parser.parse_args()
    
    # Configure logging based on verbosity flags
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
        logger.setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        logger.setLevel(logging.INFO)
        logging.getLogger("httpx").setLevel(logging.INFO)
        logging.getLogger("httpcore").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    
    # Load configuration
    config = ConfigLoader.load()
    
    # Override config with CLI arguments if provided
    if args.port:
        config.port = args.port
    if args.host:
        config.host = args.host
    
    # Check and start Glances if needed (unless --ignore-glances is set)
    if not args.ignore_glances:
        if not check_glances_running():
            if not args.quiet:
                print("⚠️  Glances is not running. Starting Glances...")
            try:
                if not start_glances():
                    if not args.quiet:
                        print("⚠️  Failed to start Glances automatically")
                        print("   You may need to start it manually: glances -w")
            except Exception as e:
                if not args.quiet:
                    print(f"⚠️  WARNING: Failed to start Glances: {e}")
                    print("   You may need to start it manually: glances -w")
        elif args.verbose:
            print("✓ Glances is already running")
    elif args.verbose:
        print("⚠️  Skipping Glances check (--ignore-glances flag set)")
    
    # Clean, professional startup message
    if not args.quiet:
        print(f"\nGlanceWatch v{__version__} starting...")
        print(f"Dashboard: http://{'localhost' if config.host == '0.0.0.0' else config.host}:{config.port}/")
        if args.verbose:
            print(f"API Docs:  http://{'localhost' if config.host == '0.0.0.0' else config.host}:{config.port}/api")
            print(f"Glances:   {config.glances_base_url}")
        print("")
    
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        log_level="error" if args.quiet else "warning",
        access_log=args.verbose
    )
    sys.exit(0)


if __name__ == "__main__":
    cli()
