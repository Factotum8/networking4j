"""Reminder digest — stage 5.

The spec (`networking-app-ai-prompt.md` #117-118) only says the periodic job
polls due `Action`s/stale contacts via Cypher, "without Celery/Redis" — it
doesn't say what happens with the results afterwards. Resolved with the
user: a structured log line (loguru) plus this digest, exposed both to the
scheduled job and to an on-demand `GET /reminders/digest` endpoint so the
dashboard (stage 6) can pull the same data without waiting for the next
scheduled run. No email/push — neither is in the stack or the spec.

Each entry model's fields mirror the shape its source repository method
already returns (`ContactRepository.list_stale`, `LinkRepository.
list_due_actions`/`upcoming_birthdays`) so `model_validate` can be used
directly on those rows without any reshaping in the handler.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.models.action import Action
from app.models.contact import Contact


class DueActionEntry(BaseModel):
    contact_id: str
    contact_name: str
    action: Action


class StaleContactEntry(BaseModel):
    contact: Contact
    last_interaction_date: date | None


class UpcomingBirthdayEntry(BaseModel):
    name: str
    kind: str  # "contact" or "relative"
    birthday: date
    contact_id: str
    relative_id: str | None
    days_away: int


class ReminderDigest(BaseModel):
    generated_at: datetime
    due_actions: list[DueActionEntry]
    stale_contacts: list[StaleContactEntry]
    upcoming_birthdays: list[UpcomingBirthdayEntry]
