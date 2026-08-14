"""APScheduler wiring — stage 5.

Per spec (`networking-app-ai-prompt.md` #117-118): a periodic job polls due
Actions/stale contacts via Cypher, "without Celery/Redis". `AsyncIOScheduler`
runs cooperatively inside the same event loop as FastAPI/uvicorn, so no
extra process or broker is needed.

What the job *does* with what it finds was the one real spec gap here,
resolved with the user: log a structured digest (loguru) — no email/push,
neither is in the stack. `ReminderHandler.build_digest` already does that
logging; this module only decides *when* to call it.
"""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from neo4j import AsyncDriver

from app.config import settings
from app.handlers.reminder_handler import ReminderHandler
from app.repositories.contact_repository import ContactRepository
from app.repositories.link_repository import LinkRepository
from app.repositories.settings_repository import SettingsRepository


async def _run_daily_digest(driver: AsyncDriver) -> None:
    handler = ReminderHandler(
        ContactRepository(driver), LinkRepository(driver), SettingsRepository(driver)
    )
    try:
        await handler.build_digest()
    except Exception:
        # A failed scheduled run shouldn't take the scheduler itself down —
        # log it and let tomorrow's run try again.
        logger.exception("Reminder digest job failed")


def start_scheduler(driver: AsyncDriver) -> AsyncIOScheduler:
    """Called once from the FastAPI lifespan (see `app.main`). The caller
    owns shutdown — `scheduler.shutdown()` on app teardown."""
    scheduler = AsyncIOScheduler()
    trigger = CronTrigger(
        hour=settings.reminder_digest_hour, minute=settings.reminder_digest_minute
    )
    scheduler.add_job(
        _run_daily_digest,
        trigger,
        args=[driver],
        id="reminder_digest",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Reminder digest job scheduled daily at {:02d}:{:02d}",
        settings.reminder_digest_hour,
        settings.reminder_digest_minute,
    )
    return scheduler
