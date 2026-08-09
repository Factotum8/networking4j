"""Integration test: `ContactRepository` round-trips against a real Neo4j.

Requires Docker; skipped the same way test_db_schema.py is when it isn't
available. This is the regression test for a real bug caught only by running
against a live container: the Neo4j driver returns its own `neo4j.time.Date`/
`DateTime` wrapper types for temporal properties, not stdlib `date`/
`datetime` — and Pydantic's `date`/`datetime` validators reject those wrapper
types outright. See `app.repositories.base._to_native`, the fix.
"""

from __future__ import annotations

from datetime import date

import pytest
from neo4j import AsyncGraphDatabase

from app.db import ensure_schema
from app.models.contact import Contact
from app.models.enums import Circle, ContactType
from app.repositories.contact_repository import ContactRepository

try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:  # pragma: no cover
    Neo4jContainer = None  # type: ignore[assignment,misc]


@pytest.mark.asyncio
async def test_contact_repository_round_trip_against_real_neo4j() -> None:
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
            repo = ContactRepository(driver)

            created = await repo.create(
                Contact(
                    name="Ada Lovelace",
                    birthday=date(1815, 12, 10),
                    circle=Circle.SUPPORT_CIRCLE,
                    contact_type=ContactType.CONNECTOR,
                )
            )
            # The bug this guards against: date/datetime fields coming back
            # from Neo4j as its own wrapper types, not stdlib ones — assert
            # the concrete type, not just equality, so a regression that
            # reintroduces a `neo4j.time.Date` here still fails loudly even
            # if some future stdlib/pydantic version stops rejecting it.
            assert type(created.birthday) is date
            assert created.birthday == date(1815, 12, 10)
            assert created.created_at is not None
            assert created.id is not None

            fetched = await repo.get(created.id)
            assert fetched is not None
            assert type(fetched.birthday) is date
            assert fetched.birthday == date(1815, 12, 10)

            listed = await repo.list_contacts()
            assert any(c.id == created.id for c in listed)

            stale = await repo.list_stale(threshold_days=1)
            assert any(s["contact"].id == created.id for s in stale)

            assert await repo.delete(created.id) is True
        finally:
            await driver.close()
    finally:
        container.stop()
