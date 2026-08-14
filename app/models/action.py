"""The `(:Action)` node, reached via `(:Contact)-[:NEXT_ACTION]->`.

`completed`/`completed_at` aren't in the spec's property list ({type,
due_date}) but are added here as a necessary implementation detail: stage 5
(reminders/APScheduler) needs some way to tell a done action apart from a
due one when querying "upcoming reminders" — this isn't a spec ambiguity,
just plumbing required to build the described reminder behavior at all.
"""

from __future__ import annotations

from datetime import date as date_
from datetime import datetime

from app.models.base import GraphNode
from app.models.enums import ActionType


class Action(GraphNode):
    type: ActionType
    due_date: date_
    completed: bool = False
    completed_at: datetime | None = None
