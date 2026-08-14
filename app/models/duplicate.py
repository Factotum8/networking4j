"""Duplicate-candidate result — stage 3 (search & dedup).

Detection only, per the user's explicit stage-3 scope call: this surfaces
scored candidate pairs and *why* they matched. Resolving a pair (normally
archiving the loser) goes through the contact-archiving endpoints that
already exist (`ContactHandler.archive`) — there's no merge/relationship
rewrite here.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.models.contact import Contact


class DuplicateCandidate(BaseModel):
    contact_a: Contact
    contact_b: Contact

    # 0-100, rapidfuzz scale. An exact phone/email match is scored at parity
    # with an exact name match (100) even when the names themselves differ
    # (nicknames, married names, typos) — see app.handlers.search_handler.
    score: float

    # Which signal(s) matched: any of "name", "phone", "email".
    matched_on: list[str]
