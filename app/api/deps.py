"""FastAPI dependency wiring: Request -> driver -> repositories -> handlers.

Every handler is built fresh per request from `request.app.state.neo4j_driver`
(set once in the lifespan hook, app/main.py) — repositories are cheap,
stateless wrappers around the shared driver, so there's no pooling concern.
"""

from __future__ import annotations

from fastapi import Request
from neo4j import AsyncDriver

from app.config import settings
from app.handlers.ai_handler import AiHandler
from app.handlers.contact_handler import ContactHandler
from app.handlers.goal_handler import GoalHandler
from app.handlers.import_export_handler import ImportExportHandler
from app.handlers.link_handler import LinkHandler
from app.handlers.reminder_handler import ReminderHandler
from app.handlers.search_handler import SearchHandler
from app.handlers.settings_handler import SettingsHandler
from app.models.dimensions import Company, Interest, Tag
from app.providers.factory import build_llm_provider
from app.repositories.contact_repository import ContactRepository
from app.repositories.goal_repository import MonthlyGoalRepository, NetworkingGoalRepository
from app.repositories.link_repository import LinkRepository
from app.repositories.named_node_repository import NamedNodeRepository
from app.repositories.settings_repository import SettingsRepository


def get_driver(request: Request) -> AsyncDriver:
    return request.app.state.neo4j_driver


def get_contact_handler(request: Request) -> ContactHandler:
    driver = get_driver(request)
    return ContactHandler(ContactRepository(driver), SettingsRepository(driver))


def get_link_handler(request: Request) -> LinkHandler:
    return LinkHandler(LinkRepository(get_driver(request)))


def get_goal_handler(request: Request) -> GoalHandler:
    driver = get_driver(request)
    return GoalHandler(NetworkingGoalRepository(driver), MonthlyGoalRepository(driver))


def get_settings_handler(request: Request) -> SettingsHandler:
    return SettingsHandler(SettingsRepository(get_driver(request)))


def get_search_handler(request: Request) -> SearchHandler:
    driver = get_driver(request)
    return SearchHandler(ContactRepository(driver), SettingsRepository(driver))


def get_reminder_handler(request: Request) -> ReminderHandler:
    driver = get_driver(request)
    return ReminderHandler(
        ContactRepository(driver), LinkRepository(driver), SettingsRepository(driver)
    )


def get_ai_handler(request: Request) -> AiHandler:
    """Raises `LLMProviderUnavailableError` (-> 500, see app/main.py) if the
    configured provider's API key is missing — no fallback to the other
    provider, per the user's stage-8 decision."""
    driver = get_driver(request)
    llm = build_llm_provider(settings)
    return AiHandler(
        llm, ContactRepository(driver), LinkRepository(driver), SettingsRepository(driver)
    )


def get_import_export_handler(request: Request) -> ImportExportHandler:
    driver = get_driver(request)
    return ImportExportHandler(
        ContactRepository(driver),
        LinkRepository(driver),
        NamedNodeRepository(driver, "Company", Company),
        NamedNodeRepository(driver, "Tag", Tag),
        NamedNodeRepository(driver, "Interest", Interest),
    )
