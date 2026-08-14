"""Integration test: `ReminderHandler.build_digest` against a real Neo4j —
exercises the actual Cypher in `ContactRepository.list_stale` /
`LinkRepository.list_due_actions`/`upcoming_birthdays` together, the same
combination the stage-5 scheduled job and `/reminders/digest` endpoint rely
on. The pure assembly logic (fake repos) is covered in
test_reminder_handler.py; this is the thing that pure unit tests can't catch
— e.g. the temporal-type bug from stage 2 that only a live container caught.
Requires Docker; skipped the same way test_db_schema.py is when unavailable.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from neo4j import AsyncGraphDatabase

from app.db import ensure_schema
from app.handlers.reminder_handler import ReminderHandler
from app.models.action import Action
from app.models.contact import Contact
from app.models.enums import ActionType
from app.repositories.contact_repository import ContactRepository
from app.repositories.link_repository import LinkRepository
from app.repositories.settings_repository import SettingsRepository

try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:  # pragma: no cover
    Neo4jContainer = None  # type: ignore[assignment,misc]


@pytest.mark.asyncio
async def test_reminder_digest_against_real_neo4j() -> None:
    if Neo4jContainer is None:
        pytest.skip("testcontainers[neo4j] not installed")

    try:
        container = Neo4jContainer("neo4j:5-community")
        container.start()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Docker/Neo4j container unavailable: {exc}")

    try:
        driver = AsyncGraphDatabase.driver(
            container.get_connection_url(),
            auth=(container.username, container.password),
        )
        try:
            await ensure_schema(driver)
            contact_repo = ContactRepository(driver)
            link_repo = LinkRepository(driver)
            settings_repo = SettingsRepository(driver)
            handler = ReminderHandler(contact_repo, link_repo, settings_repo)

            # A contact with an overdue action.
            overdue_contact = await contact_repo.create(Contact(name="Ada Lovelace"))
            assert overdue_contact.id is not None
            await link_repo.add_action(
                overdue_contact.id,
                Action(type=ActionType.CALL, due_date=date.today() - timedelta(days=1)),
            )

            # A contact nobody has ever talked to — stale by definition.
            await contact_repo.create(Contact(name="Alan Turing"))

            # A contact whose birthday is coming up in the default 30-day window.
            soon = date.today() + timedelta(days=5)
            await contact_repo.create(
                Contact(name="Grace Hopper", birthday=date(2000, soon.month, soon.day))
            )

            digest = await handler.build_digest()

            assert {d.contact_name for d in digest.due_actions} == {"Ada Lovelace"}
            assert {s.contact.name for s in digest.stale_contacts} == {
                "Ada Lovelace",
                "Alan Turing",
                "Grace Hopper",
            }
            assert {b.name for b in digest.upcoming_birthdays} == {"Grace Hopper"}
        finally:
            await driver.close()
    finally:
        container.stop()
