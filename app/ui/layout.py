"""Shared page shell — a header with navigation, reused by every page so
the app doesn't have to be re-skinned six times.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from nicegui import ui

# Every UI page except the dashboard lives under /app/... — the REST API
# already owns the bare top-level namespace (/contacts, /settings, /goals,
# /reminders, /actions, /search, plus the six dimension routers), and since
# both are mounted on the same FastAPI app (see app/ui/__init__.py), a
# same-path @ui.page would silently lose to the REST route registered
# first. Discovered by curling every page after wiring it up — not a
# design choice, a routing necessity.
_NAV_LINKS: list[tuple[str, str]] = [
    ("Дашборд", "/"),
    ("Контакты", "/app/contacts"),
    ("Граф", "/app/graph"),
    ("Дубликаты", "/app/duplicates"),
    ("Импорт/экспорт", "/app/import-export"),
    ("Настройки", "/app/settings"),
]


@contextmanager
def shell(title: str, *, wide: bool = False) -> Iterator[None]:
    """Wrap a page's content in the shared header/nav. Usage::

        @ui.page("/")
        async def dashboard_page() -> None:
            with layout.shell("Дашборд"):
                ui.label("...")

    :param wide: use the full viewport width instead of the usual
        centered `max-w-5xl` column — the graph screen needs the room.
    """
    with ui.header().classes("items-center justify-between"):
        ui.label("networking4j").classes("text-lg font-bold")
        with ui.row().classes("gap-4"):
            for label, path in _NAV_LINKS:
                ui.link(label, path).classes("text-white")
        ui.label(title).classes("text-sm opacity-75")
    container_classes = "w-full p-4 gap-4" if wide else "w-full max-w-5xl mx-auto p-4 gap-4"
    with ui.column().classes(container_classes):
        yield
