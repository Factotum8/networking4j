"""Import/export result shapes — stage 4."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.contact import Contact


class ContactImportRow(BaseModel):
    """One successfully-parsed row from a CSV/vCard import, before it hits
    the database — the contact itself plus dimension-node names to link
    (resolved via `NamedNodeRepository.get_or_create` once the contact has
    an id)."""

    contact: Contact
    companies: list[str] = []
    tags: list[str] = []
    interests: list[str] = []


class ImportRowError(BaseModel):
    """A row that failed to parse/validate. `row` is the 1-indexed position
    a human would see if they opened the source file (spreadsheet row
    number, or n-th vCard in the file) — not a 0-indexed list position."""

    row: int
    message: str


class ImportSummary(BaseModel):
    created: int
    errors: list[ImportRowError] = []
