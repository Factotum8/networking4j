"""The `(:Contact)` node — the central entity of the graph model."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.base import GraphNode
from app.models.enums import Circle, ContactType


class Contact(GraphNode):
    name: str

    # Single avatar photo (item 6: one photo per contact, not a gallery).
    # Stored as a path/URL string; the storage backend is a stage-2 detail,
    # not a spec decision.
    photo: str | None = None

    phone: str | None = None
    email: str | None = None
    position: str | None = None
    city: str | None = None

    # Item 5 (CLI scenarios): "a contact's birthday and the birthdays of
    # their relatives" implies the contact itself needs a birthday too, not
    # just app.models.relative.Relative.
    birthday: date | None = None

    # Doubles as the "important facts about a contact" field (item 5,
    # resolved: same thing as notes — no separate structured entity).
    notes: str | None = None

    met_place: str | None = None
    met_date: date | None = None

    contact_type: ContactType | None = None
    circle: Circle | None = None

    # Item 3: three numeric criteria, 1-10, not tags.
    dangerous: int | None = Field(default=None, ge=1, le=10)
    interesting: int | None = Field(default=None, ge=1, le=10)
    difficult: int | None = Field(default=None, ge=1, le=10)

    # Soft delete/archive (spec: deletion only after confirmation; archiving
    # as a separate, reversible operation).
    archived: bool = False
    archived_at: datetime | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None


class ContactUpdate(BaseModel):
    """PATCH payload — every field optional, only the ones supplied are
    changed. Excludes `id`/`created_at`/`archived*` (archiving has its own
    dedicated, confirmation-aware endpoints)."""

    name: str | None = None
    photo: str | None = None
    phone: str | None = None
    email: str | None = None
    position: str | None = None
    city: str | None = None
    birthday: date | None = None
    notes: str | None = None
    met_place: str | None = None
    met_date: date | None = None
    contact_type: ContactType | None = None
    circle: Circle | None = None
    dangerous: int | None = Field(default=None, ge=1, le=10)
    interesting: int | None = Field(default=None, ge=1, le=10)
    difficult: int | None = Field(default=None, ge=1, le=10)
