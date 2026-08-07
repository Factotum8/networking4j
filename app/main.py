"""FastAPI application entry point.

Lifespan wiring (Neo4j driver + schema bootstrap + 1Password secret load)
plus every domain router built so far (stage 2: contacts, dimension nodes,
links/relationships, goals, settings).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api import contacts, goals
from app.api import settings as settings_api
from app.api.dimensions import all_dimension_routers
from app.api.links import actions_router, contact_links_router, misc_router
from app.config import settings
from app.db import create_driver, ensure_schema
from app.logging_config import configure_logging
from app.services.secrets import load_llm_api_keys


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("Starting networking4j on {}:{}", settings.app_host, settings.app_port)

    driver = create_driver()
    await ensure_schema(driver)
    app.state.neo4j_driver = driver

    app.state.llm_api_keys = await load_llm_api_keys()

    try:
        yield
    finally:
        await driver.close()
        logger.info("Neo4j driver closed, shutting down")


app = FastAPI(title="networking4j", version="0.1.0", lifespan=lifespan)

app.include_router(contacts.router)
app.include_router(contact_links_router)
app.include_router(actions_router)
app.include_router(goals.router)
app.include_router(settings_api.router)
app.include_router(misc_router)
for dimension_router in all_dimension_routers:
    app.include_router(dimension_router)


@app.get("/health")
async def health() -> dict[str, str]:
    logger.debug("Health check requested")
    return {"status": "ok"}
