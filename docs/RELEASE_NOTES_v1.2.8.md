# Release Notes - GlanceWatch v1.2.8

**Release Date:** July 14, 2026

## Summary

Routine dependency update release — bumps all core dependencies to their latest stable versions.

## Dependency Updates

| Package | Previous | Updated |
|---------|----------|---------|
| `fastapi` | `>=0.136.0` | `>=0.139.0` |
| `uvicorn` | `>=0.48.0` | `>=0.51.0` |
| `httpx` | `>=0.27.0` | `>=0.28.1` |
| `pydantic` | `>=2.13.0` | `>=2.13.4` |
| `pydantic-settings` | `>=2.14.0` | `>=2.14.2` |
| `PyYAML` | `>=6.0.1` | `>=6.0.3` |
| `glances` | `>=4.0.0` | `>=4.5.5` |

## No Breaking Changes

All updates are backwards compatible. No changes to GlanceWatch configuration, API, or behavior.

## Upgrade

```bash
pip install --upgrade glancewatch
```
