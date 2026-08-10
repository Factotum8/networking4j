"""`/app/settings` — user-configurable settings page (stage 6, step F):
`stale_contact_days` (item 6: "haven't been in touch" threshold) and
`dedup_score_threshold` (stage 3: duplicate-detection sensitivity).
"""

from __future__ import annotations

from nicegui import ui

from app.ui import deps, layout


@ui.page("/app/settings")
async def settings_page() -> None:
    with layout.shell("Настройки"):
        handler = deps.get_settings_handler()
        settings = await handler.get()

        with ui.card().classes("w-full"):
            ui.label("Настройки").classes("text-lg font-bold")
            stale_input = ui.number(
                "Порог «давно не общались» (дней)",
                value=settings.stale_contact_days,
                min=1,
                precision=0,
            ).classes("w-full")
            dedup_input = ui.number(
                "Порог схожести для дубликатов (0-100)",
                value=settings.dedup_score_threshold,
                min=0,
                max=100,
            ).classes("w-full")

            async def save() -> None:
                if not stale_input.value or stale_input.value < 1:
                    ui.notify("Порог должен быть не меньше 1 дня", type="negative")
                    return
                if dedup_input.value is None or not (0 <= dedup_input.value <= 100):
                    ui.notify("Порог схожести должен быть от 0 до 100", type="negative")
                    return
                await handler.update(
                    {
                        "stale_contact_days": int(stale_input.value),
                        "dedup_score_threshold": float(dedup_input.value),
                    }
                )
                ui.notify("Настройки сохранены", type="positive")

            ui.button("Сохранить", on_click=save)
