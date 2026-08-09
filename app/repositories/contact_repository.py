"""Cypher repository for `(:Contact)`."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.models.contact import Contact
from app.models.enums import Circle, ContactType
from app.repositories.base import Repository

# Lucene special characters that need escaping before a user-typed search
# string can be embedded in a query string passed to
# db.index.fulltext.queryNodes — see https://lucene.apache.org/core/.../
# QueryParserBase (escape()) for the reference character set.
_LUCENE_SPECIAL = re.compile(r'([+\-!(){}\[\]^"~*?:\\/&|])')


def _to_contact(record: Mapping[str, Any]) -> Contact:
    return Contact.model_validate({**record["props"], "id": record["id"]})


def _build_fulltext_query(text: str) -> str:
    """Turn free-typed search text into a Lucene query string.

    Each whitespace-separated token is escaped and given a trailing ``~``
    (fuzzy match, default edit distance) so typos in a name/note still hit —
    e.g. "Jonh" still finds "John". Tokens are left space-separated, which
    Lucene's default query parser combines with implicit OR, so a
    multi-word query matches contacts hitting any of the words (ranked by
    how many/how well via `score`).
    """
    tokens = text.strip().split()
    return " ".join(f"{_LUCENE_SPECIAL.sub(r'\\\1', token)}~" for token in tokens)


class ContactRepository(Repository):
    async def create(self, contact: Contact) -> Contact:
        now = datetime.now(UTC)
        props = contact.model_dump(exclude={"id"}, exclude_none=True)
        props["created_at"] = now
        props["updated_at"] = now
        query = "CREATE (c:Contact) SET c = $props RETURN elementId(c) AS id, c {.*} AS props"
        record = await self._run_one(query, props=props)
        assert record is not None
        return _to_contact(record)

    async def get(self, contact_id: str) -> Contact | None:
        query = (
            "MATCH (c:Contact) WHERE elementId(c) = $id RETURN elementId(c) AS id, c {.*} AS props"
        )
        record = await self._run_one(query, id=contact_id)
        return _to_contact(record) if record else None

    async def list_contacts(
        self,
        *,
        circle: Circle | None = None,
        contact_type: ContactType | None = None,
        archived: bool = False,
    ) -> list[Contact]:
        conditions = ["c.archived = $archived"]
        params: dict[str, Any] = {"archived": archived}
        if circle is not None:
            conditions.append("c.circle = $circle")
            params["circle"] = circle
        if contact_type is not None:
            conditions.append("c.contact_type = $contact_type")
            params["contact_type"] = contact_type
        where = " AND ".join(conditions)
        query = (
            f"MATCH (c:Contact) WHERE {where} "
            "RETURN elementId(c) AS id, c {.*} AS props ORDER BY c.name"
        )
        records = await self._run(query, **params)
        return [_to_contact(r) for r in records]

    async def update(self, contact_id: str, updates: dict[str, Any]) -> Contact | None:
        updates = {**updates, "updated_at": datetime.now(UTC)}
        query = (
            "MATCH (c:Contact) WHERE elementId(c) = $id "
            "SET c += $updates RETURN elementId(c) AS id, c {.*} AS props"
        )
        record = await self._run_one(query, id=contact_id, updates=updates)
        return _to_contact(record) if record else None

    async def archive(self, contact_id: str) -> Contact | None:
        """Soft delete — see AGENTS.md/spec: deletion always needs
        confirmation, archiving is the reversible default."""
        return await self.update(contact_id, {"archived": True, "archived_at": datetime.now(UTC)})

    async def unarchive(self, contact_id: str) -> Contact | None:
        return await self.update(contact_id, {"archived": False, "archived_at": None})

    async def list_stale(self, *, threshold_days: int) -> list[dict[str, Any]]:
        """Contacts nobody has talked to in >= `threshold_days` — backs both
        the dashboard's "haven't been in touch" list and the CLI "stale"
        scenario. A contact with zero interactions ever counts as stale too
        (never having talked is certainly "a while")."""
        query = """
        MATCH (c:Contact) WHERE c.archived = false
        OPTIONAL MATCH (c)-[:HAD_INTERACTION]->(i:Interaction)
        WITH c, max(i.date) AS last_interaction_date
        WHERE last_interaction_date IS NULL
           OR duration.between(last_interaction_date, date()).days >= $threshold_days
        RETURN elementId(c) AS id, c {.*} AS props, last_interaction_date
        ORDER BY last_interaction_date ASC
        """
        records = await self._run(query, threshold_days=threshold_days)
        return [
            {
                "contact": _to_contact(r),
                "last_interaction_date": r["last_interaction_date"],
            }
            for r in records
        ]

    async def search_fulltext(self, query: str, *, limit: int = 20) -> list[Contact]:
        """Full-text search over name/notes via the `contact_fulltext` Lucene
        index (created in `app.db.ensure_schema`). Archived contacts are
        excluded — this backs the live dashboard search box, not an
        archive-browsing tool."""
        lucene_query = _build_fulltext_query(query)
        if not lucene_query:
            return []
        # Cypher param is named $search, not $query — Repository._run's own
        # positional parameter is named `query` (the Cypher text itself), so
        # a kwarg literally named `query` collides with it.
        cypher = (
            "CALL db.index.fulltext.queryNodes('contact_fulltext', $search) "
            "YIELD node, score "
            "WHERE node.archived = false "
            "RETURN elementId(node) AS id, node {.*} AS props, score "
            "ORDER BY score DESC LIMIT $limit"
        )
        records = await self._run(cypher, search=lucene_query, limit=limit)
        return [_to_contact(r) for r in records]

    async def delete(self, contact_id: str) -> bool:
        """Hard delete — rare, irreversible; the API layer requires an
        explicit confirm flag before calling this (see app/api/contacts.py)."""
        query = "MATCH (c:Contact) WHERE elementId(c) = $id DETACH DELETE c"
        summary = await self._run_summary(query, id=contact_id)
        return bool(summary.counters.nodes_deleted)
