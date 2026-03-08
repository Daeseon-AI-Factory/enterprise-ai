from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any

from app.services.settings_service import SettingsService

router = APIRouter()
service = SettingsService()


class SettingPayload(BaseModel):
    key: str
    data: Any


@router.get("/{key}")
async def get_setting(key: str):
    """Get a saved setting by key."""
    data = await service.get(key)
    if data is None:
        return {"key": key, "data": None}
    return {"key": key, "data": data}


@router.put("")
async def save_setting(payload: SettingPayload):
    """Save a setting."""
    await service.save(payload.key, payload.data)
    return {"status": "saved", "key": payload.key}


@router.delete("/{key}")
async def delete_setting(key: str):
    """Delete a setting."""
    deleted = await service.delete(key)
    return {"status": "deleted" if deleted else "not_found", "key": key}


@router.get("")
async def list_settings():
    """List all setting keys."""
    keys = await service.list_keys()
    return {"keys": keys}
