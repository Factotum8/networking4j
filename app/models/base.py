"""Shared base for Pydantic models that map onto Neo4j nodes.

``id`` holds the Neo4j ``elementId`` — ``None`` until the node has been
persisted (repositories fill it in on read/create).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class GraphNode(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
