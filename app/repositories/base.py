"""Shared repository plumbing.

Every repository takes an `AsyncDriver` (never a raw session) and opens its
own session per call — matches the pattern already used in `app.db`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from neo4j import AsyncDriver


class Repository:
    """Base class for all Cypher repositories: just holds the driver."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def _run(self, query: str, **params: Any) -> list[Mapping[str, Any]]:
        async with self._driver.session() as session:
            result = await session.run(query, params)
            return [record.data() async for record in result]

    async def _run_one(self, query: str, **params: Any) -> Mapping[str, Any] | None:
        records = await self._run(query, **params)
        return records[0] if records else None

    async def _run_summary(self, query: str, **params: Any) -> Any:
        """For write-only queries with no RETURN — gives access to
        ``ResultSummary.counters`` (e.g. ``nodes_deleted``)."""
        async with self._driver.session() as session:
            result = await session.run(query, params)
            return await result.consume()
