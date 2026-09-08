"""`/app/contacts/new` and `/app/contacts/{contact_id}` — the contact
detail/edit page (stage 6, step E): the full field form plus every
relationship section (dimension links, KNOWS, relatives, interactions,
actions).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

from nicegui import ui

from app.handlers.contact_handler import ContactNotFoundError
from app.models.contact import Contact
from app.models.enums import DimensionLinkType
from app.models.interaction import Interaction
from app.models.relationships import Knows
from app.models.relative import Relative
from app.repositories.named_node_repository import NamedNodeRepository
from app.ui import deps, layout
from app.ui.components import assign_action_dialog
from app.ui.labels import (
    ACTION_TYPE_LABELS,
    CIRCLE_LABELS,
    CONTACT_TYPE_LABELS,
    DIMENSION_TYPE_LABELS,
    INTERACTION_TYPE_LABELS,
)

_RATING_OPTIONS: dict[int | None, str] = {None: "—", **{n: str(n) for n in range(1, 11)}}


def _parse_optional_date(text: str) -> date | None:
    text = text.strip()
    if not text:
        return None
    return date.fromisoformat(text)


@ui.page("/app/contacts/new")
async def new_contact_page() -> None:
    with layout.shell("Новый контакт"):
        _render_main_form(contact=None)


@ui.page("/app/contacts/{contact_id}")
async def contact_detail_page(contact_id: str) -> None:
    handler = deps.get_contact_handler()
    try:
        contact = await handler.get(contact_id)
    except ContactNotFoundError:
        with layout.shell("Контакт не найден"):
            ui.label(f"Контакт {contact_id} не найден.").classes("text-lg")
            ui.link("К списку контактов", "/app/contacts")
        return

    with layout.shell(contact.name):
        _render_main_form(contact=contact)
        await _render_dimension_links(contact_id)
        await _render_knows(contact_id)
        await _render_relatives(contact_id)
        await _render_interactions(contact_id)
        await _render_actions(contact_id)


def _render_main_form(contact: Contact | None) -> None:
    """The core field form. Shared between /new (contact is None, only a
    "Создать" action) and the detail page (pre-filled, "Сохранить" +
    archive/unarchive + delete)."""
    is_new = contact is None
    c = contact or Contact(name="")

    with ui.card().classes("w-full"):
        if not is_new and c.archived:
            ui.label("Архивирован").classes("text-sm text-orange-600 font-bold")

        name_input = ui.input("Имя *", value=c.name).classes("w-full")
        with ui.row().classes("w-full gap-4"):
            phone_input = ui.input("Телефон", value=c.phone or "").classes("grow")
            email_input = ui.input("Email", value=c.email or "").classes("grow")
        with ui.row().classes("w-full gap-4"):
            position_input = ui.input("Должность", value=c.position or "").classes("grow")
            city_input = ui.input("Город", value=c.city or "").classes("grow")
        photo_input = ui.input("Фото (URL)", value=c.photo or "").classes("w-full")
        with ui.row().classes("w-full gap-4"):
            circle_select = ui.select(
                dict(CIRCLE_LABELS), label="Круг", value=c.circle, clearable=True
            ).classes("grow")
            type_select = ui.select(
                dict(CONTACT_TYPE_LABELS),
                label="Тип контакта",
                value=c.contact_type,
                clearable=True,
            ).classes("grow")
        with ui.row().classes("w-full gap-4"):
            dangerous_select = ui.select(
                _RATING_OPTIONS, label="Dangerous", value=c.dangerous
            ).classes("grow")
            interesting_select = ui.select(
                _RATING_OPTIONS, label="Interesting", value=c.interesting
            ).classes("grow")
            difficult_select = ui.select(
                _RATING_OPTIONS, label="Difficult", value=c.difficult
            ).classes("grow")
        with ui.row().classes("w-full gap-4"):
            birthday_input = ui.input(
                "День рождения (ГГГГ-ММ-ДД)", value=c.birthday.isoformat() if c.birthday else ""
            ).classes("grow")
            met_place_input = ui.input("Место встречи", value=c.met_place or "").classes("grow")
            met_date_input = ui.input(
                "Дата встречи (ГГГГ-ММ-ДД)", value=c.met_date.isoformat() if c.met_date else ""
            ).classes("grow")
        notes_input = ui.textarea("Заметки", value=c.notes or "").classes("w-full")

        def build_updates() -> dict[str, object] | None:
            if not name_input.value.strip():
                ui.notify("Имя обязательно", type="negative")
                return None
            try:
                birthday = _parse_optional_date(birthday_input.value)
                met_date = _parse_optional_date(met_date_input.value)
            except ValueError:
                ui.notify("Некорректная дата, ожидается формат ГГГГ-ММ-ДД", type="negative")
                return None
            return {
                "name": name_input.value.strip(),
                "phone": phone_input.value.strip() or None,
                "email": email_input.value.strip() or None,
                "position": position_input.value.strip() or None,
                "city": city_input.value.strip() or None,
                "photo": photo_input.value.strip() or None,
                "circle": circle_select.value,
                "contact_type": type_select.value,
                "dangerous": dangerous_select.value,
                "interesting": interesting_select.value,
                "difficult": difficult_select.value,
                "birthday": birthday,
                "met_place": met_place_input.value.strip() or None,
                "met_date": met_date,
                "notes": notes_input.value.strip() or None,
            }

        async def save() -> None:
            updates = build_updates()
            if updates is None:
                return
            contact_handler = deps.get_contact_handler()
            if is_new:
                await contact_handler.create(Contact.model_validate(updates))
                ui.notify("Контакт создан", type="positive")
            else:
                assert c.id is not None
                await contact_handler.update(c.id, updates)
                ui.notify("Сохранено", type="positive")
            ui.navigate.to("/app/graph")

        def back_to_graph() -> None:
            ui.navigate.to("/app/graph")

        async def archive() -> None:
            assert c.id is not None
            await deps.get_contact_handler().archive(c.id)
            ui.notify("Контакт архивирован", type="positive")
            ui.navigate.reload()

        async def unarchive() -> None:
            assert c.id is not None
            await deps.get_contact_handler().unarchive(c.id)
            ui.notify("Контакт восстановлен из архива", type="positive")
            ui.navigate.reload()

        def confirm_delete() -> None:
            assert c.id is not None
            with ui.dialog() as dialog, ui.card():
                ui.label(f"Удалить контакт «{c.name}» безвозвратно?").classes("text-lg")

                async def do_delete() -> None:
                    assert c.id is not None
                    await deps.get_contact_handler().delete(c.id, confirm=True)
                    ui.notify("Контакт удалён", type="positive")
                    dialog.close()
                    ui.navigate.to("/app/contacts")

                with ui.row().classes("justify-end w-full"):
                    ui.button("Отмена", on_click=dialog.close).props("flat")
                    ui.button("Удалить", on_click=do_delete).props("color=negative")
            dialog.open()

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Назад", on_click=back_to_graph).props("flat")
            if not is_new:
                if c.archived:
                    ui.button("Восстановить из архива", on_click=unarchive).props("flat")
                else:
                    ui.button("Архивировать", on_click=archive).props("flat")
                ui.button("Удалить", on_click=confirm_delete).props("flat color=negative")
            ui.button("Создать" if is_new else "Сохранить", on_click=save)


async def _render_dimension_links(contact_id: str) -> None:
    """One "attach existing / create new" picker per dimension type
    (Company/Event/Community/Project/Interest/Tag) — typing an existing
    name reuses that node (`NamedNodeRepository.get_or_create` MERGEs by
    name), typing a new one creates it."""
    link_handler = deps.get_link_handler()

    with ui.card().classes("w-full"):
        ui.label("Связи").classes("text-lg font-bold")
        section = ui.column().classes("w-full gap-3")

        async def refresh() -> None:
            section.clear()
            repos = deps.get_dimension_repos()
            links = await link_handler.list_dimension_links(contact_id)
            with section:
                for rel_type, repo in repos.items():
                    _dimension_type_row(contact_id, rel_type, repo, links, refresh)

        await refresh()


def _dimension_type_row(
    contact_id: str,
    rel_type: DimensionLinkType,
    repo: NamedNodeRepository,
    links: list[dict[str, Any]],
    refresh: Callable[[], Awaitable[None]],
) -> None:
    link_handler = deps.get_link_handler()
    attached = [link for link in links if link["rel_type"] == rel_type]
    ui.label(DIMENSION_TYPE_LABELS[rel_type]).classes("text-sm font-bold")
    with ui.row().classes("items-center gap-2 flex-wrap w-full"):
        for link in attached:

            async def detach(target_id: str = link["target_id"]) -> None:
                await link_handler.detach(contact_id, rel_type, target_id)
                await refresh()

            with ui.row().classes("items-center gap-1 border rounded px-2 py-0.5"):
                ui.label(link["target_name"])
                ui.button(icon="close", on_click=detach).props("flat dense size=xs")
        new_input = ui.input(placeholder="новое или существующее").props("dense").classes("w-48")

        async def add() -> None:
            name = new_input.value.strip()
            if not name:
                return
            node = await repo.get_or_create(name)
            assert node.id is not None
            await link_handler.attach(contact_id, rel_type, node.id)
            new_input.value = ""
            await refresh()

        ui.button(icon="add", on_click=add).props("flat dense size=xs")


async def _render_knows(contact_id: str) -> None:
    link_handler = deps.get_link_handler()
    contact_handler = deps.get_contact_handler()

    with ui.card().classes("w-full"):
        ui.label("Знакомства").classes("text-lg font-bold")
        section = ui.column().classes("w-full gap-1")

        async def refresh() -> None:
            section.clear()
            entries = await link_handler.list_knows(contact_id)
            with section:
                if not entries:
                    ui.label("Пока нет связей").classes("text-sm opacity-60")
                for entry in entries:
                    other: Contact = entry["contact"]
                    knows: Knows = entry["knows"]
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.link(other.name, f"/app/contacts/{other.id}")
                        meta = ", ".join(
                            p
                            for p in [
                                knows.type or "",
                                str(knows.date or ""),
                                str(knows.closeness or ""),
                            ]
                            if p
                        )
                        ui.label(meta).classes("text-xs opacity-60")

                        async def remove(other_id: str = other.id or "") -> None:
                            await link_handler.remove_knows(contact_id, other_id)
                            await refresh()

                        ui.button(icon="close", on_click=remove).props("flat dense size=xs")

        with ui.row().classes("items-end gap-2 w-full"):
            all_contacts = await contact_handler.list_contacts()
            options = {c.id: c.name for c in all_contacts if c.id != contact_id}
            other_select = ui.select(options, label="Контакт", with_input=True).classes("grow")
            type_input = ui.input("Тип").classes("grow")
            date_input = ui.input("Дата (ГГГГ-ММ-ДД)").classes("grow")
            closeness_input = ui.number("Близость", min=1, max=10, precision=0).classes("w-24")

            async def add_knows() -> None:
                if other_select.value is None:
                    ui.notify("Выберите контакт", type="negative")
                    return
                try:
                    knows_date = _parse_optional_date(date_input.value)
                except ValueError:
                    ui.notify("Некорректная дата", type="negative")
                    return
                knows = Knows(
                    type=type_input.value.strip() or None,
                    date=knows_date,
                    closeness=int(closeness_input.value) if closeness_input.value else None,
                )
                await link_handler.set_knows(contact_id, other_select.value, knows)
                await refresh()

            ui.button(icon="add", on_click=add_knows).props("flat dense")

        await refresh()


async def _render_relatives(contact_id: str) -> None:
    link_handler = deps.get_link_handler()

    with ui.card().classes("w-full"):
        ui.label("Родственники").classes("text-lg font-bold")
        section = ui.column().classes("w-full gap-1")

        async def refresh() -> None:
            section.clear()
            relatives = await link_handler.list_relatives(contact_id)
            with section:
                if not relatives:
                    ui.label("Пока нет данных").classes("text-sm opacity-60")
                for relative in relatives:
                    meta = " · ".join(
                        p for p in [relative.relation_type or "", str(relative.birthday or "")] if p
                    )
                    ui.label(f"{relative.name}" + (f" ({meta})" if meta else ""))

        with ui.row().classes("items-end gap-2 w-full"):
            name_input = ui.input("Имя").classes("grow")
            relation_input = ui.input("Кем приходится").classes("grow")
            birthday_input = ui.input("День рождения (ГГГГ-ММ-ДД)").classes("grow")

            async def add_relative() -> None:
                name = name_input.value.strip()
                if not name:
                    ui.notify("Имя обязательно", type="negative")
                    return
                try:
                    birthday = _parse_optional_date(birthday_input.value)
                except ValueError:
                    ui.notify("Некорректная дата", type="negative")
                    return
                relative = Relative(
                    name=name, relation_type=relation_input.value.strip() or None, birthday=birthday
                )
                await link_handler.add_relative(contact_id, relative)
                name_input.value = ""
                relation_input.value = ""
                birthday_input.value = ""
                await refresh()

            ui.button(icon="add", on_click=add_relative).props("flat dense")

        await refresh()


async def _render_interactions(contact_id: str) -> None:
    link_handler = deps.get_link_handler()

    with ui.card().classes("w-full"):
        ui.label("История взаимодействий").classes("text-lg font-bold")
        section = ui.column().classes("w-full gap-1")

        async def refresh() -> None:
            section.clear()
            interactions = await link_handler.list_interactions(contact_id)
            with section:
                if not interactions:
                    ui.label("Пока нет записей").classes("text-sm opacity-60")
                for interaction in interactions:
                    label = f"{INTERACTION_TYPE_LABELS[interaction.type]} — {interaction.date}"
                    if interaction.comment:
                        label += f": {interaction.comment}"
                    ui.label(label).classes("text-sm")

        with ui.row().classes("items-end gap-2 w-full"):
            type_select = ui.select(dict(INTERACTION_TYPE_LABELS), label="Тип").classes("grow")
            date_input = ui.input("Дата (ГГГГ-ММ-ДД)", value=date.today().isoformat()).classes(
                "grow"
            )
            comment_input = ui.input("Комментарий").classes("grow")

            async def add_interaction() -> None:
                if type_select.value is None:
                    ui.notify("Выберите тип", type="negative")
                    return
                try:
                    interaction_date = _parse_optional_date(date_input.value)
                except ValueError:
                    interaction_date = None
                if interaction_date is None:
                    ui.notify("Некорректная дата", type="negative")
                    return
                interaction = Interaction(
                    type=type_select.value,
                    date=interaction_date,
                    comment=comment_input.value.strip() or None,
                )
                await link_handler.add_interaction(contact_id, interaction)
                comment_input.value = ""
                await refresh()

            ui.button(icon="add", on_click=add_interaction).props("flat dense")

        await refresh()


async def _render_actions(contact_id: str) -> None:
    link_handler = deps.get_link_handler()
    contact_handler = deps.get_contact_handler()

    with ui.card().classes("w-full"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.label("Действия").classes("text-lg font-bold")

            async def open_quick_dialog() -> None:
                contact = await contact_handler.get(contact_id)
                assign_action_dialog(contact_id, contact.name, refresh)

            ui.button("Назначить действие", on_click=open_quick_dialog).props("flat dense")

        section = ui.column().classes("w-full gap-1")

        async def refresh() -> None:
            section.clear()
            actions = await link_handler.list_actions(contact_id)
            with section:
                if not actions:
                    ui.label("Пока нет действий").classes("text-sm opacity-60")
                for action in actions:
                    with ui.row().classes("items-center justify-between w-full"):
                        status = "выполнено" if action.completed else "в работе"
                        ui.label(
                            f"{ACTION_TYPE_LABELS[action.type]} — срок {action.due_date} ({status})"
                        ).classes("text-sm")
                        if not action.completed:
                            action_id = action.id

                            async def complete(action_id: str | None = action_id) -> None:
                                if action_id is None:
                                    return
                                await link_handler.complete_action(action_id)
                                await refresh()

                            ui.button("Готово", on_click=complete).props("flat dense size=xs")

        await refresh()
