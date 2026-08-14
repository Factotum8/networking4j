"""Business logic for the stage-7 graph screen — thin logging wrapper
around `GraphRepository`, same pattern as every other handler."""

from __future__ import annotations

from loguru import logger

from app.models.enums import Circle, ContactType, DimensionLinkType
from app.models.graph import GraphSnapshot
from app.repositories.graph_repository import GraphRepository


class GraphHandler:
    def __init__(self, repo: GraphRepository) -> None:
        self._repo = repo

    async def snapshot(
        self,
        *,
        limit: int,
        circles: list[Circle] | None = None,
        contact_types: list[ContactType] | None = None,
        dimension_filter: tuple[DimensionLinkType, str] | None = None,
    ) -> GraphSnapshot:
        result = await self._repo.snapshot(
            limit=limit,
            circles=circles,
            contact_types=contact_types,
            dimension_filter=dimension_filter,
        )
        logger.debug(
            "Graph snapshot: {} node(s), {} edge(s) ({} of {} contact(s) matched)",
            len(result.nodes),
            len(result.edges),
            sum(1 for n in result.nodes if n.label == "Contact"),
            result.total_contacts,
        )
        return result

    async def neighbors(self, contact_id: str) -> GraphSnapshot:
        result = await self._repo.neighbors(contact_id)
        logger.debug(
            "Expanded contact {}: {} node(s), {} edge(s)",
            contact_id,
            len(result.nodes),
            len(result.edges),
        )
        return result

    async def shortest_path(self, from_id: str, to_id: str) -> GraphSnapshot | None:
        result = await self._repo.shortest_path(from_id, to_id)
        if result is None:
            logger.debug("No KNOWS path found between {} and {}", from_id, to_id)
        else:
            logger.debug("Path {} -> {}: {} hop(s)", from_id, to_id, len(result.nodes) - 1)
        return result
