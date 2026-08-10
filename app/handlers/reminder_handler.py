"""Business logic for stage 5: assembles the daily reminder digest.

No new repository methods needed — the three "needs attention" views (due
actions, stale contacts, upcoming birthdays) already exist from earlier
stages; this just bundles them behind one call so the scheduled job
(`app.services.scheduler`) and the on-demand `GET /reminders/digest`
endpoint share the exact same logic instead of drifting apart.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any, Protocol

from loguru import logger

from app.models.reminder import (
    DueActionEntry,
    ReminderDigest,
    StaleContactEntry,
    UpcomingBirthdayEntry,
)
from app.models.settings import UserSettings


class _ContactSource(Protocol):
    async def list_stale(self, *, threshold_days: int) -> list[dict[str, Any]]: ...


class _LinkSource(Protocol):
    async def list_due_actions(
        self, *, before: date, include_completed: bool = ...
    ) -> list[dict[str, Any]]: ...

    async def upcoming_birthdays(self, *, within_days: int) -> list[Mapping[str, Any]]: ...


class _SettingsSource(Protocol):
    async def get(self) -> UserSettings: ...


class ReminderHandler:
    def __init__(
        self,
        contact_repo: _ContactSource,
        link_repo: _LinkSource,
        settings_repo: _SettingsSource,
    ) -> None:
        self._contact_repo = contact_repo
        self._link_repo = link_repo
        self._settings_repo = settings_repo

    async def build_digest(self, *, birthday_within_days: int = 30) -> ReminderDigest:
        settings = await self._settings_repo.get()

        due_rows = await self._link_repo.list_due_actions(before=date.today())
        stale_rows = await self._contact_repo.list_stale(threshold_days=settings.stale_contact_days)
        birthday_rows = await self._link_repo.upcoming_birthdays(within_days=birthday_within_days)

        digest = ReminderDigest(
            generated_at=datetime.now(UTC),
            due_actions=[DueActionEntry.model_validate(r) for r in due_rows],
            stale_contacts=[StaleContactEntry.model_validate(r) for r in stale_rows],
            upcoming_birthdays=[UpcomingBirthdayEntry.model_validate(r) for r in birthday_rows],
        )
        logger.info(
            "Reminder digest assembled: {} due action(s), {} stale contact(s), "
            "{} upcoming birthday(s)",
            len(digest.due_actions),
            len(digest.stale_contacts),
            len(digest.upcoming_birthdays),
        )
        return digest
