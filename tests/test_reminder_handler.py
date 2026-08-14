"""Unit tests for `ReminderHandler.build_digest` — pure assembly logic
against fake repositories, no Neo4j needed (mirrors test_search_handler.py's
approach). A live round-trip against a real Neo4j lives in
test_reminder_digest_integration.py since it needs actual
Action/Contact/Interaction nodes to query."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

import pytest

from app.handlers.reminder_handler import ReminderHandler
from app.models.action import Action
from app.models.contact import Contact
from app.models.enums import ActionType
from app.models.settings import UserSettings


class _FakeContactRepository:
    def __init__(self, stale_rows: list[dict[str, object]]) -> None:
        self._stale_rows = stale_rows
        self.seen_threshold_days: int | None = None

    async def list_stale(self, *, threshold_days: int) -> list[dict[str, object]]:
        self.seen_threshold_days = threshold_days
        return self._stale_rows


class _FakeLinkRepository:
    def __init__(
        self, due_rows: list[dict[str, object]], birthday_rows: list[Mapping[str, object]]
    ) -> None:
        self._due_rows = due_rows
        self._birthday_rows = birthday_rows
        self.seen_within_days: int | None = None

    async def list_due_actions(
        self, *, before: date, include_completed: bool = False
    ) -> list[dict[str, object]]:
        return self._due_rows

    async def upcoming_birthdays(self, *, within_days: int) -> list[Mapping[str, object]]:
        self.seen_within_days = within_days
        return self._birthday_rows


class _FakeSettingsRepository:
    def __init__(self, settings: UserSettings) -> None:
        self._settings = settings

    async def get(self) -> UserSettings:
        return self._settings


def _due_row() -> dict[str, object]:
    contact = Contact(name="Ada Lovelace")
    return {
        "contact_id": "c1",
        "contact_name": contact.name,
        "action": Action(type=ActionType.CALL, due_date=date(2026, 8, 1)),
    }


def _stale_row() -> dict[str, object]:
    return {"contact": Contact(name="Alan Turing"), "last_interaction_date": date(2025, 1, 1)}


def _birthday_row() -> dict[str, object]:
    return {
        "name": "Grace Hopper",
        "kind": "contact",
        "birthday": date(2026, 8, 20),
        "contact_id": "c2",
        "relative_id": None,
        "days_away": 10,
    }


@pytest.mark.asyncio
async def test_build_digest_bundles_all_three_views() -> None:
    handler = ReminderHandler(
        _FakeContactRepository([_stale_row()]),
        _FakeLinkRepository([_due_row()], [_birthday_row()]),
        _FakeSettingsRepository(UserSettings()),
    )

    digest = await handler.build_digest()

    assert len(digest.due_actions) == 1
    assert digest.due_actions[0].contact_name == "Ada Lovelace"
    assert len(digest.stale_contacts) == 1
    assert digest.stale_contacts[0].contact.name == "Alan Turing"
    assert len(digest.upcoming_birthdays) == 1
    assert digest.upcoming_birthdays[0].name == "Grace Hopper"


@pytest.mark.asyncio
async def test_build_digest_uses_configured_stale_threshold() -> None:
    contact_repo = _FakeContactRepository([])
    handler = ReminderHandler(
        contact_repo,
        _FakeLinkRepository([], []),
        _FakeSettingsRepository(UserSettings(stale_contact_days=90)),
    )

    await handler.build_digest()

    assert contact_repo.seen_threshold_days == 90


@pytest.mark.asyncio
async def test_build_digest_passes_through_birthday_window_override() -> None:
    link_repo = _FakeLinkRepository([], [])
    handler = ReminderHandler(
        _FakeContactRepository([]), link_repo, _FakeSettingsRepository(UserSettings())
    )

    await handler.build_digest(birthday_within_days=7)

    assert link_repo.seen_within_days == 7


@pytest.mark.asyncio
async def test_build_digest_handles_empty_results() -> None:
    handler = ReminderHandler(
        _FakeContactRepository([]),
        _FakeLinkRepository([], []),
        _FakeSettingsRepository(UserSettings()),
    )

    digest = await handler.build_digest()

    assert digest.due_actions == []
    assert digest.stale_contacts == []
    assert digest.upcoming_birthdays == []
