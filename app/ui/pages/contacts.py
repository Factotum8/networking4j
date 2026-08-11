"""`/app/contacts` — the contacts list page (stage 6, step D): a
filterable, archive-aware list with a "+ Новый контакт" entry point.
"""

from __future__ import annotations

from nicegui import ui

from app.ui import deps, layout
from app.ui.labels import CIRCLE_LABELS, CONTACT_TYPE_LABELS


@ui.page("/app/contacts")
async def contacts_page() -> None:
    with layout.shell("Контакты"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.label("Контакты").classes("text-lg font-bold")
            ui.button("+ Новый контакт", on_click=lambda: ui.navigate.to("/app/contacts/new"))

        with ui.card().classes("w-full"):
            with ui.row().classes("items-center w-full"):
                circle_filter = ui.select(
                    dict(CIRCLE_LABELS), label="Круг", clearable=True
                ).classes("grow")
                type_filter = ui.select(
                    dict(CONTACT_TYPE_LABELS), label="Тип контакта", clearable=True
                ).classes("grow")
                archived_toggle = ui.switch("Показывать архивные")

            results = ui.column().classes("w-full gap-1")

            async def refresh() -> None:
                results.clear()
                handler = deps.get_contact_handler()
                filters: dict[str, object] = {"archived": archived_toggle.value}
                if circle_filter.value is not None:
                    filters["circle"] = circle_filter.value
                if type_filter.value is not None:
                    filters["contact_type"] = type_filter.value
                contacts = await handler.list_contacts(**filters)
                with results:
                    if not contacts:
                        ui.label("Нет контактов по заданным фильтрам").classes("text-sm opacity-60")
                    for contact in contacts:
                        row_classes = "items-center justify-between w-full border-b py-1"
                        with ui.row().classes(row_classes), ui.column().classes("gap-0"):
                            ui.link(contact.name, f"/app/contacts/{contact.id}").classes(
                                "text-base"
                            )
                            meta = " · ".join(
                                p
                                for p in [
                                    CIRCLE_LABELS.get(contact.circle, "") if contact.circle else "",
                                    CONTACT_TYPE_LABELS.get(contact.contact_type, "")
                                    if contact.contact_type
                                    else "",
                                    contact.city or "",
                                    contact.phone or "",
                                ]
                                if p
                            )
                            if meta:
                                ui.label(meta).classes("text-xs opacity-60")

            circle_filter.on_value_change(refresh)
            type_filter.on_value_change(refresh)
            archived_toggle.on_value_change(refresh)
            await refresh()
