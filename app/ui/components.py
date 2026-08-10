"""Small reusable UI bits shared by more than one page."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date

from nicegui import ui

from app.models.action import Action
from app.models.enums import ActionType
from app.ui import deps
from app.ui.labels import ACTION_TYPE_LABELS


def assign_action_dialog(
    contact_id: str, contact_name: str, on_saved: Callable[[], Awaitable[None] | None]
) -> None:
    """Opens a small dialog to schedule the contact's next action (spec
    item: "write, call, meet, or come back to the contact later") — used
    from both the dashboard's "haven't been in touch" list and the contact
    detail page's actions section."""
    with ui.dialog() as dialog, ui.card():
        ui.label(f"Назначить действие: {contact_name}").classes("text-lg")
        type_select = ui.select(
            dict(ACTION_TYPE_LABELS),
            value=ActionType.CALL,
            label="Тип действия",
        ).classes("w-full")
        due_input = ui.input("Срок (ГГГГ-ММ-ДД)", value=date.today().isoformat()).classes("w-full")

        async def save() -> None:
            try:
                due_date = date.fromisoformat(due_input.value)
            except ValueError:
                ui.notify("Некорректная дата, ожидается формат ГГГГ-ММ-ДД", type="negative")
                return
            handler = deps.get_link_handler()
            await handler.add_action(contact_id, Action(type=type_select.value, due_date=due_date))
            ui.notify("Действие назначено", type="positive")
            dialog.close()
            result = on_saved()
            if result is not None:
                await result

        with ui.row().classes("justify-end w-full"):
            ui.button("Отмена", on_click=dialog.close).props("flat")
            ui.button("Сохранить", on_click=save)
    dialog.open()
