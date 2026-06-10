"""Config API endpoints — read and write user_config.json via the web UI."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import user_config as uc

logger = logging.getLogger(__name__)
router = APIRouter()

_MASK = "••••••••"


def _mask_api_keys(cfg: dict) -> dict:
    """Return a copy of cfg with non-empty API key values replaced by a placeholder."""
    result = {}
    for section, value in cfg.items():
        if section == "api_keys" and isinstance(value, dict):
            result[section] = {
                k: (_MASK if v else "") for k, v in value.items()
            }
        else:
            result[section] = value
    return result


def _merge_defaults(raw: dict) -> dict:
    """Merge user overrides on top of defaults, section by section."""
    merged = {}
    for section, defaults in uc.DEFAULTS.items():
        merged[section] = {**defaults, **raw.get(section, {})}
    return merged


class ConfigSaveRequest(BaseModel):
    config: Dict[str, Any]


@router.get("/config")
async def get_config():
    """Return current config (API keys masked) plus the factory defaults."""
    raw = uc.get()
    full = _merge_defaults(raw)
    return {
        "config": _mask_api_keys(full),
        "defaults": uc.DEFAULTS,
        "has_user_config": bool(raw),
    }


@router.put("/config")
async def save_config(body: ConfigSaveRequest):
    """
    Persist the submitted config.

    API key fields whose value equals the mask placeholder are left unchanged
    so the browser never has to send the actual secret back.
    """
    new_cfg = body.config
    existing = uc.get()

    # Preserve existing secret if the frontend sent back a masked placeholder
    new_keys = new_cfg.get("api_keys", {})
    existing_keys = existing.get("api_keys", {})
    for k, v in list(new_keys.items()):
        if v == _MASK or set(v) <= {"•"}:
            new_keys[k] = existing_keys.get(k, "")

    try:
        uc.save(new_cfg)
        return {"status": "ok"}
    except Exception as e:
        logger.error("Failed to save user config: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/config")
async def reset_config():
    """Reset all user config to factory defaults."""
    try:
        uc.save({})
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
