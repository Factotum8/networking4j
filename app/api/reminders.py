"""`/reminders` — stage 5: on-demand access to the same digest the
scheduled job (`app.services.scheduler`) logs daily.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_reminder_handler
from app.handlers.reminder_handler import ReminderHandler
from app.models.reminder import ReminderDigest

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("/digest", response_model=ReminderDigest)
async def get_digest(
    birthday_within_days: int = Query(default=30, ge=1),
    handler: ReminderHandler = Depends(get_reminder_handler),
) -> ReminderDigest:
    return await handler.build_digest(birthday_within_days=birthday_within_days)
