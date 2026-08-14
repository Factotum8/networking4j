"""Cypher repository for the single `(:AppSettings)` node backing
`app.models.settings.UserSettings` (item 6: user-configurable, global, not
per-contact)."""

from __future__ import annotations

from typing import Any

from app.models.settings import UserSettings
from app.repositories.base import Repository


class SettingsRepository(Repository):
    async def get(self) -> UserSettings:
        query = "MATCH (s:AppSettings) RETURN elementId(s) AS id, s {.*} AS props LIMIT 1"
        record = await self._run_one(query)
        if record is None:
            return UserSettings()  # defaults, not yet persisted
        return UserSettings.model_validate({**record["props"], "id": record["id"]})

    async def update(self, updates: dict[str, Any]) -> UserSettings:
        existing = await self.get()
        if existing.id is None:
            props = {**existing.model_dump(exclude={"id"}), **updates}
            query = (
                "CREATE (s:AppSettings) SET s = $props RETURN elementId(s) AS id, s {.*} AS props"
            )
            record = await self._run_one(query, props=props)
        else:
            query = (
                "MATCH (s:AppSettings) WHERE elementId(s) = $id "
                "SET s += $updates RETURN elementId(s) AS id, s {.*} AS props"
            )
            record = await self._run_one(query, id=existing.id, updates=updates)
        assert record is not None
        return UserSettings.model_validate({**record["props"], "id": record["id"]})
