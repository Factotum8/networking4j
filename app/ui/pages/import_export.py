"""`/app/import-export` — CSV/Excel/vCard import, export, and an on-demand
full-graph backup trigger (stage 6, step H).
"""

from __future__ import annotations

from nicegui import ui
from nicegui.events import UploadEventArguments

from app.models.import_result import ImportSummary
from app.services.backup_export import build_backup, write_backup_files
from app.ui import deps, layout


@ui.page("/app/import-export")
async def import_export_page() -> None:
    with layout.shell("Импорт/экспорт"):
        _render_import_section()
        _render_export_section()
        _render_backup_section()


def _render_import_section() -> None:
    with ui.card().classes("w-full"):
        ui.label("Импорт").classes("text-lg font-bold")
        result_area = ui.column().classes("w-full gap-1")

        def show_summary(summary: ImportSummary) -> None:
            result_area.clear()
            with result_area:
                ui.label(f"Создано контактов: {summary.created}").classes("text-sm")
                if summary.errors:
                    ui.label(f"Ошибок: {len(summary.errors)}").classes("text-sm text-orange-600")
                    for error in summary.errors:
                        ui.label(f"Строка {error.row}: {error.message}").classes(
                            "text-xs opacity-60"
                        )

        async def handle_csv_upload(e: UploadEventArguments) -> None:
            data = await e.file.read()
            handler = deps.get_import_export_handler()
            summary = await handler.import_csv(e.file.name, data)
            show_summary(summary)

        async def handle_vcard_upload(e: UploadEventArguments) -> None:
            data = await e.file.read()
            handler = deps.get_import_export_handler()
            summary = await handler.import_vcard(data)
            show_summary(summary)

        with ui.row().classes("gap-6"):
            with ui.column():
                ui.label("CSV / Excel").classes("text-sm font-bold")
                ui.upload(on_upload=handle_csv_upload, auto_upload=True).classes("max-w-xs")
            with ui.column():
                ui.label("vCard").classes("text-sm font-bold")
                ui.upload(on_upload=handle_vcard_upload, auto_upload=True).classes("max-w-xs")


def _render_export_section() -> None:
    with ui.card().classes("w-full"):
        ui.label("Экспорт").classes("text-lg font-bold")
        include_archived = ui.switch("Включать архивные")

        async def export_csv() -> None:
            handler = deps.get_import_export_handler()
            data = await handler.export_csv(include_archived=include_archived.value)
            ui.download.content(data, "contacts.csv", media_type="text/csv")

        async def export_vcard() -> None:
            handler = deps.get_import_export_handler()
            data = await handler.export_vcard(include_archived=include_archived.value)
            ui.download.content(data, "contacts.vcf", media_type="text/vcard")

        with ui.row().classes("gap-2"):
            ui.button("Экспорт CSV", on_click=export_csv).props("flat")
            ui.button("Экспорт vCard", on_click=export_vcard).props("flat")


def _render_backup_section() -> None:
    with ui.card().classes("w-full"):
        ui.label("Резервная копия").classes("text-lg font-bold")
        ui.label(
            "Полный снимок графа (JSON) + CSV контактов, отдельно от "
            "бинарного neo4j-admin dump (см. Makefile)."
        ).classes("text-xs opacity-60")
        result_label = ui.label()

        async def run_backup() -> None:
            driver = deps.get_driver()
            backup = await build_backup(driver)
            json_path, csv_path = write_backup_files(backup)
            result_label.text = f"Сохранено: {json_path.name}, {csv_path.name}"
            ui.notify("Бэкап создан", type="positive")

        ui.button("Сделать бэкап сейчас", on_click=run_backup).props("flat")
