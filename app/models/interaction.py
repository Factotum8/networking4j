"""The `(:Interaction)` node, reached via `(:Contact)-[:HAD_INTERACTION]->`.

Modeled as its own node (per networking-app-ai-prompt.md) rather than a list
property on Contact, so "when did we last see this person" can be answered
with a simple aggregation.
"""

from __future__ import annotations

from datetime import date as date_

from app.models.base import GraphNode
from app.models.enums import InteractionType


class Interaction(GraphNode):
    type: InteractionType
    date: date_
    comment: str | None = None
