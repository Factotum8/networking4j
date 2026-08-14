"""Business logic for stage 8's `/ai/*` endpoints — the backend
`cli/main.py`'s 5 AI-agent scenarios (item 5 in
`networking-app-ai-prompt.md`) talk to over HTTP.

No new Cypher: every scenario reuses a repository method already built for
the dashboard/reminders (stage 5/6) or search (stage 3). The only new work
here is handing that data to an `LLMProvider` — for `add_contact_from_text`
that's turning free text into structured fields; for the other four it's
turning already-fetched data into a natural-language response, per the
user's stage-8 decision that the LLM formats every `/ai/*` response, not
just add-contact's parse.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from loguru import logger

from app.models.ai import ParsedContactFields
from app.models.contact import Contact
from app.models.enums import DimensionLinkType
from app.models.settings import UserSettings


class AiContactNotFoundError(Exception):
    """No contact matched the name given to last-meeting/facts."""


class _LLMSource(Protocol):
    async def parse_contact(self, text: str) -> ParsedContactFields: ...
    async def complete(self, *, system: str, data: Any) -> str: ...


class _ContactSource(Protocol):
    async def create(self, contact: Contact) -> Contact: ...
    async def list_stale(self, *, threshold_days: int) -> list[dict[str, Any]]: ...
    async def search_fulltext(self, query: str, *, limit: int = ...) -> list[Contact]: ...


class _LinkSource(Protocol):
    async def upcoming_birthdays(self, *, within_days: int) -> list[Mapping[str, Any]]: ...
    async def last_interaction(self, contact_id: str) -> Any: ...
    async def list_dimension_links(self, contact_id: str) -> list[dict[str, Any]]: ...


class _SettingsSource(Protocol):
    async def get(self) -> UserSettings: ...


class AiHandler:
    def __init__(
        self,
        llm: _LLMSource,
        contact_repo: _ContactSource,
        link_repo: _LinkSource,
        settings_repo: _SettingsSource,
    ) -> None:
        self._llm = llm
        self._contact_repo = contact_repo
        self._link_repo = link_repo
        self._settings_repo = settings_repo

    async def _find_contact_by_name(self, name: str) -> Contact:
        # Reuses the fuzzy Lucene search from stage 3 rather than requiring
        # an exact match — "facts John" should find "John Smith".
        matches = await self._contact_repo.search_fulltext(name, limit=1)
        if not matches:
            logger.warning("AI lookup: no contact matched name {!r}", name)
            raise AiContactNotFoundError(name)
        contact = matches[0]
        assert contact.id is not None  # every DB-resolved contact has one
        return contact

    async def add_contact_from_text(self, text: str) -> tuple[Contact, str]:
        parsed = await self._llm.parse_contact(text)
        contact = await self._contact_repo.create(Contact(**parsed.model_dump()))
        logger.info("AI add-contact: created {} ({}) from free text", contact.name, contact.id)
        return contact, f"Added {contact.name}."

    async def stale_contacts_summary(self, *, threshold_days: int | None = None) -> str:
        if threshold_days is None:
            settings = await self._settings_repo.get()
            threshold_days = settings.stale_contact_days
        rows = await self._contact_repo.list_stale(threshold_days=threshold_days)
        data = [
            {"name": row["contact"].name, "last_interaction_date": row["last_interaction_date"]}
            for row in rows
        ]
        logger.info("AI stale-contacts: summarizing {} contact(s)", len(data))
        return await self._llm.complete(
            system=(
                "You help a personal-networking app's user stay in touch. Given "
                "this JSON list of contacts they haven't interacted with in a "
                "while (name + last_interaction_date, null meaning never), write "
                "a short, friendly note naming who to reach out to. If the list "
                "is empty, say there's nobody stale right now."
            ),
            data=data,
        )

    async def last_meeting_summary(self, name: str) -> str:
        contact = await self._find_contact_by_name(name)
        assert contact.id is not None
        interaction = await self._link_repo.last_interaction(contact.id)
        data = {
            "contact_name": contact.name,
            "last_interaction": interaction.model_dump(mode="json") if interaction else None,
        }
        logger.info("AI last-meeting: summarizing contact {!r}", contact.name)
        return await self._llm.complete(
            system=(
                "Given a contact's most recent interaction (or null if there's "
                "none on record), answer 'when did I last meet this person and "
                "what happened', in a sentence or two."
            ),
            data=data,
        )

    async def birthdays_summary(self, *, within_days: int = 30) -> str:
        rows = await self._link_repo.upcoming_birthdays(within_days=within_days)
        data = [
            {
                "name": row["name"],
                "kind": row["kind"],
                "birthday": row["birthday"],
                "days_away": row["days_away"],
            }
            for row in rows
        ]
        logger.info("AI birthdays: summarizing {} upcoming birthday(s)", len(data))
        return await self._llm.complete(
            system=(
                "Given this JSON list of upcoming birthdays (contacts and their "
                "relatives, with days_away), write a short reminder of who's "
                "coming up and when. If the list is empty, say there are none "
                "in the window."
            ),
            data=data,
        )

    async def facts_summary(self, name: str) -> str:
        contact = await self._find_contact_by_name(name)
        assert contact.id is not None
        links = await self._link_repo.list_dimension_links(contact.id)
        interests = [
            link["target_name"]
            for link in links
            if link["rel_type"] == DimensionLinkType.INTERESTED_IN
        ]
        data = {"name": contact.name, "notes": contact.notes, "interests": interests}
        logger.info("AI facts: summarizing contact {!r}", contact.name)
        return await self._llm.complete(
            system=(
                "Summarize what's known about this contact — their notes and "
                "interests — in a couple of sentences a user could skim before "
                "seeing them again."
            ),
            data=data,
        )
