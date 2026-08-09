"""FastAPI dependency wiring: Request -> driver -> repositories -> handlers.

Every handler is built fresh per request from `request.app.state.neo4j_driver`
(set once in the lifespan hook, app/main.py) — repositories are cheap,
stateless wrappers around the shared driver, so there's no pooling concern.
"""

from __future__ import annotations

from fastapi import Request
from neo4j import AsyncDriver

from app.handlers.contact_handler import ContactHandler
from app.handlers.goal_handler import GoalHandler
from app.handlers.link_handler import LinkHandler
from app.handlers.search_handler import SearchHandler
from app.handlers.settings_handler import SettingsHandler
from app.repositories.contact_repository import ContactRepository
from app.repositories.goal_repository import MonthlyGoalRepository, NetworkingGoalRepository
from app.repositories.link_repository import LinkRepository
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
