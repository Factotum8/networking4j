"""Pure helpers translating a `GraphSnapshot` into `ui.echart` options —
kept separate from the page so the position/option-building logic is easy
to reason about on its own.

The 3 concentric circles are real geometry, not just a Cytoscape/NVL-style
automatic clustering: every node gets an explicit (x, y) computed here,
and the graph series is bound to a fixed-range `cartesian2d` coordinate
system (see `build_option`) so a `custom` series can draw matching
background rings via `api.coord(...)` — they stay aligned with the nodes
through zoom/pan because both series share the same axes.
"""

from __future__ import annotations

import math
from typing import Any

from app.models.enums import Circle, DimensionLinkType
from app.models.graph import GraphSnapshot, GraphVisNode
from app.ui.labels import CIRCLE_LABELS

# Support Circle = core (innermost), Success Circle = outer zone — item 1
# in networking-app-ai-prompt.md. Contacts with no `circle` set get a
# small dedicated cluster at the very center instead of being folded into
# one of the three real rings (not having been categorized yet isn't the
# same as being "in" a circle).
UNASSIGNED_RADIUS = 30.0
RING_RADII: dict[Circle, float] = {
    Circle.SUPPORT_CIRCLE: 110.0,
    Circle.FUNCTIONAL_CIRCLES: 230.0,
    Circle.SUCCESS_CIRCLE: 350.0,
}
DIMENSION_RADIUS = 470.0
_MAX_RADIUS = DIMENSION_RADIUS

DIMENSION_LABELS_RU: dict[str, str] = {
    "Company": "Компания",
    "Event": "Событие",
    "Community": "Сообщество",
    "Project": "Проект",
    "Interest": "Интерес",
    "Tag": "Тег",
}

LABEL_TO_REL_TYPE: dict[str, DimensionLinkType] = {
    "Company": DimensionLinkType.WORKS_AT,
    "Event": DimensionLinkType.ATTENDED,
    "Community": DimensionLinkType.MEMBER_OF,
    "Project": DimensionLinkType.INVOLVED_IN,
    "Interest": DimensionLinkType.INTERESTED_IN,
    "Tag": DimensionLinkType.TAGGED,
}

_CATEGORY_NAMES: list[str] = [
    "Support Circle",
    "Functional Circles",
    "Success Circle",
    "Без круга",
    *DIMENSION_LABELS_RU.values(),
]
_CATEGORY_INDEX = {name: i for i, name in enumerate(_CATEGORY_NAMES)}


def _category_name(node: GraphVisNode) -> str:
    if node.label == "Contact":
        return CIRCLE_LABELS[node.circle] if node.circle else "Без круга"
    return DIMENSION_LABELS_RU.get(node.label, node.label)


def _place_ring(
    nodes: list[GraphVisNode], radius: float, positions: dict[str, tuple[float, float]]
) -> None:
    count = len(nodes)
    for i, node in enumerate(nodes):
        angle = (2 * math.pi * i / count) if count else 0.0
        positions[node.id] = (radius * math.cos(angle), radius * math.sin(angle))


def compute_positions(nodes: list[GraphVisNode]) -> dict[str, tuple[float, float]]:
    """One (x, y) per node: contacts arranged into their circle's ring (or
    the central unassigned cluster), dimension nodes on one outer ring."""
    groups: dict[Circle | None, list[GraphVisNode]] = {}
    dimension_nodes: list[GraphVisNode] = []
    for node in nodes:
        if node.label == "Contact":
            groups.setdefault(node.circle, []).append(node)
        else:
            dimension_nodes.append(node)

    positions: dict[str, tuple[float, float]] = {}
    for circle, group in groups.items():
        radius = RING_RADII[circle] if circle else UNASSIGNED_RADIUS
        _place_ring(group, radius, positions)
    _place_ring(dimension_nodes, DIMENSION_RADIUS, positions)
    return positions


def bound_for_zoom(zoom: float) -> float:
    """Half-width of the shared axis range at a given zoom level. Exposed
    (not just inlined in `build_option`) because the graph page's
    drag-to-pan handler needs the exact same value to convert on-screen
    pixel deltas into this module's data-space units — using a different
    formula there would make dragging feel inconsistent with the current
    zoom level."""
    return (_MAX_RADIUS * 1.15) / zoom


def build_option(
    snapshot: GraphSnapshot,
    positions: dict[str, tuple[float, float]],
    zoom: float = 1.0,
    center: tuple[float, float] = (0.0, 0.0),
) -> dict[str, Any]:
    nodes = [
        {
            "id": node.id,
            "name": node.name,
            # `value` (not just x/y) is what a graph series bound to a
            # cartesian2d coordinateSystem actually reads for position —
            # x/y alone are only honored under the axis-less "none"
            # layout. Confirmed empirically: without `value`, the graph
            # series silently renders zero nodes (no error, nothing in
            # the console) once coordinateSystem is set.
            "value": list(positions[node.id]),
            "x": positions[node.id][0],
            "y": positions[node.id][1],
            "symbolSize": 26 if node.label == "Contact" else 16,
            "category": _CATEGORY_INDEX[_category_name(node)],
        }
        for node in snapshot.nodes
    ]
    edges = [
        {
            "source": edge.source,
            "target": edge.target,
            "label": {"show": bool(edge.edge_label), "formatter": edge.edge_label or ""},
            "lineStyle": {"width": 2 if edge.rel_type == "KNOWS" else 1},
        }
        for edge in snapshot.edges
    ]
    # `zoom`/`center` shrink-and-shift the shared axis range around the same
    # fixed node positions — higher zoom = smaller bound = nodes spread
    # further apart visually; `center` recenters the window for panning.
    # This is a real fix, not a workaround: confirmed empirically (a
    # standalone echarts sandbox page, and real trusted mouse-wheel/drag
    # input via browser automation, not just synthetic JS events) that a
    # `graph` series bound to `coordinateSystem: cartesian2d` does NOT
    # respond to ECharts' own `dataZoom`/`roam` interactive zoom-or-pan at
    # all — the axis range never changes on wheel or drag input, silently,
    # no console error. Likely because `graph` series has no
    # `xAxisIndex`/`yAxisIndex` of its own for dataZoom to target, unlike
    # scatter/line/bar, and `roam`'s own view transform is apparently only
    # wired up under the axis-less "none" layout. Re-issuing `setOption`
    # with a new axis range (what the zoom buttons and the mousemove-driven
    # drag-to-pan handler in app/ui/pages/graph.py both do) uses the exact
    # same rendering path that already correctly draws the initial view,
    # so it's guaranteed to work.
    bound = bound_for_zoom(zoom)
    cx, cy = center

    return {
        "tooltip": {},
        "legend": [{"data": _CATEGORY_NAMES, "top": 0}],
        "xAxis": {"show": False, "min": cx - bound, "max": cx + bound, "type": "value"},
        "yAxis": {"show": False, "min": cy - bound, "max": cy + bound, "type": "value"},
        "series": [
            {
                # The 3 background rings — one custom-series datum per
                # ring radius, drawn via api.coord() so they scale/pan
                # exactly like the graph series sharing the same axes.
                "type": "custom",
                "coordinateSystem": "cartesian2d",
                "silent": True,
                "z": 1,
                "data": list(RING_RADII.values()),
                ":renderItem": (
                    "function(params, api) {"
                    "  var r = api.value(0);"
                    "  var center = api.coord([0, 0]);"
                    "  var edge = api.coord([r, 0]);"
                    "  var radius = Math.abs(edge[0] - center[0]);"
                    "  return {"
                    "    type: 'circle',"
                    "    shape: {cx: center[0], cy: center[1], r: radius},"
                    "    style: {"
                    "      fill: 'rgba(100, 150, 220, 0.06)',"
                    "      stroke: 'rgba(100, 150, 220, 0.35)',"
                    "      lineWidth: 1"
                    "    }"
                    "  };"
                    "}"
                ),
            },
            {
                "type": "graph",
                "coordinateSystem": "cartesian2d",
                # Both explicitly False. `roam`'s own view-transform is a
                # no-op under coordinateSystem: cartesian2d (see the big
                # comment above `bound`) — but even inert, it still makes
                # zrender (echarts' internal canvas layer) capture and
                # stopPropagation() every mousedown/mousemove for its own
                # dead-end pan handling, so the hand-rolled drag-to-pan
                # listeners in app/ui/pages/graph.py never see the events
                # while it's on. `draggable` lets you grab and reposition a
                # single node, which (confirmed by reproducing it) also
                # wins over a whole-graph drag whenever it starts on top of
                # a node.
                "roam": False,
                "draggable": False,
                "label": {"show": True, "position": "right"},
                "categories": [{"name": name} for name in _CATEGORY_NAMES],
                "data": nodes,
                "links": edges,
                "lineStyle": {"color": "source", "curveness": 0.1},
                "emphasis": {"focus": "adjacency"},
                "z": 2,
            },
        ],
    }
