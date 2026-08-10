"""`/app/duplicates` — duplicate-candidate review page (stage 6, step G).

Detection only, per the stage-3 scope decision (see
`app.models.duplicate.DuplicateCandidate`): there's no merge action here,
just a quick "archive one side of the pair" shortcut into the existing
archive endpoint.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from nicegui import ui

from app.handlers.contact_handler import ContactHandler
from app.models.duplicate import DuplicateCandidate
from app.ui import deps, layout


@ui.page("/app/duplicates")
async def duplicates_page() -> None:
    with layout.shell("Дубликаты"):
        search_handler = deps.get_search_handler()
        contact_handler = deps.get_contact_handler()

        with ui.row().classes("items-end gap-2 w-full"):
            threshold_input = ui.number("Порог схожести (0-100)", min=0, max=100).classes("grow")
            results = ui.column().classes("w-full gap-2")

            async def refresh() -> None:
                results.clear()
                threshold = float(threshold_input.value) if threshold_input.value else None
                candidates = await search_handler.find_duplicates(threshold=threshold)
                with results:
                    if not candidates:
                        ui.label("Дубликаты не найдены").classes("text-sm opacity-60")
                    for candidate in candidates:
                        _candidate_row(candidate, contact_handler, refresh)

            ui.button("Обновить", on_click=refresh).props("flat")

        await refresh()


def _candidate_row(
    candidate: DuplicateCandidate,
    contact_handler: ContactHandler,
    refresh: Callable[[], Awaitable[None]],
) -> None:
    a, b = candidate.contact_a, candidate.contact_b
    with ui.card().classes("w-full"):
        ui.label(f"{a.name} ↔ {b.name}").classes("text-base font-bold")
        ui.label(
            f"Совпадение: {candidate.score:.0f} ({', '.join(candidate.matched_on)})"
        ).classes("text-xs opacity-60")
        with ui.row().classes("gap-2"):
            for contact in (a, b):

                async def archive(
                    contact_id: str = contact.id or "", contact_name: str = contact.name
                ) -> None:
                    await contact_handler.archive(contact_id)
                    ui.notify(f"{contact_name} архивирован", type="positive")
                    await refresh()

                ui.link(contact.name, f"/app/contacts/{contact.id}")
                ui.button(f"Архивировать «{contact.name}»", on_click=archive).props(
                    "flat dense size=sm"
                )
