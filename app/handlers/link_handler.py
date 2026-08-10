"""Business logic for everything in app.repositories.link_repository."""

from __future__ import annotations

from datetime import date
from typing import Any

from loguru import logger

from app.models.action import Action
from app.models.enums import DimensionLinkType
from app.models.interaction import Interaction
from app.models.relationships import Knows
from app.models.relative import Relative
from app.repositories.link_repository import LinkRepository


class LinkHandler:
    def __init__(self, repo: LinkRepository) -> None:
        self._repo = repo

    async def attach(self, contact_id: str, rel_type: DimensionLinkType, target_id: str) -> None:
        await self._repo.attach(contact_id, rel_type, target_id)
        logger.info("Linked contact {} -[{}]-> {}", contact_id, rel_type, target_id)

    async def detach(self, contact_id: str, rel_type: DimensionLinkType, target_id: str) -> bool:
        removed = await self._repo.detach(contact_id, rel_type, target_id)
        if removed:
            logger.info("Unlinked contact {} -[{}]-> {}", contact_id, rel_type, target_id)
        else:
            logger.warning("Nothing to unlink for {} -[{}]-> {}", contact_id, rel_type, target_id)
        return removed

    async def set_knows(self, from_id: str, to_id: str, knows: Knows) -> Knows:
        result = await self._repo.set_knows(from_id, to_id, knows)
        logger.info("Set KNOWS {} -> {}", from_id, to_id)
        return result

    async def remove_knows(self, from_id: str, to_id: str) -> bool:
        return await self._repo.remove_knows(from_id, to_id)

    async def add_interaction(self, contact_id: str, interaction: Interaction) -> Interaction:
        created = await self._repo.add_interaction(contact_id, interaction)
        logger.info("Logged {} interaction for contact {}", interaction.type, contact_id)
        return created

    async def list_interactions(self, contact_id: str) -> list[Interaction]:
        return await self._repo.list_interactions(contact_id)

    async def last_interaction_context(self, contact_id: str) -> Interaction | None:
        """Backs the CLI "context of the last meeting" scenario (item 5)."""
        last = await self._repo.last_interaction(contact_id)
        if last is None:
            logger.debug("No prior interaction for contact {}", contact_id)
        return last

    async def add_action(self, contact_id: str, action: Action) -> Action:
        created = await self._repo.add_action(contact_id, action)
        logger.info("Scheduled {} action for contact {}", action.type, contact_id)
        return created

    async def list_due_actions(self, *, before: date, include_completed: bool = False):
        return await self._repo.list_due_actions(before=before, include_completed=include_completed)

    async def list_actions(self, contact_id: str) -> list[Action]:
        return await self._repo.list_actions(contact_id)

    async def complete_action(self, action_id: str) -> Action:
        completed = await self._repo.complete_action(action_id)
        if completed is None:
            logger.warning("Complete-action failed — action {} not found", action_id)
            raise ValueError(f"Action {action_id} not found")
        logger.info("Completed action {}", action_id)
        return completed

    async def add_relative(self, contact_id: str, relative: Relative) -> Relative:
        created = await self._repo.add_relative(contact_id, relative)
        logger.info("Added relative {} for contact {}", relative.name, contact_id)
        return created

    async def list_relatives(self, contact_id: str) -> list[Relative]:
        return await self._repo.list_relatives(contact_id)

    async def list_knows(self, contact_id: str) -> list[dict[str, Any]]:
        return await self._repo.list_knows(contact_id)

    async def list_dimension_links(self, contact_id: str) -> list[dict[str, Any]]:
        return await self._repo.list_dimension_links(contact_id)

    async def upcoming_birthdays(self, *, within_days: int = 30):
        birthdays = await self._repo.upcoming_birthdays(within_days=within_days)
        logger.debug("Found {} upcoming birthday(s) within {} days", len(birthdays), within_days)
        return birthdays
