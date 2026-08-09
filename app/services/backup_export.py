"""Standalone backup-export script — stage 4.

Run via ``python -m app.services.backup_export`` (the Makefile's ``backup``
target calls this right after the binary ``neo4j-admin database dump``).
Produces a portable, human-readable copy alongside that binary dump:

- one JSON file with the *entire* graph — every node type and every
  relationship, walked via the existing repositories — for a full,
  human-readable point-in-time snapshot.
- one CSV with just the contacts, the spreadsheet-friendly subset a human
  is actually most likely to want to open.

Export only, deliberately: restoring a wiped database is what the binary
neo4j-admin dump is for. This JSON isn't designed to be loaded back through
the app (elementIds aren't stable across a reload anyway) — if a JSON-based
restore is ever needed, that's a separate, explicit ask.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from pathlib import Path

from loguru import logger
from neo4j import AsyncDriver

from app.db import create_driver
from app.logging_config import configure_logging
from app.models.backup import (
    ActionRecord,
    DimensionLinkRecord,
    GraphBackup,
    InteractionRecord,
    KnowsRecord,
    RelativeRecord,
)
from app.models.dimensions import Community, Company, Event, Interest, Project, Tag
from app.repositories.contact_repository import ContactRepository
from app.repositories.goal_repository import MonthlyGoalRepository, NetworkingGoalRepository
from app.repositories.link_repository import LinkRepository
from app.repositories.named_node_repository import NamedNodeRepository
from app.repositories.settings_repository import SettingsRepository
from app.services.contact_io import contacts_to_csv

BACKUPS_DIR = Path("backups")


async def build_backup(driver: AsyncDriver) -> GraphBackup:
    """Walk every repository and assemble one full-graph snapshot."""
    contact_repo = ContactRepository(driver)
    link_repo = LinkRepository(driver)
    settings_repo = SettingsRepository(driver)
    goal_repo = NetworkingGoalRepository(driver)
    monthly_goal_repo = MonthlyGoalRepository(driver)

    active_contacts = await contact_repo.list_contacts(archived=False)
    archived_contacts = await contact_repo.list_contacts(archived=True)
    contacts = active_contacts + archived_contacts
    logger.info(
        "Backup: {} contact(s) ({} active, {} archived)",
        len(contacts),
        len(active_contacts),
        len(archived_contacts),
    )

    interactions = [
        InteractionRecord(contact_id=r["contact_id"], interaction=r["interaction"])
        for r in await link_repo.list_all_interactions()
    ]
    # Reuses list_due_actions with a maximal date + include_completed=True to
    # get "every action ever", rather than adding a near-duplicate query.
    due_actions = await link_repo.list_due_actions(before=date.max, include_completed=True)
    actions = [
        ActionRecord(contact_id=r["contact_id"], contact_name=r["contact_name"], action=r["action"])
        for r in due_actions
    ]
    relatives = [
        RelativeRecord(contact_id=r["contact_id"], relative=r["relative"])
        for r in await link_repo.list_all_relatives()
    ]
    knows = [
        KnowsRecord(from_id=r["from_id"], to_id=r["to_id"], knows=r["knows"])
        for r in await link_repo.list_all_knows()
    ]
    dimension_links = [
        DimensionLinkRecord.model_validate(r) for r in await link_repo.list_all_dimension_links()
    ]
    logger.info(
        "Backup: {} interaction(s), {} action(s), {} relative(s), "
        "{} KNOWS edge(s), {} dimension link(s)",
        len(interactions),
        len(actions),
        len(relatives),
        len(knows),
        len(dimension_links),
    )

    companies = await NamedNodeRepository(driver, "Company", Company).list_all()
    events = await NamedNodeRepository(driver, "Event", Event).list_all()
    communities = await NamedNodeRepository(driver, "Community", Community).list_all()
    projects = await NamedNodeRepository(driver, "Project", Project).list_all()
    interests = await NamedNodeRepository(driver, "Interest", Interest).list_all()
    tags = await NamedNodeRepository(driver, "Tag", Tag).list_all()

    networking_goal = await goal_repo.get()
    monthly_goals = await monthly_goal_repo.list_history()
    settings = await settings_repo.get()

    return GraphBackup(
        exported_at=datetime.now(UTC),
        contacts=contacts,
        interactions=interactions,
        actions=actions,
        relatives=relatives,
        knows=knows,
        dimension_links=dimension_links,
        companies=companies,
        events=events,
        communities=communities,
        projects=projects,
        interests=interests,
        tags=tags,
        networking_goal=networking_goal,
        monthly_goals=monthly_goals,
        settings=settings,
    )


async def main() -> None:
    configure_logging()
    BACKUPS_DIR.mkdir(exist_ok=True)
    driver = create_driver()
    try:
        backup = await build_backup(driver)
    finally:
        await driver.close()

    timestamp = backup.exported_at.strftime("%Y%m%dT%H%M%SZ")
    json_path = BACKUPS_DIR / f"backup_{timestamp}.json"
    csv_path = BACKUPS_DIR / f"contacts_{timestamp}.csv"

    json_path.write_text(backup.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Wrote full-graph JSON backup to {}", json_path)

    csv_path.write_bytes(contacts_to_csv(backup.contacts))
    logger.info("Wrote contacts CSV backup to {}", csv_path)


if __name__ == "__main__":
    asyncio.run(main())
