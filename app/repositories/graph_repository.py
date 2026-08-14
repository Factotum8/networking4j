"""Cypher for the stage-7 graph screen: a filtered snapshot of the active
network, one contact's immediate neighborhood ("expand"), and the shortest
KNOWS-path between two contacts ("chain of acquaintances") — the three
Cypher shapes the spec calls out by name (networking-app-ai-prompt.md
#108: shortestPath, variable-length paths, filters by labels/properties).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.models.enums import Circle, ContactType, DimensionLinkType
from app.models.graph import GraphSnapshot, GraphVisEdge, GraphVisNode
from app.repositories.base import Repository

# Same fixed enum -> label mapping as LinkRepository._TARGET_LABELS — kept
# local rather than shared since this repository only needs the relationship
# type list for an IN-clause, not the label side.
_DIMENSION_REL_TYPES = [rel_type.value for rel_type in DimensionLinkType]


def _contact_node(record: Mapping[str, Any], *, prefix: str = "") -> GraphVisNode:
    circle = record[f"{prefix}circle"]
    contact_type = record[f"{prefix}contact_type"]
    return GraphVisNode(
        id=record[f"{prefix}id"],
        label="Contact",
        name=record[f"{prefix}name"],
        circle=Circle(circle) if circle else None,
        contact_type=ContactType(contact_type) if contact_type else None,
    )


class GraphRepository(Repository):
    async def snapshot(
        self,
        *,
        limit: int,
        circles: list[Circle] | None = None,
        contact_types: list[ContactType] | None = None,
        dimension_filter: tuple[DimensionLinkType, str] | None = None,
    ) -> GraphSnapshot:
        conditions = ["c.archived = false"]
        params: dict[str, Any] = {}
        if circles:
            conditions.append("c.circle IN $circles")
            params["circles"] = [c.value for c in circles]
        if contact_types:
            conditions.append("c.contact_type IN $contact_types")
            params["contact_types"] = [t.value for t in contact_types]
        if dimension_filter is not None:
            rel_type, target_id = dimension_filter
            # rel_type is always one of the fixed DimensionLinkType members
            # (never raw user input), so interpolating its value is as safe
            # as the identical pattern already used in LinkRepository.
            conditions.append(
                f"EXISTS {{ MATCH (c)-[:{rel_type.value}]->(t) "
                "WHERE elementId(t) = $dimension_target_id }"
            )
            params["dimension_target_id"] = target_id
        where = " AND ".join(conditions)

        total_record = await self._run_one(
            f"MATCH (c:Contact) WHERE {where} RETURN count(c) AS total", **params
        )
        total_contacts = total_record["total"] if total_record else 0

        contact_records = await self._run(
            f"MATCH (c:Contact) WHERE {where} "
            "RETURN elementId(c) AS id, c.name AS name, c.circle AS circle, "
            "c.contact_type AS contact_type ORDER BY c.name LIMIT $limit",
            **params,
            limit=limit,
        )
        nodes = [_contact_node(r) for r in contact_records]
        contact_ids = [n.id for n in nodes]
        if not contact_ids:
            return GraphSnapshot(nodes=[], edges=[], total_contacts=total_contacts)

        knows_records = await self._run(
            "MATCH (a:Contact)-[k:KNOWS]->(b:Contact) "
            "WHERE elementId(a) IN $ids AND elementId(b) IN $ids "
            "RETURN elementId(k) AS id, elementId(a) AS source, elementId(b) AS target, "
            "k.closeness AS closeness",
            ids=contact_ids,
        )
        edges = [
            GraphVisEdge(
                id=r["id"],
                source=r["source"],
                target=r["target"],
                rel_type="KNOWS",
                edge_label=str(r["closeness"]) if r["closeness"] is not None else None,
            )
            for r in knows_records
        ]

        dim_records = await self._run(
            "MATCH (c:Contact)-[rel]->(t) "
            "WHERE elementId(c) IN $ids AND type(rel) IN $rel_types "
            "RETURN elementId(rel) AS id, elementId(c) AS contact_id, type(rel) AS rel_type, "
            "elementId(t) AS target_id, labels(t)[0] AS target_label, t.name AS target_name",
            ids=contact_ids,
            rel_types=_DIMENSION_REL_TYPES,
        )
        seen_dim_nodes: dict[str, GraphVisNode] = {}
        for r in dim_records:
            seen_dim_nodes.setdefault(
                r["target_id"],
                GraphVisNode(id=r["target_id"], label=r["target_label"], name=r["target_name"]),
            )
            edges.append(
                GraphVisEdge(
                    id=r["id"],
                    source=r["contact_id"],
                    target=r["target_id"],
                    rel_type=r["rel_type"],
                )
            )
        nodes.extend(seen_dim_nodes.values())

        return GraphSnapshot(nodes=nodes, edges=edges, total_contacts=total_contacts)

    async def neighbors(self, contact_id: str) -> GraphSnapshot:
        """One contact's immediate neighborhood — KNOWS (either direction)
        plus dimension links — for the graph screen's "expand" action."""
        center = await self._run_one(
            "MATCH (c:Contact) WHERE elementId(c) = $contact_id "
            "RETURN elementId(c) AS id, c.name AS name, c.circle AS circle, "
            "c.contact_type AS contact_type",
            contact_id=contact_id,
        )
        if center is None:
            return GraphSnapshot(nodes=[], edges=[], total_contacts=0)

        nodes = [_contact_node(center)]
        edges: list[GraphVisEdge] = []

        knows_records = await self._run(
            "MATCH (c:Contact)-[k:KNOWS]-(other:Contact) WHERE elementId(c) = $contact_id "
            "RETURN elementId(k) AS id, elementId(startNode(k)) AS source, "
            "elementId(endNode(k)) AS target, k.closeness AS closeness, "
            "elementId(other) AS other_id, other.name AS other_name, "
            "other.circle AS other_circle, other.contact_type AS other_contact_type",
            contact_id=contact_id,
        )
        for r in knows_records:
            nodes.append(_contact_node(r, prefix="other_"))
            edges.append(
                GraphVisEdge(
                    id=r["id"],
                    source=r["source"],
                    target=r["target"],
                    rel_type="KNOWS",
                    edge_label=str(r["closeness"]) if r["closeness"] is not None else None,
                )
            )

        dim_records = await self._run(
            "MATCH (c:Contact)-[rel]->(t) "
            "WHERE elementId(c) = $contact_id AND type(rel) IN $rel_types "
            "RETURN elementId(rel) AS id, type(rel) AS rel_type, elementId(t) AS target_id, "
            "labels(t)[0] AS target_label, t.name AS target_name",
            contact_id=contact_id,
            rel_types=_DIMENSION_REL_TYPES,
        )
        for r in dim_records:
            nodes.append(
                GraphVisNode(id=r["target_id"], label=r["target_label"], name=r["target_name"])
            )
            edges.append(
                GraphVisEdge(
                    id=r["id"], source=contact_id, target=r["target_id"], rel_type=r["rel_type"]
                )
            )

        contact_count = sum(1 for n in nodes if n.label == "Contact")
        return GraphSnapshot(nodes=nodes, edges=edges, total_contacts=contact_count)

    async def shortest_path(self, from_id: str, to_id: str) -> GraphSnapshot | None:
        """The "chain of acquaintances" scenario — shortest KNOWS path
        between two contacts, direction-agnostic (knowing someone matters
        here more than who introduced whom). `None` if no path exists.

        Returns plain maps built via `nodes(p)`/`relationships(p)` rather
        than `RETURN p` directly — the driver's generic `Record.data()`
        (which `Repository._run` uses) collapses `Node`/`Relationship`
        values down to just their properties, losing elementId and label/
        type, so the path has to be unpacked in Cypher instead.
        """
        record = await self._run_one(
            "MATCH (a:Contact) WHERE elementId(a) = $from_id "
            "MATCH (b:Contact) WHERE elementId(b) = $to_id "
            "MATCH p = shortestPath((a)-[:KNOWS*]-(b)) "
            "RETURN [n IN nodes(p) | {id: elementId(n), name: n.name, circle: n.circle, "
            "contact_type: n.contact_type}] AS path_nodes, "
            "[r IN relationships(p) | {id: elementId(r), source: elementId(startNode(r)), "
            "target: elementId(endNode(r)), closeness: r.closeness}] AS path_rels",
            from_id=from_id,
            to_id=to_id,
        )
        if record is None:
            return None

        nodes = [
            GraphVisNode(
                id=n["id"],
                label="Contact",
                name=n["name"],
                circle=Circle(n["circle"]) if n["circle"] else None,
                contact_type=ContactType(n["contact_type"]) if n["contact_type"] else None,
            )
            for n in record["path_nodes"]
        ]
        edges = [
            GraphVisEdge(
                id=r["id"],
                source=r["source"],
                target=r["target"],
                rel_type="KNOWS",
                edge_label=str(r["closeness"]) if r["closeness"] is not None else None,
            )
            for r in record["path_rels"]
        ]
        return GraphSnapshot(nodes=nodes, edges=edges, total_contacts=len(nodes))
