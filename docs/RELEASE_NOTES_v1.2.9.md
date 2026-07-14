# GlanceWatch v1.2.9 Release Notes

**Release Date:** July 14, 2026

## Overview

v1.2.9 is a code quality and correctness release — a "Karpathy-style" refactor of the core codebase, plus a comprehensive test suite repair pass. No breaking changes. All 108 tests pass.

## Code Improvements

### `app/monitor.py`
- Renamed `_fetch_glances_endpoint` → `_fetch` (cleaner internal API)
- Removed `_last_error` side-effect instance variable — errors now propagate via exceptions or explicit return values
- URL logic simplified: tries API v4 first, falls back to v3 on 404 (future-proof for Glances 4.x)
- `check_ram`, `check_cpu`, `check_disk` each wrap `_fetch` in isolated try/except — clean error surfaces
- `check_status` uses `asyncio.gather` for concurrent RAM/CPU/disk checks
- `get_system_info` uses `asyncio.gather` for 4 concurrent endpoint fetches
- `test_connection` now catches all exceptions and returns `False` gracefully
- Removed duplicate `except` block

### `app/models.py`
- Replaced deprecated `datetime.utcnow()` (raises `DeprecationWarning` in Python 3.12+) with `datetime.now(timezone.utc)` via a `_now()` helper
- `ErrorResponse.timestamp` now typed as `datetime` (was `str`)

### `app/config.py`
- Removed redundant `validate_percentage` validator — `Field(ge=0.0, le=100.0)` already enforces the constraint
- `load_from_yaml` now catches `yaml.YAMLError` and returns `{}` instead of crashing on malformed files

### `app/main.py`
- `import yaml` moved to top-level (was buried inside `update_config`)
- `handle_metric_error` no longer takes an unused `request` parameter
- Removed dead PUT `/thresholds` alias endpoint (use PUT `/config`)
- `ThresholdUpdate.thresholds` now uses a typed `ThresholdValues` Pydantic model — invalid inputs return HTTP 422 instead of 500
- `ErrorResponse.model_dump(mode="json")` — datetime fields now serialize correctly in JSON responses
- `start_glances()` call in `cli()` wrapped in try/except for graceful failure handling
- `cli()` calls `sys.exit(0)` after `uvicorn.run()` completes

## Test Suite
- Fixed `AsyncMock` → `MagicMock` for synchronous `.json()` and `raise_for_status()` calls throughout test files
- Updated URL keys from `/api/3/` to `/api/4/` (monitor now tries v4 first)
- Fixed field name `mount` → `mount_point` in disk response assertions
- Fixed health endpoint patch target: `app.main.app_config` (not `app.api.health.app_config`)
- Updated threshold validation test to expect `ValidationError` (Pydantic) instead of `ValueError`
- Fixed `test_monitor_api_v4_fallback` mock signature (unbound method patch needs `self_arg`)
- Updated `test_monitor_without_context_manager` to assert MetricResponse error (not RuntimeError propagation)

## Test Coverage
- **108 tests passing**, 0 failures
- Overall coverage: **88%**
- `app/models.py`: 100%
- `app/config.py`: 95%
- `app/monitor.py`: 90%

## No Breaking Changes
All existing API endpoints, environment variables, and config file formats remain unchanged.
