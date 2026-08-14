"""Handler wiring for the NiceGUI pages — the UI-side counterpart to
`app.api.deps`.

The two architectural decisions behind this module (confirmed with the
user before stage 6 was written): NiceGUI is mounted into the *same*
FastAPI process as the REST API (`ui.run_with(app)`, see `app/ui/__init__.
py`), and pages call handlers directly, in-process — no HTTP round trip
through the REST layer the way the CLI does.

`ui.run_with(app)` mounts NiceGUI's routes as a Starlette *sub-application*
(`nicegui.core.app`, mounted onto our `app`). A request routed to a mounted
sub-app sees the sub-app as `request.app`, not our own `FastAPI` instance —
so `request.app.state.neo4j_driver` (the pattern `app.api.deps` uses) isn't
reachable from a `@ui.page` function. Instead, `bind()` captures our own
`app` object directly at mount time (`app/ui/__init__.py::mount`), and every
handler factory below reads `app.state.neo4j_driver` off that captured
reference — sidestepping the sub-app ambiguity entirely rather than relying
on it going one way or the other.
"""

from __future__ import annotations

from fastapi import FastAPI
from neo4j import AsyncDriver

from app.handlers.contact_handler import ContactHandler
from app.handlers.goal_handler import GoalHandler
from app.handlers.graph_handler import GraphHandler
from app.handlers.import_export_handler import ImportExportHandler
from app.handlers.link_handler import LinkHandler
from app.handlers.reminder_handler import ReminderHandler
from app.handlers.search_handler import SearchHandler
from app.handlers.settings_handler import SettingsHandler
from app.models.base import GraphNode
from app.models.dimensions import Community, Company, Event, Interest, Project, Tag
from app.models.enums import DimensionLinkType
from app.repositories.contact_repository import ContactRepository
from app.repositories.goal_repository import MonthlyGoalRepository, NetworkingGoalRepository
from app.repositories.graph_repository import GraphRepository
from app.repositories.link_repository import LinkRepository
from app.repositories.named_node_repository import NamedNodeRepository
from app.repositories.settings_repository import SettingsRepository

# One (label, model) pair per DimensionLinkType — the UI-side counterpart to
# LinkRepository's private `_TARGET_LABELS`, needed here too since the
# contact detail page builds a `NamedNodeRepository` per dimension type to
# offer "attach existing / create new" pickers.
_DIMENSION_TYPES: dict[DimensionLinkType, tuple[str, type[GraphNode]]] = {
    DimensionLinkType.WORKS_AT: ("Company", Company),
    DimensionLinkType.ATTENDED: ("Event", Event),
    DimensionLinkType.MEMBER_OF: ("Community", Community),
    DimensionLinkType.INVOLVED_IN: ("Project", Project),
    DimensionLinkType.INTERESTED_IN: ("Interest", Interest),
    DimensionLinkType.TAGGED: ("Tag", Tag),
}

_app: FastAPI | None = None


def bind(app: FastAPI) -> None:
    """Called once from `app.ui.mount` before any page is served."""
    global _app
    _app = app


def get_driver() -> AsyncDriver:
    if _app is None:
        raise RuntimeError("app.ui.deps.bind() must be called before any UI page is served")
    return _app.state.neo4j_driver


def get_contact_handler() -> ContactHandler:
    driver = get_driver()
    return ContactHandler(ContactRepository(driver), SettingsRepository(driver))


def get_link_handler() -> LinkHandler:
    return LinkHandler(LinkRepository(get_driver()))


def get_goal_handler() -> GoalHandler:
    driver = get_driver()
    return GoalHandler(NetworkingGoalRepository(driver), MonthlyGoalRepository(driver))


def get_settings_handler() -> SettingsHandler:
    return SettingsHandler(SettingsRepository(get_driver()))


def get_search_handler() -> SearchHandler:
    driver = get_driver()
    return SearchHandler(ContactRepository(driver), SettingsRepository(driver))


def get_reminder_handler() -> ReminderHandler:
    driver = get_driver()
    return ReminderHandler(
        ContactRepository(driver), LinkRepository(driver), SettingsRepository(driver)
    )


def get_import_export_handler() -> ImportExportHandler:
    driver = get_driver()
    return ImportExportHandler(
        ContactRepository(driver),
        LinkRepository(driver),
        NamedNodeRepository(driver, "Company", Company),
        NamedNodeRepository(driver, "Tag", Tag),
        NamedNodeRepository(driver, "Interest", Interest),
    )


def get_graph_handler() -> GraphHandler:
    return GraphHandler(GraphRepository(get_driver()))


def get_dimension_repos() -> dict[DimensionLinkType, NamedNodeRepository]:
    """One `NamedNodeRepository` per dimension-link type, keyed by the link
    type itself — what the contact detail page's "attach existing / create
    new" pickers need for all six dimension kinds at once."""
    driver = get_driver()
    return {
        rel_type: NamedNodeRepository(driver, label, model)
        for rel_type, (label, model) in _DIMENSION_TYPES.items()
    }
