"""`/app/graph` — the graph screen (stage 7): explore contacts and their
connections, filter by circle/type/dimension, expand a contact's
neighborhood, and find the shortest chain of acquaintances between two
people (networking-app-ai-prompt.md #68/#108). Renders via `ui.echart`
(ships with NiceGUI) — see `app/ui/graph_layout.py` for how positions and
the 3 concentric background rings are computed.
"""

from __future__ import annotations

from nicegui import ui
from nicegui.events import EChartPointClickEventArguments, GenericEventArguments

from app.models.graph import GraphSnapshot
from app.ui import deps, layout
from app.ui.graph_layout import (
    LABEL_TO_REL_TYPE,
    bound_for_zoom,
    build_option,
    compute_positions,
)
from app.ui.labels import CIRCLE_LABELS, CONTACT_TYPE_LABELS

_DEFAULT_LIMIT = 150


def _merge(base: GraphSnapshot, extra: GraphSnapshot) -> GraphSnapshot:
    """Adds `extra`'s nodes/edges to `base` without duplicating anything
    already shown — backs the "expand neighborhood" action, which should
    grow the current view rather than replace it."""
    nodes_by_id = {n.id: n for n in base.nodes}
    for node in extra.nodes:
        nodes_by_id.setdefault(node.id, node)
    edges_by_id = {e.id: e for e in base.edges}
    for edge in extra.edges:
        edges_by_id.setdefault(edge.id, edge)
    nodes = list(nodes_by_id.values())
    contact_count = sum(1 for n in nodes if n.label == "Contact")
    return GraphSnapshot(
        nodes=nodes,
        edges=list(edges_by_id.values()),
        total_contacts=max(base.total_contacts, contact_count),
    )


_ZOOM_STEP = 1.25
_ZOOM_MIN = 0.4
_ZOOM_MAX = 4.0


@ui.page("/app/graph")
async def graph_page() -> None:
    with layout.shell("Граф", wide=True):
        current: dict[str, GraphSnapshot] = {}
        zoom_state = {"level": 1.0}
        center_state = {"x": 0.0, "y": 0.0}
        # Measured once against the real rendered chart element (see the end
        # of this function) so drag-to-pan converts on-screen pixel deltas
        # into data-space units at roughly the right scale. The container is
        # a fixed size regardless of zoom (confirmed with the user — no
        # Google-Maps-style grow/shrink), so one measurement holds for the
        # whole page's lifetime; a fallback guess covers the brief window
        # before that measurement lands.
        chart_px = {"size": 600.0}

        # Status stays outside the collapsible sections below so it's always
        # visible even with both collapsed — collapsed-by-default per the
        # user's request to give the canvas as much default vertical room as
        # possible (filters/path-finder are still one click away).
        status_label = ui.label().classes("text-sm opacity-60")

        with ui.expansion("Фильтры графа", icon="tune").classes("w-full").props("bordered"):
            with ui.row().classes("items-end gap-4 w-full"):
                circle_filter = ui.select(
                    dict(CIRCLE_LABELS), label="Круг", multiple=True, clearable=True
                ).classes("grow")
                type_filter = ui.select(
                    dict(CONTACT_TYPE_LABELS), label="Тип контакта", multiple=True, clearable=True
                ).classes("grow")
                limit_input = ui.number(
                    "Лимит контактов", value=_DEFAULT_LIMIT, min=1, precision=0
                ).classes("w-40")

            async def refresh_snapshot() -> None:
                handler = deps.get_graph_handler()
                limit = int(limit_input.value) if limit_input.value else _DEFAULT_LIMIT
                snapshot = await handler.snapshot(
                    limit=limit,
                    circles=circle_filter.value or None,
                    contact_types=type_filter.value or None,
                )
                render(snapshot)

            ui.button("Обновить", on_click=refresh_snapshot)

        with (
            ui.expansion("Цепочка знакомств", icon="route").classes("w-full").props("bordered"),
            ui.row().classes("items-end gap-4 w-full"),
        ):
            contact_handler = deps.get_contact_handler()
            all_contacts = await contact_handler.list_contacts()
            contact_options = {c.id: c.name for c in all_contacts}
            from_select = ui.select(contact_options, label="От кого", with_input=True).classes(
                "grow"
            )
            to_select = ui.select(contact_options, label="До кого", with_input=True).classes("grow")

            async def find_path() -> None:
                if not from_select.value or not to_select.value:
                    ui.notify("Выберите оба контакта", type="negative")
                    return
                handler = deps.get_graph_handler()
                path = await handler.shortest_path(from_select.value, to_select.value)
                if path is None:
                    ui.notify(
                        "Путь не найден — нет цепочки знакомств между этими контактами",
                        type="warning",
                    )
                    return
                render(path)

            ui.button("Найти путь", on_click=find_path)
            ui.button("Показать весь граф", on_click=refresh_snapshot).props("flat")

        info_panel = ui.card().classes("w-full")
        info_panel.set_visibility(False)

        # xAxis/yAxis share one symmetric [-bound, bound] range (see
        # build_option) so the 3 rings render as actual circles, not
        # ellipses — that only holds if the container is square.
        #
        # Sized off *width* only (`width: 100%` of the page column, up to a
        # generous cap) with `aspect-ratio: 1/1` locking height to match —
        # no viewport-height term at all. Confirmed with the user: on a
        # short/wide window this means the canvas can run taller than the
        # viewport (page scrolls, or use the zoom-out button below to see
        # the whole graph) rather than shrinking the canvas to fit — they'd
        # rather have a bigger graph than one guaranteed to fit above the
        # fold. `aspect-ratio` also makes this responsive for free (recomputed
        # by the browser on any width change, incl. narrow phone/tablet
        # viewports) without needing a resize listener.
        #
        # **Real bug found 2026-08-19:** `aspect-ratio` was silently having
        # no effect at all — confirmed by inspecting the live DOM, the box
        # measured 1448px wide but only 256px tall (= NiceGUI's own
        # `nicegui.css` default `.nicegui-echart { height: 16rem }`,
        # 16*16px), squashing the rings into ellipses. `aspect-ratio` only
        # fills in a dimension that's `auto`; our `.style()` call overrides
        # `width` but never touched `height`, so the framework's explicit
        # `16rem` stayed in effect and aspect-ratio had nothing to resolve.
        # `height: auto` below is the actual fix — it's what makes `height`
        # auto again so aspect-ratio can compute it from the (now correct)
        # width. `flex-shrink: 0` is cheap defensive insurance on top (this
        # div is a flex item of the `ui.column` above it), not itself the
        # fix — flex-shrink was never what caused the squash here.
        with ui.row().classes("items-center gap-2"):
            zoom_label = ui.label().classes("text-sm opacity-60 w-16")

            def redraw() -> None:
                """Re-renders the last snapshot at the current zoom/pan
                state — no new backend call, just a new axis range (see
                build_option's docstring for why this is the zoom/pan
                mechanism, not scroll/roam)."""
                snapshot = current.get("snapshot")
                if snapshot is None:
                    return
                positions = compute_positions(snapshot.nodes)
                chart._props["options"] = build_option(  # noqa: SLF001
                    snapshot,
                    positions,
                    zoom=zoom_state["level"],
                    center=(center_state["x"], center_state["y"]),
                )
                chart.update()
                zoom_label.text = f"{round(zoom_state['level'] * 100)}%"

            def zoom_in() -> None:
                zoom_state["level"] = min(_ZOOM_MAX, zoom_state["level"] * _ZOOM_STEP)
                redraw()

            def zoom_out() -> None:
                zoom_state["level"] = max(_ZOOM_MIN, zoom_state["level"] / _ZOOM_STEP)
                redraw()

            def reset_view() -> None:
                zoom_state["level"] = 1.0
                center_state["x"] = 0.0
                center_state["y"] = 0.0
                redraw()

            ui.button(icon="zoom_in", on_click=zoom_in).props("flat dense round")
            ui.button(icon="zoom_out", on_click=zoom_out).props("flat dense round")
            ui.button("Сбросить вид", on_click=reset_view).props("flat dense")
            ui.label("Перетаскивайте график мышью/тачпадом, чтобы двигаться").classes(
                "text-xs opacity-60"
            )

        chart = ui.echart({}).style(
            "width: min(100%, 1600px);"
            "height: auto;"
            "aspect-ratio: 1 / 1;"
            "margin: 0 auto;"
            "cursor: grab;"
            "flex-shrink: 0;"
        )

        def handle_pan(e: GenericEventArguments) -> None:
            # `buttons` is a native MouseEvent bitmask (bit 0 = left button)
            # reported on every mousemove — checking it here means panning
            # needs no separate mousedown/mouseup state tracking at all, and
            # can't get stuck "stuck dragging" if a mouseup happens outside
            # the chart or even outside the browser window (a classic
            # drag-implementation gotcha). This wasn't just a simplification:
            # `chart.on("mousedown"/"mouseup"/"click", ...)` were tried first
            # and never reached Python at all despite the identical
            # registration mechanism working fine for "mousemove" — some
            # click-related interaction elsewhere in the NiceGUI/Quasar/
            # echarts stack swallows those specific event types before they
            # reach our handler (unconfirmed which layer; not worth
            # resolving when this event carries everything panning needs).
            if not (e.args.get("buttons") or 0) & 1:
                return
            dx_px = e.args.get("movementX") or 0
            dy_px = e.args.get("movementY") or 0
            if not dx_px and not dy_px:
                return
            bound = bound_for_zoom(zoom_state["level"])
            data_per_px = (2 * bound) / chart_px["size"]
            # Grab-and-drag feel: moving the mouse right/down should reveal
            # what was to the left/above, so the view center shifts the
            # opposite way. y is flipped because screen pixels grow downward
            # while this module's data-space y grows upward.
            center_state["x"] -= dx_px * data_per_px
            center_state["y"] += dy_px * data_per_px
            redraw()

        # `args` must be given explicitly — without it NiceGUI tries to
        # JSON-serialize the entire raw event object client-side before ever
        # reaching Python. A plain DOM MouseEvent has no problematic own
        # properties normally, but this reliably breaks the moment any of
        # echarts' own `chart:*` events are used instead (they carry zrender/
        # Vue internals with real circular refs — `__zr`, `parent`/
        # `_children`) — that throws "Converting circular structure to JSON"
        # *before* the websocket emit, silently dropping the event with no
        # server-side trace at all. Cost several dead ends to pin down.
        chart.on("mousemove", handle_pan, args=["movementX", "movementY", "buttons"], throttle=0.05)

        def render(snapshot: GraphSnapshot) -> None:
            current["snapshot"] = snapshot
            positions = compute_positions(snapshot.nodes)
            chart._props["options"] = build_option(  # noqa: SLF001
                snapshot,
                positions,
                zoom=zoom_state["level"],
                center=(center_state["x"], center_state["y"]),
            )
            chart.update()
            zoom_label.text = f"{round(zoom_state['level'] * 100)}%"
            info_panel.set_visibility(False)
            contact_count = sum(1 for n in snapshot.nodes if n.label == "Contact")
            if snapshot.truncated:
                status_label.text = f"Показано {contact_count} из {snapshot.total_contacts}"
            else:
                status_label.text = f"Контактов: {snapshot.total_contacts}"

        def show_info(node_id: str) -> None:
            snapshot = current.get("snapshot")
            node = next((n for n in snapshot.nodes if n.id == node_id), None) if snapshot else None
            if node is None:
                return
            info_panel.clear()
            with info_panel:
                ui.label(node.name).classes("text-base font-bold")
                with ui.row().classes("gap-2"):
                    if node.label == "Contact":
                        ui.link("Открыть карточку", f"/app/contacts/{node_id}")

                        async def expand() -> None:
                            handler = deps.get_graph_handler()
                            extra = await handler.neighbors(node_id)
                            base = current.get("snapshot")
                            if base is not None:
                                render(_merge(base, extra))

                        ui.button("Развернуть окружение", on_click=expand).props("flat dense")
                    else:
                        ui.label(f"Тип: {node.label}").classes("text-xs opacity-60 self-center")

                        async def filter_by_node(target_id: str = node_id) -> None:
                            rel_type = LABEL_TO_REL_TYPE.get(node.label)
                            if rel_type is None:
                                return
                            handler = deps.get_graph_handler()
                            limit = int(limit_input.value) if limit_input.value else _DEFAULT_LIMIT
                            snapshot = await handler.snapshot(
                                limit=limit, dimension_filter=(rel_type, target_id)
                            )
                            render(snapshot)

                        ui.button("Показать связанные контакты", on_click=filter_by_node).props(
                            "flat dense"
                        )
            info_panel.set_visibility(True)

        def on_point_click(e: EChartPointClickEventArguments) -> None:
            if e.series_type != "graph" or e.data_type != "node":
                return
            node_id = e.data.get("id") if isinstance(e.data, dict) else None
            if node_id:
                show_info(node_id)

        chart.on_point_click(on_point_click)

        await refresh_snapshot()

        # Measure the chart's actual rendered pixel size once it's mounted,
        # for handle_pan's pixel-to-data-space conversion above. Best-effort:
        # the `chart_px` fallback default covers this briefly failing (e.g.
        # a slow client) or returning nothing.
        measured = await ui.run_javascript(
            "document.getElementsByClassName('nicegui-echart')[0]?.offsetWidth || 0"
        )
        if measured:
            chart_px["size"] = float(measured)
