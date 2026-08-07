"""Business logic between the contacts API and ContactRepository/LinkRepository.

Per AGENTS.md code-review guidelines: every return and every branch that
carries a decision gets logged with context.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.models.contact import Contact
from app.repositories.contact_repository import ContactRepository
from app.repositories.settings_repository import SettingsRepository


class ContactNotFoundError(Exception):
    pass


class DeleteNotConfirmedError(Exception):
    pass


class ContactHandler:
    def __init__(self, repo: ContactRepository, settings_repo: SettingsRepository) -> None:
        self._repo = repo
        self._settings_repo = settings_repo

    async def create(self, contact: Contact) -> Contact:
        created = await self._repo.create(contact)
        logger.info("Created contact {} ({})", created.id, created.name)
        return created

    async def get(self, contact_id: str) -> Contact:
        contact = await self._repo.get(contact_id)
        if contact is None:
            logger.warning("Contact {} not found", contact_id)
            raise ContactNotFoundError(contact_id)
        logger.debug("Fetched contact {}", contact_id)
        return contact

    async def list_contacts(self, **filters: Any) -> list[Contact]:
        contacts = await self._repo.list_contacts(**filters)
        logger.debug("Listed {} contact(s) with filters {}", len(contacts), filters)
        return contacts

    async def update(self, contact_id: str, updates: dict[str, Any]) -> Contact:
        updated = await self._repo.update(contact_id, updates)
        if updated is None:
            logger.warning("Update failed — contact {} not found", contact_id)
            raise ContactNotFoundError(contact_id)
        logger.info("Updated contact {}: {}", contact_id, list(updates))
        return updated

    async def archive(self, contact_id: str) -> Contact:
        archived = await self._repo.archive(contact_id)
        if archived is None:
            logger.warning("Archive failed — contact {} not found", contact_id)
            raise ContactNotFoundError(contact_id)
        logger.info("Archived contact {}", contact_id)
        return archived

    async def unarchive(self, contact_id: str) -> Contact:
        restored = await self._repo.unarchive(contact_id)
        if restored is None:
            logger.warning("Unarchive failed — contact {} not found", contact_id)
            raise ContactNotFoundError(contact_id)
        logger.info("Unarchived contact {}", contact_id)
        return restored

    async def delete(self, contact_id: str, *, confirm: bool) -> None:
        """Hard delete — spec requires explicit user confirmation first."""
        if not confirm:
            logger.warning("Delete rejected for contact {} — confirm=False", contact_id)
            raise DeleteNotConfirmedError(contact_id)
        deleted = await self._repo.delete(contact_id)
        if not deleted:
            logger.warning("Delete failed — contact {} not found", contact_id)
            raise ContactNotFoundError(contact_id)
        logger.info("Deleted contact {} (confirmed)", contact_id)

    async def list_stale(self, *, threshold_days: int | None = None) -> list[dict[str, Any]]:
        if threshold_days is None:
            settings = await self._settings_repo.get()
            threshold_days = settings.stale_contact_days
            logger.debug("Using configured stale threshold: {} days", threshold_days)
        else:
            logger.debug("Using override stale threshold: {} days", threshold_days)
        stale = await self._repo.list_stale(threshold_days=threshold_days)
        logger.info("Found {} stale contact(s) (>= {} days)", len(stale), threshold_days)
        return stale
