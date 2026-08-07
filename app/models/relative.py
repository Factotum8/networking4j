"""The `(:Relative)` node, reached via `(:Contact)-[:HAS_RELATIVE]->`.

Resolved in item 5 of networking-app-ai-prompt.md: a separate node linked to
Contact, not properties on the contact itself — needed so the CLI can
aggregate "whose birthday is this week" across relatives too.
"""

from __future__ import annotations

from datetime import date

from app.models.base import GraphNode


class Relative(GraphNode):
    name: str

    # Not enumerated in the spec (e.g. "mother", "spouse", "child") — kept
    # as free text rather than inventing a fixed set of relation kinds.
    relation_type: str | None = None

    birthday: date | None = None
