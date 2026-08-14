"""Generic repository for the six "dimension" node types that are just a
`name` (Company, Event, Community, Project, Interest, Tag) — see
app.models.dimensions. One implementation, parameterized by label + model
class (PEP 695 generics), instead of six near-identical repositories.
"""

from __future__ import annotations

from neo4j import AsyncDriver

from app.models.base import GraphNode
from app.repositories.base import Repository


class NamedNodeRepository[T: GraphNode](Repository):
    def __init__(self, driver: AsyncDriver, label: str, model: type[T]) -> None:
        super().__init__(driver)
        self._label = label
        self._model = model

    async def list_all(self) -> list[T]:
        query = (
            f"MATCH (n:{self._label}) RETURN elementId(n) AS id, n {{.*}} AS props ORDER BY n.name"
        )
        records = await self._run(query)
        return [self._model.model_validate({**r["props"], "id": r["id"]}) for r in records]

    async def get_by_name(self, name: str) -> T | None:
        query = (
            f"MATCH (n:{self._label} {{name: $name}}) RETURN elementId(n) AS id, n {{.*}} AS props"
        )
        record = await self._run_one(query, name=name)
        if record is None:
            return None
        return self._model.model_validate({**record["props"], "id": record["id"]})

    async def get_or_create(self, name: str) -> T:
        """MERGE by name — dimension nodes are deduplicated (see the unique
        constraints in app.db.ensure_schema), so linking a contact to
        "Acme Inc" twice reuses the same Company node."""
        query = (
            f"MERGE (n:{self._label} {{name: $name}}) RETURN elementId(n) AS id, n {{.*}} AS props"
        )
        record = await self._run_one(query, name=name)
        assert record is not None  # MERGE always returns exactly one row
        return self._model.model_validate({**record["props"], "id": record["id"]})
