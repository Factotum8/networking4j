"""Integration test: `GraphRepository` (stage 7) against a real Neo4j —
snapshot filtering/limiting, one-contact expansion, and shortestPath.
Requires Docker, skipped the same way test_db_schema.py is.
"""

from __future__ import annotations

import pytest
from neo4j import AsyncGraphDatabase

from app.db import ensure_schema
from app.models.contact import Contact
from app.models.dimensions import Company
from app.models.enums import Circle, ContactType, DimensionLinkType
from app.models.relationships import Knows
from app.repositories.contact_repository import ContactRepository
from app.repositories.graph_repository import GraphRepository
from app.repositories.link_repository import LinkRepository
from app.repositories.named_node_repository import NamedNodeRepository

try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:  # pragma: no cover
    Neo4jContainer = None  # type: ignore[assignment,misc]


@pytest.mark.asyncio
async def test_graph_repository_against_real_neo4j() -> None:
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
            company_repo = NamedNodeRepository(driver, "Company", Company)
            graph_repo = GraphRepository(driver)

            ada = await contact_repo.create(
                Contact(name="Ada Lovelace", circle=Circle.SUPPORT_CIRCLE)
            )
            grace = await contact_repo.create(
                Contact(name="Grace Hopper", circle=Circle.FUNCTIONAL_CIRCLES)
            )
            bob = await contact_repo.create(
                Contact(name="Bob Outsider", contact_type=ContactType.BRIDGE)
            )
            assert ada.id and grace.id and bob.id

            await link_repo.set_knows(ada.id, grace.id, Knows(closeness=8))
            await link_repo.set_knows(grace.id, bob.id, Knows(closeness=5))
            acme = await company_repo.get_or_create("Acme Inc")
            assert acme.id is not None
            await link_repo.attach(ada.id, DimensionLinkType.WORKS_AT, acme.id)

            # --- snapshot: no filters, no cap ---
            full = await graph_repo.snapshot(limit=100)
            assert full.total_contacts == 3
            assert not full.truncated
            contact_names = {n.name for n in full.nodes if n.label == "Contact"}
            assert contact_names == {"Ada Lovelace", "Grace Hopper", "Bob Outsider"}
            assert any(n.label == "Company" and n.name == "Acme Inc" for n in full.nodes)
            assert any(e.rel_type == "KNOWS" for e in full.edges)
            assert any(e.rel_type == "WORKS_AT" for e in full.edges)

            # --- snapshot: capped ---
            capped = await graph_repo.snapshot(limit=1)
            assert capped.total_contacts == 3
            assert capped.truncated
            assert sum(1 for n in capped.nodes if n.label == "Contact") == 1

            # --- snapshot: filtered by circle ---
            support_only = await graph_repo.snapshot(limit=100, circles=[Circle.SUPPORT_CIRCLE])
            assert {n.name for n in support_only.nodes if n.label == "Contact"} == {"Ada Lovelace"}

            # --- snapshot: filtered by dimension (company) ---
            at_acme = await graph_repo.snapshot(
                limit=100, dimension_filter=(DimensionLinkType.WORKS_AT, acme.id)
            )
            assert {n.name for n in at_acme.nodes if n.label == "Contact"} == {"Ada Lovelace"}

            # --- neighbors ---
            grace_neighbors = await graph_repo.neighbors(grace.id)
            neighbor_names = {n.name for n in grace_neighbors.nodes}
            assert neighbor_names == {"Grace Hopper", "Ada Lovelace", "Bob Outsider"}

            # --- shortest_path ---
            path = await graph_repo.shortest_path(ada.id, bob.id)
            assert path is not None
            assert [n.name for n in path.nodes] == ["Ada Lovelace", "Grace Hopper", "Bob Outsider"]
            assert len(path.edges) == 2

            # --- shortest_path: no connection ---
            lonely = await contact_repo.create(Contact(name="Lonely Contact"))
            assert lonely.id is not None
            assert await graph_repo.shortest_path(ada.id, lonely.id) is None
        finally:
            await driver.close()
    finally:
        container.stop()
