"""Integration test: the three stage-6 "what is this contact linked to"
`LinkRepository` methods (`list_actions`, `list_knows`,
`list_dimension_links`) against a real Neo4j — they back the contact detail
page's sections. Requires Docker, skipped the same way test_db_schema.py is.
"""

from __future__ import annotations

from datetime import date

import pytest
from neo4j import AsyncGraphDatabase

from app.db import ensure_schema
from app.models.action import Action
from app.models.contact import Contact
from app.models.dimensions import Company, Tag
from app.models.enums import ActionType, DimensionLinkType
from app.models.relationships import Knows
from app.repositories.contact_repository import ContactRepository
from app.repositories.link_repository import LinkRepository
from app.repositories.named_node_repository import NamedNodeRepository

try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:  # pragma: no cover
    Neo4jContainer = None  # type: ignore[assignment,misc]


@pytest.mark.asyncio
async def test_per_contact_link_views_against_real_neo4j() -> None:
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
            tag_repo = NamedNodeRepository(driver, "Tag", Tag)

            ada = await contact_repo.create(Contact(name="Ada Lovelace"))
            grace = await contact_repo.create(Contact(name="Grace Hopper"))
            assert ada.id is not None and grace.id is not None

            await link_repo.add_action(
                ada.id, Action(type=ActionType.CALL, due_date=date(2026, 1, 1))
            )
            await link_repo.add_action(
                ada.id, Action(type=ActionType.MEET, due_date=date(2026, 2, 1))
            )

            await link_repo.set_knows(
                ada.id, grace.id, Knows(type="colleague", date=date(2020, 1, 1), closeness=8)
            )

            acme = await company_repo.get_or_create("Acme Inc")
            vip = await tag_repo.get_or_create("vip")
            assert acme.id is not None and vip.id is not None
            await link_repo.attach(ada.id, DimensionLinkType.WORKS_AT, acme.id)
            await link_repo.attach(ada.id, DimensionLinkType.TAGGED, vip.id)

            actions = await link_repo.list_actions(ada.id)
            assert {a.type for a in actions} == {ActionType.CALL, ActionType.MEET}

            knows = await link_repo.list_knows(ada.id)
            assert len(knows) == 1
            assert knows[0]["contact"].name == "Grace Hopper"
            assert knows[0]["knows"].closeness == 8

            links = await link_repo.list_dimension_links(ada.id)
            assert {(link["rel_type"], link["target_name"]) for link in links} == {
                (DimensionLinkType.WORKS_AT, "Acme Inc"),
                (DimensionLinkType.TAGGED, "vip"),
            }

            # Grace has none of these — the queries are scoped per-contact,
            # not accidentally global.
            assert await link_repo.list_actions(grace.id) == []
            assert await link_repo.list_dimension_links(grace.id) == []
        finally:
            await driver.close()
    finally:
        container.stop()
