"""Business logic for stage 4: CSV/Excel/vCard import and export.

Parsing/serialization itself is pure (`app.services.contact_io`) — this
handler is just the DB-talking glue: bulk-create the parsed contacts, then
link each one to its company/tags/interests dimension nodes.
"""

from __future__ import annotations

from loguru import logger

from app.models.dimensions import Company, Interest, Tag
from app.models.enums import DimensionLinkType
from app.models.import_result import ContactImportRow, ImportRowError, ImportSummary
from app.repositories.contact_repository import ContactRepository
from app.repositories.link_repository import LinkRepository
from app.repositories.named_node_repository import NamedNodeRepository
from app.services.contact_io import contacts_to_csv, contacts_to_vcard, parse_csv, parse_vcard


class ImportExportHandler:
    def __init__(
        self,
        contact_repo: ContactRepository,
        link_repo: LinkRepository,
        company_repo: NamedNodeRepository[Company],
        tag_repo: NamedNodeRepository[Tag],
        interest_repo: NamedNodeRepository[Interest],
    ) -> None:
        self._contact_repo = contact_repo
        self._link_repo = link_repo
        self._company_repo = company_repo
        self._tag_repo = tag_repo
        self._interest_repo = interest_repo

    async def import_csv(self, filename: str, data: bytes) -> ImportSummary:
        rows, errors = parse_csv(filename, data)
        logger.debug(
            "Parsed CSV/Excel import {!r}: {} row(s), {} error(s)", filename, len(rows), len(errors)
        )
        return await self._import_rows(rows, errors)

    async def import_vcard(self, data: bytes) -> ImportSummary:
        rows, errors = parse_vcard(data)
        logger.debug("Parsed vCard import: {} card(s), {} error(s)", len(rows), len(errors))
        return await self._import_rows(rows, errors)

    async def _import_rows(
        self, rows: list[ContactImportRow], errors: list[ImportRowError]
    ) -> ImportSummary:
        if not rows:
            logger.warning("Import produced 0 valid row(s), {} error(s)", len(errors))
            return ImportSummary(created=0, errors=errors)

        created = await self._contact_repo.bulk_create([row.contact for row in rows])
        for contact, row in zip(created, rows, strict=True):
            assert contact.id is not None  # just created, always has an id
            for name in row.companies:
                company = await self._company_repo.get_or_create(name)
                assert company.id is not None
                await self._link_repo.attach(contact.id, DimensionLinkType.WORKS_AT, company.id)
            for name in row.tags:
                tag = await self._tag_repo.get_or_create(name)
                assert tag.id is not None
                await self._link_repo.attach(contact.id, DimensionLinkType.TAGGED, tag.id)
            for name in row.interests:
                interest = await self._interest_repo.get_or_create(name)
                assert interest.id is not None
                await self._link_repo.attach(
                    contact.id, DimensionLinkType.INTERESTED_IN, interest.id
                )

        logger.info("Imported {} contact(s), {} error(s)", len(created), len(errors))
        return ImportSummary(created=len(created), errors=errors)

    async def export_csv(self, *, include_archived: bool) -> bytes:
        contacts = await self._contact_repo.list_contacts(archived=False)
        if include_archived:
            contacts += await self._contact_repo.list_contacts(archived=True)
        logger.info(
            "Exporting {} contact(s) to CSV (include_archived={})", len(contacts), include_archived
        )
        return contacts_to_csv(contacts)

    async def export_vcard(self, *, include_archived: bool) -> bytes:
        contacts = await self._contact_repo.list_contacts(archived=False)
        if include_archived:
            contacts += await self._contact_repo.list_contacts(archived=True)
        logger.info(
            "Exporting {} contact(s) to vCard (include_archived={})",
            len(contacts),
            include_archived,
        )
        return contacts_to_vcard(contacts)
