"""Stage 6: NiceGUI dashboard + contact CRUD; stage 7: the graph screen.
Mounted into the same FastAPI process as the REST API (see `app/ui/deps.py`
for why, and how pages reach the database).
"""

from __future__ import annotations

from fastapi import FastAPI
from nicegui import ui

from app.ui import deps


def mount(app: FastAPI) -> None:
    """Called once from `app.main`'s module body, after the REST routers
    are registered. Import order matters here: the page modules register
    their routes as an import side effect (`@ui.page(...)`), so they must
    be imported before `ui.run_with` — and in practice before the server
    starts accepting connections, which happens well after this call
    returns anyway."""
    deps.bind(app)

    from app.ui.pages import (  # noqa: F401
        contact_detail,
        contacts,
        dashboard,
        duplicates,
        graph,
        import_export,
        settings,
    )

    ui.run_with(app, title="networking4j", show_welcome_message=False)
