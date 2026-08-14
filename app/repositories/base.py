"""Shared repository plumbing.

Every repository takes an `AsyncDriver` (never a raw session) and opens its
own session per call — matches the pattern already used in `app.db`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from neo4j import AsyncDriver
from neo4j.time import Date, DateTime, Time


def _to_native(value: Any) -> Any:
    """Recursively convert the driver's temporal wrapper types to their
    stdlib equivalents.

    The Neo4j driver never returns plain `datetime.date`/`datetime.datetime`
    for a temporal property — it returns its own `neo4j.time.*` types
    (they're higher-precision than Python's), and `record.data()` leaves
    them as-is nested inside dicts/lists. Every `GraphNode.model_validate`
    call in the repositories feeds a Cypher record straight into a Pydantic
    model typed with plain `date`/`datetime`, and Pydantic's validator
    rejects the driver's wrapper types outright — confirmed against a live
    container, not just in theory. Converting once here, at the single
    choke point every repository read goes through, beats adding the same
    `.to_native()` call to every `_to_*`/`_hydrate` helper.
    """
    match value:
        case dict():
            return {k: _to_native(v) for k, v in value.items()}
        case list():
            return [_to_native(v) for v in value]
        case Date() | DateTime() | Time():
            return value.to_native()
        case _:
            return value


class Repository:
    """Base class for all Cypher repositories: just holds the driver."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def _run(self, query: str, **params: Any) -> list[Mapping[str, Any]]:
        async with self._driver.session() as session:
            result = await session.run(query, params)
            return [_to_native(record.data()) async for record in result]

    async def _run_one(self, query: str, **params: Any) -> Mapping[str, Any] | None:
        records = await self._run(query, **params)
        return records[0] if records else None

    async def _run_summary(self, query: str, **params: Any) -> Any:
        """For write-only queries with no RETURN — gives access to
        ``ResultSummary.counters`` (e.g. ``nodes_deleted``)."""
        async with self._driver.session() as session:
            result = await session.run(query, params)
            return await result.consume()
