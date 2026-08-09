"""Everything that isn't a plain CRUD-on-one-node-type repository:
property-less links between Contact and a dimension node, the KNOWS
relationship, and the three "Contact grows a child node" relationships
(HAD_INTERACTION, NEXT_ACTION, HAS_RELATIVE).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any

from app.models.action import Action
from app.models.enums import DimensionLinkType
from app.models.interaction import Interaction
from app.models.relationships import Knows
from app.models.relative import Relative
from app.repositories.base import Repository

# Target node label for each DimensionLinkType — the single source of truth
# for relationship type -> target label is the enum itself; this just maps
# it to the label side. Interpolated into Cypher, but only ever from this
# fixed internal mapping, never from raw user input.
_TARGET_LABELS: dict[DimensionLinkType, str] = {
    DimensionLinkType.WORKS_AT: "Company",
    DimensionLinkType.ATTENDED: "Event",
    DimensionLinkType.MEMBER_OF: "Community",
    DimensionLinkType.INVOLVED_IN: "Project",
    DimensionLinkType.INTERESTED_IN: "Interest",
    DimensionLinkType.TAGGED: "Tag",
}


class LinkRepository(Repository):
    # --- Property-less Contact -> dimension-node links ---

    async def attach(self, contact_id: str, rel_type: DimensionLinkType, target_id: str) -> None:
        label = _TARGET_LABELS[rel_type]
        query = (
            f"MATCH (c:Contact) WHERE elementId(c) = $contact_id "
            f"MATCH (t:{label}) WHERE elementId(t) = $target_id "
            f"MERGE (c)-[:{rel_type.value}]->(t)"
        )
        await self._run_summary(query, contact_id=contact_id, target_id=target_id)

    async def detach(self, contact_id: str, rel_type: DimensionLinkType, target_id: str) -> bool:
        label = _TARGET_LABELS[rel_type]
        query = (
            f"MATCH (c:Contact)-[r:{rel_type.value}]->(t:{label}) "
            "WHERE elementId(c) = $contact_id AND elementId(t) = $target_id "
            "DELETE r"
        )
        summary = await self._run_summary(query, contact_id=contact_id, target_id=target_id)
        return bool(summary.counters.relationships_deleted)

    # --- KNOWS (Contact-Contact, with properties) ---

    async def set_knows(self, from_id: str, to_id: str, knows: Knows) -> Knows:
        props = knows.model_dump(exclude_none=True)
        query = (
            "MATCH (a:Contact) WHERE elementId(a) = $from_id "
            "MATCH (b:Contact) WHERE elementId(b) = $to_id "
            "MERGE (a)-[r:KNOWS]->(b) SET r += $props "
            "RETURN r {.*} AS props"
        )
        record = await self._run_one(query, from_id=from_id, to_id=to_id, props=props)
        assert record is not None
        return Knows.model_validate(record["props"])

    async def remove_knows(self, from_id: str, to_id: str) -> bool:
        query = (
            "MATCH (a:Contact)-[r:KNOWS]->(b:Contact) "
            "WHERE elementId(a) = $from_id AND elementId(b) = $to_id "
            "DELETE r"
        )
        summary = await self._run_summary(query, from_id=from_id, to_id=to_id)
        return bool(summary.counters.relationships_deleted)

    # --- HAD_INTERACTION ---

    async def add_interaction(self, contact_id: str, interaction: Interaction) -> Interaction:
        props = interaction.model_dump(exclude={"id"}, exclude_none=True)
        query = (
            "MATCH (c:Contact) WHERE elementId(c) = $contact_id "
            "CREATE (i:Interaction) SET i = $props "
            "CREATE (c)-[:HAD_INTERACTION]->(i) "
            "RETURN elementId(i) AS id, i {.*} AS props"
        )
        record = await self._run_one(query, contact_id=contact_id, props=props)
        assert record is not None
        return Interaction.model_validate({**record["props"], "id": record["id"]})

    async def list_interactions(self, contact_id: str) -> list[Interaction]:
        query = (
            "MATCH (c:Contact)-[:HAD_INTERACTION]->(i:Interaction) "
            "WHERE elementId(c) = $contact_id "
            "RETURN elementId(i) AS id, i {.*} AS props ORDER BY i.date DESC"
        )
        records = await self._run(query, contact_id=contact_id)
        return [Interaction.model_validate({**r["props"], "id": r["id"]}) for r in records]

    async def last_interaction(self, contact_id: str) -> Interaction | None:
        interactions = await self.list_interactions(contact_id)
        return interactions[0] if interactions else None

    # --- NEXT_ACTION ---

    async def add_action(self, contact_id: str, action: Action) -> Action:
        props = action.model_dump(exclude={"id"}, exclude_none=True)
        query = (
            "MATCH (c:Contact) WHERE elementId(c) = $contact_id "
            "CREATE (a:Action) SET a = $props "
            "CREATE (c)-[:NEXT_ACTION]->(a) "
            "RETURN elementId(a) AS id, a {.*} AS props"
        )
        record = await self._run_one(query, contact_id=contact_id, props=props)
        assert record is not None
        return Action.model_validate({**record["props"], "id": record["id"]})

    async def list_due_actions(
        self, *, before: date, include_completed: bool = False
    ) -> list[dict[str, Any]]:
        """Rows of `{contact_id, contact_name, action}` — the shape the
        stage-5 reminders job and the dashboard both need."""
        query = (
            "MATCH (c:Contact)-[:NEXT_ACTION]->(a:Action) "
            "WHERE a.due_date <= $before AND ($include_completed OR a.completed = false) "
            "RETURN elementId(c) AS contact_id, c.name AS contact_name, "
            "elementId(a) AS id, a {.*} AS props ORDER BY a.due_date"
        )
        records = await self._run(query, before=before, include_completed=include_completed)
        return [
            {
                "contact_id": r["contact_id"],
                "contact_name": r["contact_name"],
                "action": Action.model_validate({**r["props"], "id": r["id"]}),
            }
            for r in records
        ]

    async def complete_action(self, action_id: str) -> Action | None:
        query = (
            "MATCH (a:Action) WHERE elementId(a) = $id "
            "SET a.completed = true, a.completed_at = $now "
            "RETURN elementId(a) AS id, a {.*} AS props"
        )
        record = await self._run_one(query, id=action_id, now=datetime.now(UTC))
        return Action.model_validate({**record["props"], "id": record["id"]}) if record else None

    # --- HAS_RELATIVE ---

    async def add_relative(self, contact_id: str, relative: Relative) -> Relative:
        props = relative.model_dump(exclude={"id"}, exclude_none=True)
        query = (
            "MATCH (c:Contact) WHERE elementId(c) = $contact_id "
            "CREATE (r:Relative) SET r = $props "
            "CREATE (c)-[:HAS_RELATIVE]->(r) "
            "RETURN elementId(r) AS id, r {.*} AS props"
        )
        record = await self._run_one(query, contact_id=contact_id, props=props)
        assert record is not None
        return Relative.model_validate({**record["props"], "id": record["id"]})

    async def list_relatives(self, contact_id: str) -> list[Relative]:
        query = (
            "MATCH (c:Contact)-[:HAS_RELATIVE]->(r:Relative) "
            "WHERE elementId(c) = $contact_id "
            "RETURN elementId(r) AS id, r {.*} AS props"
        )
        records = await self._run(query, contact_id=contact_id)
        return [Relative.model_validate({**r["props"], "id": r["id"]}) for r in records]

    # --- Cross-contact "list everything" views (stage 4: full-graph backup) ---

    async def list_all_interactions(self) -> list[dict[str, Any]]:
        query = (
            "MATCH (c:Contact)-[:HAD_INTERACTION]->(i:Interaction) "
            "RETURN elementId(c) AS contact_id, elementId(i) AS id, i {.*} AS props"
        )
        records = await self._run(query)
        return [
            {
                "contact_id": r["contact_id"],
                "interaction": Interaction.model_validate({**r["props"], "id": r["id"]}),
            }
            for r in records
        ]

    async def list_all_relatives(self) -> list[dict[str, Any]]:
        query = (
            "MATCH (c:Contact)-[:HAS_RELATIVE]->(r:Relative) "
            "RETURN elementId(c) AS contact_id, elementId(r) AS id, r {.*} AS props"
        )
        records = await self._run(query)
        return [
            {
                "contact_id": r["contact_id"],
                "relative": Relative.model_validate({**r["props"], "id": r["id"]}),
            }
            for r in records
        ]

    async def list_all_knows(self) -> list[dict[str, Any]]:
        query = (
            "MATCH (a:Contact)-[r:KNOWS]->(b:Contact) "
            "RETURN elementId(a) AS from_id, elementId(b) AS to_id, r {.*} AS props"
        )
        records = await self._run(query)
        return [
            {
                "from_id": r["from_id"],
                "to_id": r["to_id"],
                "knows": Knows.model_validate(r["props"]),
            }
            for r in records
        ]

    async def list_all_dimension_links(self) -> list[Mapping[str, Any]]:
        """Every property-less Contact -> dimension-node edge (WORKS_AT/
        ATTENDED/MEMBER_OF/INVOLVED_IN/INTERESTED_IN/TAGGED), generically —
        one query instead of six near-identical ones."""
        query = (
            "MATCH (c:Contact)-[rel]->(t) WHERE type(rel) IN $rel_types "
            "RETURN elementId(c) AS contact_id, type(rel) AS rel_type, "
            "labels(t)[0] AS target_label, elementId(t) AS target_id"
        )
        rel_types = [rel_type.value for rel_type in DimensionLinkType]
        return await self._run(query, rel_types=rel_types)

    async def upcoming_birthdays(self, *, within_days: int) -> list[Mapping[str, Any]]:
        """Contacts' own birthdays + their relatives', due within N days —
        backs the CLI "birthdays" scenario (item 5). Compares month/day only
        (birth *year* doesn't matter for "is it coming up")."""
        query = """
        CALL () {
            MATCH (c:Contact) WHERE c.birthday IS NOT NULL
            RETURN c.name AS name, 'contact' AS kind, c.birthday AS birthday,
                   elementId(c) AS contact_id, null AS relative_id
            UNION
            MATCH (c:Contact)-[:HAS_RELATIVE]->(r:Relative) WHERE r.birthday IS NOT NULL
            RETURN r.name AS name, 'relative' AS kind, r.birthday AS birthday,
                   elementId(c) AS contact_id, elementId(r) AS relative_id
        }
        WITH name, kind, birthday, contact_id, relative_id,
             date({year: date().year, month: birthday.month, day: birthday.day}) AS this_year,
             date() AS today
        WITH name, kind, birthday, contact_id, relative_id, today, this_year,
             CASE
                 WHEN this_year < today
                 THEN date({year: today.year + 1, month: birthday.month, day: birthday.day})
                 ELSE this_year
             END AS next_occurrence
        WITH name, kind, birthday, contact_id, relative_id, today, next_occurrence,
             duration.between(today, next_occurrence).days AS days_away
        WHERE days_away <= $within_days
        RETURN name, kind, birthday, contact_id, relative_id, days_away
        ORDER BY days_away
        """
        return await self._run(query, within_days=within_days)
