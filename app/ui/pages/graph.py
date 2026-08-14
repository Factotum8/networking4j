"""`/app/graph` — the graph screen (stage 7): explore contacts and their
connections, filter by circle/type/dimension, expand a contact's
neighborhood, and find the shortest chain of acquaintances between two
people (networking-app-ai-prompt.md #68/#108). Renders via `ui.echart`
(ships with NiceGUI) — see `app/ui/graph_layout.py` for how positions and
the 3 concentric background rings are computed.
"""

from __future__ import annotations

from nicegui import ui
from nicegui.events import EChartPointClickEventArguments

from app.models.graph import GraphSnapshot
from app.ui import deps, layout
from app.ui.graph_layout import LABEL_TO_REL_TYPE, build_option, compute_positions
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


@ui.page("/app/graph")
async def graph_page() -> None:
    with layout.shell("Граф", wide=True):
        current: dict[str, GraphSnapshot] = {}

        with ui.card().classes("w-full"):
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
                status_label = ui.label().classes("text-sm opacity-60")

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

        with ui.card().classes("w-full"):
            ui.label("Цепочка знакомств").classes("text-sm font-bold")
            with ui.row().classes("items-end gap-4 w-full"):
                contact_handler = deps.get_contact_handler()
                all_contacts = await contact_handler.list_contacts()
                contact_options = {c.id: c.name for c in all_contacts}
                from_select = ui.select(contact_options, label="От кого", with_input=True).classes(
                    "grow"
                )
                to_select = ui.select(contact_options, label="До кого", with_input=True).classes(
                    "grow"
                )

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

        chart = ui.echart({}).classes("w-full").style("height: 70vh")

        def render(snapshot: GraphSnapshot) -> None:
            current["snapshot"] = snapshot
            positions = compute_positions(snapshot.nodes)
            chart._props["options"] = build_option(snapshot, positions)  # noqa: SLF001
            chart.update()
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
