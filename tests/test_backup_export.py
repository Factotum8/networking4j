"""Integration test: `app.services.backup_export.build_backup` walks a real
Neo4j and assembles a full-graph snapshot. Requires Docker, skipped the same
way test_db_schema.py is."""

from __future__ import annotations

from datetime import date

import pytest
from neo4j import AsyncGraphDatabase

from app.db import ensure_schema
from app.models.contact import Contact
from app.models.enums import InteractionType
from app.models.interaction import Interaction
from app.repositories.contact_repository import ContactRepository
from app.repositories.link_repository import LinkRepository
from app.services.backup_export import build_backup
from app.services.contact_io import contacts_to_csv

try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:  # pragma: no cover
    Neo4jContainer = None  # type: ignore[assignment,misc]


@pytest.mark.asyncio
async def test_build_backup_captures_contacts_and_relationships() -> None:
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

            a = await contact_repo.create(Contact(name="Ada Lovelace"))
            b = await contact_repo.create(Contact(name="Grace Hopper"))
            assert a.id is not None
            assert b.id is not None
            await contact_repo.archive(b.id)
            await link_repo.add_interaction(
                a.id, Interaction(type=InteractionType.MEETING, date=date(2024, 1, 1))
            )

            backup = await build_backup(driver)

            assert {c.name for c in backup.contacts} == {"Ada Lovelace", "Grace Hopper"}
            assert len(backup.interactions) == 1
            assert backup.interactions[0].contact_id == a.id
            assert backup.interactions[0].interaction.type == InteractionType.MEETING

            # The JSON side has to actually serialize without error (dates,
            # enums, nested models — the whole point of routing everything
            # through one Pydantic model).
            json_text = backup.model_dump_json()
            assert "Ada Lovelace" in json_text

            # And the CSV side, reusing the same contacts_to_csv as export.
            csv_bytes = contacts_to_csv(backup.contacts)
            assert b"Ada Lovelace" in csv_bytes
        finally:
            await driver.close()
    finally:
        container.stop()
