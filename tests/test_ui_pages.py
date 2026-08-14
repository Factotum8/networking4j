"""Integration test: NiceGUI pages (stages 6-7) against a real Neo4j.

`@ui.page` functions run server-side on the very first GET — the response
already embeds the fully-built element tree (confirmed by hand: curling a
page mid-development, before websocket even connects, showed real contact
names baked into the HTML) — so a plain HTTP GET through the real app
lifespan exercises the actual handler/DB calls each page makes, not just
routing. The interactive parts (buttons, dialogs, uploads, graph
filters/clicks/shortest-path) were verified by hand against the live
docker-compose stack for every page in both stages (stage 6: dashboard,
contacts list/detail/CRUD, settings, duplicates, import/export; stage 7:
the graph screen) — this test is the automated regression net for "does
the page still build without blowing up and does it still show real
data", not a replacement for that manual pass.

Requires Docker; skipped the same way test_db_schema.py is when it isn't
available.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from neo4j import AsyncGraphDatabase

from app.db import ensure_schema
from app.models.contact import Contact
from app.models.enums import Circle
from app.repositories.contact_repository import ContactRepository

try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:  # pragma: no cover
    Neo4jContainer = None  # type: ignore[assignment,misc]


@pytest.mark.asyncio
async def test_ui_pages_render_against_real_neo4j(monkeypatch: pytest.MonkeyPatch) -> None:
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
            seeded = await ContactRepository(driver).create(
                Contact(name="UI Smoke Test Contact", circle=Circle.SUPPORT_CIRCLE)
            )
            assert seeded.id is not None

            import app.main as main_module

            # main.py's lifespan calls create_driver() itself; point that at
            # our container instead of whatever .env configures, so the
            # already-mounted app (imported once, cached by pytest) talks to
            # the same Neo4j this test seeded.
            monkeypatch.setattr(main_module, "create_driver", lambda: driver)

            transport = ASGITransport(app=main_module.app)
            lifespan = main_module.app.router.lifespan_context(main_module.app)
            async with lifespan, AsyncClient(transport=transport, base_url="http://test") as client:
                for path in (
                    "/",
                    "/app/contacts",
                    "/app/duplicates",
                    "/app/import-export",
                    "/app/settings",
                    "/app/graph",
                ):
                    response = await client.get(path)
                    assert response.status_code == 200, path

                detail_response = await client.get(f"/app/contacts/{seeded.id}")
                assert detail_response.status_code == 200
                assert "UI Smoke Test Contact" in detail_response.text

                graph_response = await client.get("/app/graph")
                assert "UI Smoke Test Contact" in graph_response.text
        finally:
            await driver.close()
    finally:
        container.stop()
