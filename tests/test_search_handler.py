"""Unit tests for `SearchHandler.find_duplicates` — pure rapidfuzz scoring
logic, no Neo4j needed. The full-text-search half needs a live Lucene index
and is covered instead in test_contact_repository.py."""

from __future__ import annotations

import pytest

from app.handlers.search_handler import SearchHandler
from app.models.contact import Contact
from app.models.settings import UserSettings


class _FakeContactRepository:
    def __init__(self, contacts: list[Contact]) -> None:
        self._contacts = contacts

    async def list_contacts(self, **_: object) -> list[Contact]:
        return self._contacts

    async def search_fulltext(self, *_: object, **__: object) -> list[Contact]:
        raise NotImplementedError("not exercised by these tests")


class _FakeSettingsRepository:
    async def get(self) -> UserSettings:
        return UserSettings()


@pytest.mark.asyncio
async def test_find_duplicates_flags_close_name_match() -> None:
    contacts = [Contact(name="Jonathan Smith"), Contact(name="Jonathon Smith")]
    handler = SearchHandler(_FakeContactRepository(contacts), _FakeSettingsRepository())

    candidates = await handler.find_duplicates()

    assert len(candidates) == 1
    assert candidates[0].matched_on == ["name"]
    assert candidates[0].score >= UserSettings().dedup_score_threshold


@pytest.mark.asyncio
async def test_find_duplicates_flags_exact_phone_match_despite_different_names() -> None:
    """A shared phone number is as strong a signal as a name match, even
    when the names (Alex / Alexander) are too different to trip the name
    heuristic on their own."""
    contacts = [
        Contact(name="Alex", phone="+1-555-0100"),
        Contact(name="Alexander", phone="+1-555-0100"),
    ]
    handler = SearchHandler(_FakeContactRepository(contacts), _FakeSettingsRepository())

    candidates = await handler.find_duplicates()

    assert len(candidates) == 1
    assert candidates[0].score == 100.0
    assert candidates[0].matched_on == ["phone"]


@pytest.mark.asyncio
async def test_find_duplicates_ignores_unrelated_contacts() -> None:
    contacts = [Contact(name="Alice Johnson"), Contact(name="Bob Williams")]
    handler = SearchHandler(_FakeContactRepository(contacts), _FakeSettingsRepository())

    assert await handler.find_duplicates() == []


@pytest.mark.asyncio
async def test_find_duplicates_respects_explicit_threshold_override() -> None:
    contacts = [Contact(name="Alice Johnson"), Contact(name="Alice Johnston")]
    handler = SearchHandler(_FakeContactRepository(contacts), _FakeSettingsRepository())

    lenient = await handler.find_duplicates(threshold=70.0)
    assert len(lenient) == 1

    strict = await handler.find_duplicates(threshold=99.0)
    assert strict == []
