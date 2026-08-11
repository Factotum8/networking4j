"""`/` — the main screen (stage 6, step C): search, filters, recently
added contacts, reminders, and the "haven't been in touch" list — per the
spec's main-screen description (networking-app-ai-prompt.md #66).
"""

from __future__ import annotations

from datetime import UTC, datetime

from nicegui import ui

from app.models.contact import Contact
from app.ui import deps, layout
from app.ui.components import assign_action_dialog
from app.ui.labels import ACTION_TYPE_LABELS, CIRCLE_LABELS, CONTACT_TYPE_LABELS

_RECENT_COUNT = 5


def _contact_row(contact: Contact, *, subtitle: str = "") -> None:
    with ui.row().classes("items-center justify-between w-full"), ui.column().classes("gap-0"):
        ui.link(contact.name, f"/app/contacts/{contact.id}").classes("text-base")
        meta = " · ".join(
            p
            for p in [
                CIRCLE_LABELS.get(contact.circle, "") if contact.circle else "",
                CONTACT_TYPE_LABELS.get(contact.contact_type, "") if contact.contact_type else "",
                subtitle,
            ]
            if p
        )
        if meta:
            ui.label(meta).classes("text-xs opacity-60")


@ui.page("/")
async def dashboard_page() -> None:
    with layout.shell("Дашборд"):
        # --- Search ---
        with ui.card().classes("w-full"):
            ui.label("Поиск").classes("text-lg font-bold")
            with ui.row().classes("items-center w-full"):
                search_input = ui.input("Имя или заметка").classes("grow")
                search_results = ui.column().classes("w-full gap-1")

            async def run_search() -> None:
                search_results.clear()
                query = search_input.value.strip()
                if not query:
                    return
                handler = deps.get_search_handler()
                results = await handler.search(query)
                with search_results:
                    if not results:
                        ui.label("Ничего не найдено").classes("text-sm opacity-60")
                    for contact in results:
                        _contact_row(contact)

            search_input.on("keydown.enter", run_search)
            ui.button("Искать", on_click=run_search)

        # --- Filters + overview ---
        with ui.card().classes("w-full"):
            ui.label("Контакты").classes("text-lg font-bold")
            overview = ui.column().classes("w-full gap-1")

            async def refresh_overview() -> None:
                overview.clear()
                handler = deps.get_contact_handler()
                filters: dict[str, object] = {}
                if circle_filter.value is not None:
                    filters["circle"] = circle_filter.value
                if type_filter.value is not None:
                    filters["contact_type"] = type_filter.value
                contacts = await handler.list_contacts(**filters)
                with overview:
                    if not contacts:
                        ui.label("Нет контактов по заданным фильтрам").classes("text-sm opacity-60")
                    for contact in contacts[:20]:
                        _contact_row(contact)
                    if len(contacts) > 20:
                        ui.label(f"...и ещё {len(contacts) - 20}").classes("text-xs opacity-60")

            with ui.row().classes("items-center w-full"):
                circle_filter = ui.select(
                    dict(CIRCLE_LABELS),
                    label="Круг",
                    clearable=True,
                    on_change=refresh_overview,
                ).classes("grow")
                type_filter = ui.select(
                    dict(CONTACT_TYPE_LABELS),
                    label="Тип контакта",
                    clearable=True,
                    on_change=refresh_overview,
                ).classes("grow")
            await refresh_overview()

        # --- Recently added ---
        with ui.card().classes("w-full"):
            ui.label("Недавно добавленные").classes("text-lg font-bold")
            handler = deps.get_contact_handler()
            all_active = await handler.list_contacts()
            recent = sorted(
                all_active,
                key=lambda c: c.created_at or datetime.min.replace(tzinfo=UTC),
                reverse=True,
            )[:_RECENT_COUNT]
            if not recent:
                ui.label("Пока нет контактов").classes("text-sm opacity-60")
            for contact in recent:
                _contact_row(contact)

        # --- Reminders + stale contacts ---
        digest_section = ui.column().classes("w-full gap-4")

        async def refresh_digest() -> None:
            digest_section.clear()
            reminder_handler = deps.get_reminder_handler()
            digest = await reminder_handler.build_digest()

            with digest_section:
                with ui.card().classes("w-full"):
                    ui.label("Напоминания").classes("text-lg font-bold")
                    if not digest.due_actions and not digest.upcoming_birthdays:
                        ui.label("Нечего напомнить").classes("text-sm opacity-60")
                    for entry in digest.due_actions:
                        action_id_value = entry.action.id
                        if action_id_value is None:
                            continue  # defensive: every persisted Action has an id

                        async def complete(action_id: str = action_id_value) -> None:
                            link_handler = deps.get_link_handler()
                            await link_handler.complete_action(action_id)
                            ui.notify("Действие отмечено выполненным", type="positive")
                            await refresh_digest()

                        with ui.row().classes("items-center justify-between w-full"):
                            action_label = ACTION_TYPE_LABELS[entry.action.type]
                            _contact_row(
                                Contact(id=entry.contact_id, name=entry.contact_name),
                                subtitle=f"{action_label}, срок {entry.action.due_date}",
                            )
                            ui.button("Готово", on_click=complete).props("flat")
                    for bday in digest.upcoming_birthdays:
                        ui.label(
                            f"🎂 {bday.name} — через {bday.days_away} дн. ({bday.birthday})"
                        ).classes("text-sm")

                with ui.card().classes("w-full"):
                    ui.label("Давно не общались").classes("text-lg font-bold")
                    if not digest.stale_contacts:
                        ui.label("Все контакты в тонусе").classes("text-sm opacity-60")
                    for stale in digest.stale_contacts:

                        def open_dialog(
                            contact_id: str = stale.contact.id or "",
                            contact_name: str = stale.contact.name,
                        ) -> None:
                            assign_action_dialog(contact_id, contact_name, refresh_digest)

                        with ui.row().classes("items-center justify-between w-full"):
                            _contact_row(
                                stale.contact,
                                subtitle=(
                                    f"последний контакт: {stale.last_interaction_date}"
                                    if stale.last_interaction_date
                                    else "ещё не общались"
                                ),
                            )
                            ui.button("Назначить действие", on_click=open_dialog).props("flat")

        await refresh_digest()
