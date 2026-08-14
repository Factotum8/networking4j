"""Full-graph backup shape — stage 4.

`app.services.backup_export` walks every repository and assembles one of
these; serializing it via `model_dump_json` is the entire JSON backup file.
Export only, deliberately — see that module's docstring for why there's no
matching "load a GraphBackup back into Neo4j" function.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.action import Action
from app.models.contact import Contact
from app.models.dimensions import Community, Company, Event, Interest, Project, Tag
from app.models.goal import MonthlyGoal, NetworkingGoal
from app.models.interaction import Interaction
from app.models.relationships import Knows
from app.models.relative import Relative
from app.models.settings import UserSettings


class InteractionRecord(BaseModel):
    contact_id: str
    interaction: Interaction


class ActionRecord(BaseModel):
    contact_id: str
    contact_name: str
    action: Action


class RelativeRecord(BaseModel):
    contact_id: str
    relative: Relative


class KnowsRecord(BaseModel):
    from_id: str
    to_id: str
    knows: Knows


class DimensionLinkRecord(BaseModel):
    """One property-less Contact -> dimension-node edge (WORKS_AT/ATTENDED/
    MEMBER_OF/INVOLVED_IN/INTERESTED_IN/TAGGED)."""

    contact_id: str
    rel_type: str
    target_label: str
    target_id: str


class GraphBackup(BaseModel):
    exported_at: datetime
    contacts: list[Contact]
    interactions: list[InteractionRecord]
    actions: list[ActionRecord]
    relatives: list[RelativeRecord]
    knows: list[KnowsRecord]
    dimension_links: list[DimensionLinkRecord]
    companies: list[Company]
    events: list[Event]
    communities: list[Community]
    projects: list[Project]
    interests: list[Interest]
    tags: list[Tag]
    networking_goal: NetworkingGoal | None
    monthly_goals: list[MonthlyGoal]
    settings: UserSettings
