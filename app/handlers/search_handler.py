"""Business logic for stage 3: full-text search and duplicate detection.

Detection only — see `app.models.duplicate.DuplicateCandidate`'s docstring
for why there's no merge/resolve action here (explicit user decision).
"""

from __future__ import annotations

from itertools import combinations
from typing import Protocol

from loguru import logger
from rapidfuzz import fuzz

from app.models.contact import Contact
from app.models.duplicate import DuplicateCandidate
from app.models.settings import UserSettings


class _ContactSource(Protocol):
    """What SearchHandler needs from a contact repository — structural, so
    tests can substitute an in-memory fake without importing the real
    (Neo4j-backed) ContactRepository."""

    async def list_contacts(self) -> list[Contact]: ...
    async def search_fulltext(self, query: str, *, limit: int = ...) -> list[Contact]: ...


class _SettingsSource(Protocol):
    async def get(self) -> UserSettings: ...


# rapidfuzz's 0-100 scale. Below this, two names are treated as unrelated
# rather than "maybe the same person, slightly misspelled".
_NAME_MATCH_FLOOR = 80.0


def _matched_on(a: Contact, b: Contact, name_score: float) -> list[str]:
    matched: list[str] = []
    if name_score >= _NAME_MATCH_FLOOR:
        matched.append("name")
    if a.phone and b.phone and a.phone == b.phone:
        matched.append("phone")
    if a.email and b.email and a.email.casefold() == b.email.casefold():
        matched.append("email")
    return matched


def _pair_candidate(a: Contact, b: Contact) -> DuplicateCandidate | None:
    name_score = fuzz.token_sort_ratio(a.name, b.name)
    matched = _matched_on(a, b, name_score)
    if not matched:
        logger.debug(
            "No duplicate signal between {!r} and {!r} (name score {:.1f})",
            a.name,
            b.name,
            name_score,
        )
        return None
    # An exact phone/email match is as strong a duplicate signal as an exact
    # name match, even when the names themselves differ (nicknames, married
    # names, a typo'd entry) — score those pairs at name-match parity rather
    # than leaving them at whatever the (possibly low) name similarity was.
    score = 100.0 if ("phone" in matched or "email" in matched) else name_score
    logger.debug(
        "Duplicate candidate: {!r} / {!r}, score {:.1f}, matched on {}",
        a.name,
        b.name,
        score,
        matched,
    )
    return DuplicateCandidate(contact_a=a, contact_b=b, score=score, matched_on=matched)


class SearchHandler:
    def __init__(self, contact_repo: _ContactSource, settings_repo: _SettingsSource) -> None:
        self._contact_repo = contact_repo
        self._settings_repo = settings_repo

    async def search(self, query: str, *, limit: int = 20) -> list[Contact]:
        results = await self._contact_repo.search_fulltext(query, limit=limit)
        logger.info("Full-text search {!r} -> {} result(s)", query, len(results))
        return results

    async def find_duplicates(self, *, threshold: float | None = None) -> list[DuplicateCandidate]:
        """Pairwise-compare every active contact (name via rapidfuzz, exact
        phone/email) and return candidates scoring at or above `threshold`,
        highest score first. O(n^2) comparisons — fine at personal-CRM scale
        (hundreds, not millions, of contacts)."""
        if threshold is None:
            settings = await self._settings_repo.get()
            threshold = settings.dedup_score_threshold
            logger.debug("Using configured dedup threshold: {}", threshold)
        else:
            logger.debug("Using override dedup threshold: {}", threshold)

        contacts = await self._contact_repo.list_contacts()
        candidates = [
            candidate
            for a, b in combinations(contacts, 2)
            if (candidate := _pair_candidate(a, b)) is not None and candidate.score >= threshold
        ]
        candidates.sort(key=lambda c: c.score, reverse=True)
        logger.info(
            "Found {} duplicate candidate pair(s) among {} contact(s) (threshold {})",
            len(candidates),
            len(contacts),
            threshold,
        )
        return candidates
