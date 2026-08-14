"""`/contacts` — CRUD, archiving, and the "stale contacts" list."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_contact_handler
from app.handlers.contact_handler import (
    ContactHandler,
    ContactNotFoundError,
    DeleteNotConfirmedError,
)
from app.models.contact import Contact, ContactUpdate
from app.models.enums import Circle, ContactType

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post("", response_model=Contact, status_code=status.HTTP_201_CREATED)
async def create_contact(
    contact: Contact, handler: ContactHandler = Depends(get_contact_handler)
) -> Contact:
    return await handler.create(contact)


@router.get("", response_model=list[Contact])
async def list_contacts(
    circle: Circle | None = None,
    contact_type: ContactType | None = None,
    archived: bool = False,
    handler: ContactHandler = Depends(get_contact_handler),
) -> list[Contact]:
    return await handler.list_contacts(circle=circle, contact_type=contact_type, archived=archived)


@router.get("/stale")
async def list_stale_contacts(
    threshold_days: int | None = Query(default=None, ge=1),
    handler: ContactHandler = Depends(get_contact_handler),
) -> list[dict]:
    return await handler.list_stale(threshold_days=threshold_days)


@router.get("/{contact_id}", response_model=Contact)
async def get_contact(
    contact_id: str, handler: ContactHandler = Depends(get_contact_handler)
) -> Contact:
    try:
        return await handler.get(contact_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found") from exc


@router.patch("/{contact_id}", response_model=Contact)
async def update_contact(
    contact_id: str,
    updates: ContactUpdate,
    handler: ContactHandler = Depends(get_contact_handler),
) -> Contact:
    try:
        return await handler.update(contact_id, updates.model_dump(exclude_none=True))
    except ContactNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found") from exc


@router.post("/{contact_id}/archive", response_model=Contact)
async def archive_contact(
    contact_id: str, handler: ContactHandler = Depends(get_contact_handler)
) -> Contact:
    try:
        return await handler.archive(contact_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found") from exc


@router.post("/{contact_id}/unarchive", response_model=Contact)
async def unarchive_contact(
    contact_id: str, handler: ContactHandler = Depends(get_contact_handler)
) -> Contact:
    try:
        return await handler.unarchive(contact_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found") from exc


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: str,
    confirm: bool = False,
    handler: ContactHandler = Depends(get_contact_handler),
) -> None:
    """Hard delete — spec: only ever after explicit user confirmation.
    `confirm=true` must be passed deliberately; the UI's delete modal
    (stage 6) is what actually asks the user."""
    try:
        await handler.delete(contact_id, confirm=confirm)
    except DeleteNotConfirmedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Deletion requires confirm=true") from exc
    except ContactNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found") from exc
