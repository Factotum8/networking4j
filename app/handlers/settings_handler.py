"""Business logic for the single user-configurable settings object (item 6)."""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.models.settings import UserSettings
from app.repositories.settings_repository import SettingsRepository


class SettingsHandler:
    def __init__(self, repo: SettingsRepository) -> None:
        self._repo = repo

    async def get(self) -> UserSettings:
        settings = await self._repo.get()
        logger.debug("Fetched settings (stale_contact_days={})", settings.stale_contact_days)
        return settings

    async def update(self, updates: dict[str, Any]) -> UserSettings:
        updated = await self._repo.update(updates)
        logger.info("Settings updated: {}", list(updates))
        return updated
