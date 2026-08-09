"""`/settings` — the single user-configurable settings object (item 6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_settings_handler
from app.handlers.settings_handler import SettingsHandler
from app.models.settings import UserSettings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    stale_contact_days: int | None = Field(default=None, ge=1)
    dedup_score_threshold: float | None = Field(default=None, ge=0, le=100)


@router.get("", response_model=UserSettings)
async def get_settings(handler: SettingsHandler = Depends(get_settings_handler)) -> UserSettings:
    return await handler.get()


@router.patch("", response_model=UserSettings)
async def update_settings(
    updates: SettingsUpdate, handler: SettingsHandler = Depends(get_settings_handler)
) -> UserSettings:
    return await handler.update(updates.model_dump(exclude_none=True))
