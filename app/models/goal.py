"""Networking goals (item 4): two separate objects, standalone in the graph
(not linked to any Contact) since the app is single-user.
"""

from __future__ import annotations

from datetime import datetime

from app.models.base import GraphNode


class NetworkingGoal(GraphNode):
    """A single, standalone `(:NetworkingGoal)` node — free text, edited in
    place, not tied to a month. Exactly one is expected to exist."""

    text: str
    updated_at: datetime | None = None


class MonthlyGoal(GraphNode):
    """One `(:MonthlyGoal)` node per month, forming the history described
    in item 4 (free text, browsable by past period)."""

    text: str
    month: str  # "YYYY-MM" — simple, sortable, unambiguous
    created_at: datetime | None = None
    updated_at: datetime | None = None
