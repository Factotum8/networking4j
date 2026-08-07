"""Relationship (edge) property models — these map onto Neo4j relationships,
not nodes, so they don't extend `GraphNode`.
"""

from __future__ import annotations

from datetime import date as date_

from pydantic import BaseModel, ConfigDict


class Knows(BaseModel):
    """`(:Contact)-[:KNOWS {type, date, comment, closeness}]->(:Contact)`.

    `type` and `closeness` aren't given a fixed value set/scale anywhere in
    the spec (unlike the Contact criteria, which are explicitly 1-10) — kept
    as free-form rather than inventing bounds.

    The `date` field is typed via the `date_` alias, not `date` directly —
    naming a field the same as its own type breaks Python 3.14's lazy
    annotation evaluation (PEP 649): resolving the forward ref for `date`
    finds the field's own class-level default under that name before it
    finds the `datetime.date` import, and `None | None` blows up. Same
    reasoning already applied in app.models.interaction/action.
    """

    model_config = ConfigDict(populate_by_name=True)

    type: str | None = None
    date: date_ | None = None
    comment: str | None = None
    closeness: int | None = None
