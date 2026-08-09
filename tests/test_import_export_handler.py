"""Integration test: `ImportExportHandler` round-trips CSV/vCard import and
export against a real Neo4j (bulk-create + dimension linking + export back
out). Requires Docker, skipped the same way test_db_schema.py is."""

from __future__ import annotations

import pytest
from neo4j import AsyncGraphDatabase

from app.db import ensure_schema
from app.handlers.import_export_handler import ImportExportHandler
from app.models.dimensions import Company, Interest, Tag
from app.repositories.contact_repository import ContactRepository
from app.repositories.link_repository import LinkRepository
from app.repositories.named_node_repository import NamedNodeRepository

try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:  # pragma: no cover
    Neo4jContainer = None  # type: ignore[assignment,misc]


@pytest.mark.asyncio
async def test_import_export_round_trip_against_real_neo4j() -> None:
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
            handler = ImportExportHandler(
                ContactRepository(driver),
                LinkRepository(driver),
                NamedNodeRepository(driver, "Company", Company),
                NamedNodeRepository(driver, "Tag", Tag),
                NamedNodeRepository(driver, "Interest", Interest),
            )

            csv_bytes = (
                b"name,phone,company,tags\n"
                b"Ada Lovelace,+1-555-0100,Acme Inc,\"vip, mathematician\"\n"
                b",5\n"  # row with no name — should error, not abort the batch
            )
            summary = await handler.import_csv("import.csv", csv_bytes)

            assert summary.created == 1
            assert len(summary.errors) == 1
            assert summary.errors[0].row == 3  # header + valid row + this bad row

            company_repo = NamedNodeRepository(driver, "Company", Company)
            tag_repo = NamedNodeRepository(driver, "Tag", Tag)
            company = await company_repo.get_by_name("Acme Inc")
            assert company is not None
            vip_tag = await tag_repo.get_by_name("vip")
            assert vip_tag is not None

            link_repo = LinkRepository(driver)
            dimension_links = await link_repo.list_all_dimension_links()
            assert any(
                link["rel_type"] == "WORKS_AT" and link["target_id"] == company.id
                for link in dimension_links
            )
            assert any(
                link["rel_type"] == "TAGGED" and link["target_id"] == vip_tag.id
                for link in dimension_links
            )

            exported_csv = await handler.export_csv(include_archived=False)
            assert b"Ada Lovelace" in exported_csv

            vcard_summary = await handler.import_vcard(
                b"BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Alan Turing\r\nEND:VCARD\r\n"
            )
            assert vcard_summary.created == 1

            exported_vcard = await handler.export_vcard(include_archived=False)
            assert b"Alan Turing" in exported_vcard
            assert b"Ada Lovelace" in exported_vcard
        finally:
            await driver.close()
    finally:
        container.stop()
