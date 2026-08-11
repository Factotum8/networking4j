"""Unit tests for `AiHandler` — pure assembly/orchestration logic against
fake repos and a fake LLM provider, no Neo4j/Claude/Codex needed (mirrors
test_reminder_handler.py's / test_search_handler.py's approach). Every
scenario here reuses a repository method already covered against a real
Neo4j elsewhere (stage 3/5/6), so there's nothing new to testcontainer-test.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

import pytest

from app.handlers.ai_handler import AiContactNotFoundError, AiHandler
from app.models.ai import ParsedContactFields
from app.models.contact import Contact
from app.models.enums import DimensionLinkType, InteractionType
from app.models.interaction import Interaction
from app.models.settings import UserSettings


class _FakeLLM:
    def __init__(self, *, parsed: ParsedContactFields | None = None, reply: str = "ok") -> None:
        self._parsed = parsed
        self._reply = reply
        self.seen_system: str | None = None
        self.seen_data: Any = None

    async def parse_contact(self, text: str) -> ParsedContactFields:
        assert self._parsed is not None
        return self._parsed

    async def complete(self, *, system: str, data: Any) -> str:
        self.seen_system = system
        self.seen_data = data
        return self._reply


class _FakeContactRepository:
    def __init__(
        self,
        *,
        stale_rows: list[dict[str, Any]] | None = None,
        search_results: list[Contact] | None = None,
    ) -> None:
        self.created: Contact | None = None
        self._stale_rows = stale_rows or []
        self._search_results = search_results if search_results is not None else []
        self.seen_threshold_days: int | None = None

    async def create(self, contact: Contact) -> Contact:
        self.created = contact
        return contact.model_copy(update={"id": "new-id"})

    async def list_stale(self, *, threshold_days: int) -> list[dict[str, Any]]:
        self.seen_threshold_days = threshold_days
        return self._stale_rows

    async def search_fulltext(self, query: str, *, limit: int = 20) -> list[Contact]:
        return self._search_results


class _FakeLinkRepository:
    def __init__(
        self,
        *,
        birthday_rows: list[Mapping[str, Any]] | None = None,
        last_interaction: Interaction | None = None,
        dimension_links: list[dict[str, Any]] | None = None,
    ) -> None:
        self._birthday_rows = birthday_rows or []
        self._last_interaction = last_interaction
        self._dimension_links = dimension_links or []

    async def upcoming_birthdays(self, *, within_days: int) -> list[Mapping[str, Any]]:
        return self._birthday_rows

    async def last_interaction(self, contact_id: str) -> Interaction | None:
        return self._last_interaction

    async def list_dimension_links(self, contact_id: str) -> list[dict[str, Any]]:
        return self._dimension_links


class _FakeSettingsRepository:
    def __init__(self, settings: UserSettings | None = None) -> None:
        self._settings = settings or UserSettings()

    async def get(self) -> UserSettings:
        return self._settings


@pytest.mark.asyncio
async def test_add_contact_from_text_creates_contact_and_returns_confirmation() -> None:
    parsed = ParsedContactFields(name="Ada Lovelace", city="London")
    llm = _FakeLLM(parsed=parsed)
    contact_repo = _FakeContactRepository()
    handler = AiHandler(llm, contact_repo, _FakeLinkRepository(), _FakeSettingsRepository())

    contact, message = await handler.add_contact_from_text("met Ada Lovelace in London")

    assert contact_repo.created is not None
    assert contact_repo.created.name == "Ada Lovelace"
    assert contact_repo.created.city == "London"
    assert contact.id == "new-id"
    assert "Ada Lovelace" in message


@pytest.mark.asyncio
async def test_stale_contacts_summary_uses_configured_threshold_and_feeds_llm() -> None:
    stale_rows = [
        {"contact": Contact(name="Alan Turing"), "last_interaction_date": date(2025, 1, 1)}
    ]
    llm = _FakeLLM(reply="Reach out to Alan Turing.")
    contact_repo = _FakeContactRepository(stale_rows=stale_rows)
    handler = AiHandler(
        llm,
        contact_repo,
        _FakeLinkRepository(),
        _FakeSettingsRepository(UserSettings(stale_contact_days=90)),
    )

    message = await handler.stale_contacts_summary()

    assert contact_repo.seen_threshold_days == 90
    assert llm.seen_data == [{"name": "Alan Turing", "last_interaction_date": date(2025, 1, 1)}]
    assert message == "Reach out to Alan Turing."


@pytest.mark.asyncio
async def test_stale_contacts_summary_respects_explicit_threshold_override() -> None:
    contact_repo = _FakeContactRepository(stale_rows=[])
    handler = AiHandler(
        _FakeLLM(), contact_repo, _FakeLinkRepository(), _FakeSettingsRepository(UserSettings())
    )

    await handler.stale_contacts_summary(threshold_days=7)

    assert contact_repo.seen_threshold_days == 7


@pytest.mark.asyncio
async def test_last_meeting_summary_feeds_llm_with_matched_contacts_last_interaction() -> None:
    contact = Contact(name="Grace Hopper", id="c1")
    interaction = Interaction(
        id="i1", type=InteractionType.MEETING, date=date(2026, 1, 1), comment="discussed COBOL"
    )
    llm = _FakeLLM(reply="Last met Grace Hopper on 2026-01-01 about COBOL.")
    handler = AiHandler(
        llm,
        _FakeContactRepository(search_results=[contact]),
        _FakeLinkRepository(last_interaction=interaction),
        _FakeSettingsRepository(),
    )

    message = await handler.last_meeting_summary("Grace")

    assert llm.seen_data == {
        "contact_name": "Grace Hopper",
        "last_interaction": interaction.model_dump(mode="json"),
    }
    assert message == "Last met Grace Hopper on 2026-01-01 about COBOL."


@pytest.mark.asyncio
async def test_last_meeting_summary_handles_no_interaction_on_record() -> None:
    contact = Contact(name="Grace Hopper", id="c1")
    llm = _FakeLLM()
    handler = AiHandler(
        llm,
        _FakeContactRepository(search_results=[contact]),
        _FakeLinkRepository(last_interaction=None),
        _FakeSettingsRepository(),
    )

    await handler.last_meeting_summary("Grace")

    assert llm.seen_data == {"contact_name": "Grace Hopper", "last_interaction": None}


@pytest.mark.asyncio
async def test_last_meeting_summary_raises_when_no_contact_matches() -> None:
    handler = AiHandler(
        _FakeLLM(),
        _FakeContactRepository(search_results=[]),
        _FakeLinkRepository(),
        _FakeSettingsRepository(),
    )

    with pytest.raises(AiContactNotFoundError):
        await handler.last_meeting_summary("Nobody")


@pytest.mark.asyncio
async def test_birthdays_summary_feeds_llm_with_trimmed_rows() -> None:
    rows: list[Mapping[str, Any]] = [
        {
            "name": "Grace Hopper",
            "kind": "contact",
            "birthday": date(2026, 8, 20),
            "contact_id": "c2",
            "relative_id": None,
            "days_away": 10,
        }
    ]
    llm = _FakeLLM(reply="Grace Hopper's birthday is in 10 days.")
    handler = AiHandler(
        llm,
        _FakeContactRepository(),
        _FakeLinkRepository(birthday_rows=rows),
        _FakeSettingsRepository(),
    )

    message = await handler.birthdays_summary()

    assert llm.seen_data == [
        {"name": "Grace Hopper", "kind": "contact", "birthday": date(2026, 8, 20), "days_away": 10}
    ]
    assert message == "Grace Hopper's birthday is in 10 days."


@pytest.mark.asyncio
async def test_facts_summary_extracts_notes_and_interested_in_links_only() -> None:
    contact = Contact(name="Alan Turing", id="c1", notes="loves puzzles")
    links = [
        {
            "rel_type": DimensionLinkType.INTERESTED_IN,
            "target_id": "i1",
            "target_name": "cryptography",
        },
        {
            "rel_type": DimensionLinkType.WORKS_AT,
            "target_id": "co1",
            "target_name": "Bletchley Park",
        },
    ]
    llm = _FakeLLM(reply="Alan Turing loves puzzles and cryptography.")
    handler = AiHandler(
        llm,
        _FakeContactRepository(search_results=[contact]),
        _FakeLinkRepository(dimension_links=links),
        _FakeSettingsRepository(),
    )

    message = await handler.facts_summary("Alan")

    assert llm.seen_data == {
        "name": "Alan Turing",
        "notes": "loves puzzles",
        "interests": ["cryptography"],
    }
    assert message == "Alan Turing loves puzzles and cryptography."


@pytest.mark.asyncio
async def test_facts_summary_raises_when_no_contact_matches() -> None:
    handler = AiHandler(
        _FakeLLM(),
        _FakeContactRepository(search_results=[]),
        _FakeLinkRepository(),
        _FakeSettingsRepository(),
    )

    with pytest.raises(AiContactNotFoundError):
        await handler.facts_summary("Nobody")
