"""Cypher repositories for the two goal objects (item 4): a standalone
`(:NetworkingGoal)` singleton and a `(:MonthlyGoal)` history, one node per
month.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from app.models.goal import MonthlyGoal, NetworkingGoal
from app.repositories.base import Repository


def _hydrate[T: BaseModel](model: type[T], record: Mapping[str, Any] | None) -> T | None:
    if record is None:
        return None
    return model.model_validate({**record["props"], "id": record["id"]})


class NetworkingGoalRepository(Repository):
    async def get(self) -> NetworkingGoal | None:
        query = "MATCH (g:NetworkingGoal) RETURN elementId(g) AS id, g {.*} AS props LIMIT 1"
        record = await self._run_one(query)
        return _hydrate(NetworkingGoal, record)

    async def set_text(self, text: str) -> NetworkingGoal:
        """Single-user app: read-then-write is an acceptable simplification
        here (no concurrent writers), so no transactional MERGE is needed."""
        now = datetime.now(UTC)
        existing = await self.get()
        if existing is None:
            query = (
                "CREATE (g:NetworkingGoal) SET g = $props "
                "RETURN elementId(g) AS id, g {.*} AS props"
            )
            record = await self._run_one(query, props={"text": text, "updated_at": now})
        else:
            query = (
                "MATCH (g:NetworkingGoal) WHERE elementId(g) = $id "
                "SET g += $props RETURN elementId(g) AS id, g {.*} AS props"
            )
            record = await self._run_one(
                query, id=existing.id, props={"text": text, "updated_at": now}
            )
        result = _hydrate(NetworkingGoal, record)
        assert result is not None
        return result


class MonthlyGoalRepository(Repository):
    async def get_by_month(self, month: str) -> MonthlyGoal | None:
        query = "MATCH (m:MonthlyGoal {month: $month}) RETURN elementId(m) AS id, m {.*} AS props"
        record = await self._run_one(query, month=month)
        return _hydrate(MonthlyGoal, record)

    async def upsert(self, month: str, text: str) -> MonthlyGoal:
        now = datetime.now(UTC)
        query = """
        MERGE (m:MonthlyGoal {month: $month})
        ON CREATE SET m.created_at = $now
        SET m.text = $text, m.updated_at = $now
        RETURN elementId(m) AS id, m {.*} AS props
        """
        record = await self._run_one(query, month=month, text=text, now=now)
        result = _hydrate(MonthlyGoal, record)
        assert result is not None
        return result

    async def list_history(self) -> list[MonthlyGoal]:
        query = (
            "MATCH (m:MonthlyGoal) RETURN elementId(m) AS id, m {.*} AS props ORDER BY m.month DESC"
        )
        records = await self._run(query)
        return [MonthlyGoal.model_validate({**r["props"], "id": r["id"]}) for r in records]
