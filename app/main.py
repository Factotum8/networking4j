"""FastAPI application entry point.

Lifespan wiring (Neo4j driver + schema bootstrap + 1Password secret load +
stage 5's APScheduler reminder job) plus every domain router built so far
(stage 2: contacts, dimension nodes, links/relationships, goals, settings;
stage 3: search & dedup; stage 4: CSV/Excel/vCard import & export; stage 5:
reminders digest; stage 6: NiceGUI dashboard + contact CRUD, mounted onto
this same app — see app/ui/__init__.py).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api import contacts, goals, import_export, reminders, search
from app.api import settings as settings_api
from app.api.dimensions import all_dimension_routers
from app.api.links import actions_router, contact_links_router, misc_router
from app.config import settings
from app.db import create_driver, ensure_schema
from app.logging_config import configure_logging
from app.services.scheduler import start_scheduler
from app.services.secrets import load_llm_api_keys
from app.ui import mount as mount_ui


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("Starting networking4j on {}:{}", settings.app_host, settings.app_port)

    driver = create_driver()
    await ensure_schema(driver)
    app.state.neo4j_driver = driver

    app.state.llm_api_keys = await load_llm_api_keys()

    scheduler = start_scheduler(driver)

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await driver.close()
        logger.info("Neo4j driver closed, shutting down")


app = FastAPI(title="networking4j", version="0.1.0", lifespan=lifespan)

app.include_router(contacts.router)
app.include_router(contact_links_router)
app.include_router(actions_router)
app.include_router(goals.router)
app.include_router(settings_api.router)
app.include_router(search.router)
app.include_router(import_export.router)
app.include_router(reminders.router)
app.include_router(misc_router)
for dimension_router in all_dimension_routers:
    app.include_router(dimension_router)


@app.get("/health")
async def health() -> dict[str, str]:
    logger.debug("Health check requested")
    return {"status": "ok"}


# Must be the LAST route registration in this module: `ui.run_with` mounts
# NiceGUI as a `Mount("/", ...)` sub-app, and Starlette tries routes in
# registration order — a mount at "/" matches every path, so anything
# registered after it (like /health above) would never be reached. Learned
# by curling /health and getting NiceGUI's 404 page back instead of our own.
mount_ui(app)
