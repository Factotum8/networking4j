"""View-model shapes for the stage-7 graph screen — deliberately separate
from `app.models.base.GraphNode` (the DB-node base every model in this app
extends): these describe a node/edge as ECharts needs them to draw the
canvas, not as Neo4j stores them. Every node type that can appear
(Contact plus all six dimension types) collapses into one flat shape here.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import Circle, ContactType


class GraphVisNode(BaseModel):
    id: str
    label: str
    """The Neo4j node label: "Contact", "Company", "Tag", etc."""

    name: str
    circle: Circle | None = None
    contact_type: ContactType | None = None


class GraphVisEdge(BaseModel):
    id: str
    source: str
    target: str
    rel_type: str
    edge_label: str | None = None
    """Short text to show on the edge itself — e.g. a KNOWS closeness
    score. `None` for property-less dimension links."""


class GraphSnapshot(BaseModel):
    nodes: list[GraphVisNode]
    edges: list[GraphVisEdge]
    total_contacts: int
    """How many active contacts matched the filters, before `limit` was
    applied — lets the UI show "showing N of total_contacts" rather than
    silently truncating."""

    @property
    def truncated(self) -> bool:
        contact_count = sum(1 for n in self.nodes if n.label == "Contact")
        return contact_count < self.total_contacts
