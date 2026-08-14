"""Integration test: `ensure_schema` runs cleanly against a real Neo4j.

Requires Docker. Skipped automatically when Docker isn't available (e.g. in
this sandbox) — this is the only place that actually validates the Cypher
constraint/index syntax in app.db, so it must be run before trusting stage 1
in an environment where Docker is available.
"""

from __future__ import annotations

import pytest
from neo4j import AsyncGraphDatabase

from app.db import ensure_schema

try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:  # pragma: no cover
    Neo4jContainer = None  # type: ignore[assignment,misc]


@pytest.mark.asyncio
async def test_ensure_schema_against_real_neo4j() -> None:
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
            # Running twice must stay a no-op (IF NOT EXISTS idempotency).
            await ensure_schema(driver)
        finally:
            await driver.close()
    finally:
        container.stop()
