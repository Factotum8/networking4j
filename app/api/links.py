"""Everything relationship-shaped: dimension links, KNOWS, interactions,
actions, relatives, and the cross-contact "due actions"/"birthdays" views
that back the dashboard and the CLI (item 5).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_link_handler
from app.handlers.link_handler import LinkHandler
from app.models.action import Action
from app.models.enums import DimensionLinkType
from app.models.interaction import Interaction
from app.models.relationships import Knows
from app.models.relative import Relative

contact_links_router = APIRouter(prefix="/contacts/{contact_id}", tags=["links"])


@contact_links_router.put("/links/{rel_type}/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def attach_link(
    contact_id: str,
    rel_type: DimensionLinkType,
    target_id: str,
    handler: LinkHandler = Depends(get_link_handler),
) -> None:
    await handler.attach(contact_id, rel_type, target_id)


@contact_links_router.delete(
    "/links/{rel_type}/{target_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def detach_link(
    contact_id: str,
    rel_type: DimensionLinkType,
    target_id: str,
    handler: LinkHandler = Depends(get_link_handler),
) -> None:
    removed = await handler.detach(contact_id, rel_type, target_id)
    if not removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")


@contact_links_router.put("/knows/{other_contact_id}", response_model=Knows)
async def set_knows(
    contact_id: str,
    other_contact_id: str,
    knows: Knows,
    handler: LinkHandler = Depends(get_link_handler),
) -> Knows:
    return await handler.set_knows(contact_id, other_contact_id, knows)


@contact_links_router.delete("/knows/{other_contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_knows(
    contact_id: str, other_contact_id: str, handler: LinkHandler = Depends(get_link_handler)
) -> None:
    removed = await handler.remove_knows(contact_id, other_contact_id)
    if not removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "KNOWS relationship not found")


@contact_links_router.post(
    "/interactions", response_model=Interaction, status_code=status.HTTP_201_CREATED
)
async def add_interaction(
    contact_id: str, interaction: Interaction, handler: LinkHandler = Depends(get_link_handler)
) -> Interaction:
    return await handler.add_interaction(contact_id, interaction)


@contact_links_router.get("/interactions", response_model=list[Interaction])
async def list_interactions(
    contact_id: str, handler: LinkHandler = Depends(get_link_handler)
) -> list[Interaction]:
    return await handler.list_interactions(contact_id)


@contact_links_router.get("/interactions/last", response_model=Interaction | None)
async def last_interaction(
    contact_id: str, handler: LinkHandler = Depends(get_link_handler)
) -> Interaction | None:
    """Backs the CLI "context of the last meeting" scenario (item 5)."""
    return await handler.last_interaction_context(contact_id)


@contact_links_router.post("/actions", response_model=Action, status_code=status.HTTP_201_CREATED)
async def add_action(
    contact_id: str, action: Action, handler: LinkHandler = Depends(get_link_handler)
) -> Action:
    return await handler.add_action(contact_id, action)


@contact_links_router.post(
    "/relatives", response_model=Relative, status_code=status.HTTP_201_CREATED
)
async def add_relative(
    contact_id: str, relative: Relative, handler: LinkHandler = Depends(get_link_handler)
) -> Relative:
    return await handler.add_relative(contact_id, relative)


@contact_links_router.get("/relatives", response_model=list[Relative])
async def list_relatives(
    contact_id: str, handler: LinkHandler = Depends(get_link_handler)
) -> list[Relative]:
    return await handler.list_relatives(contact_id)


@contact_links_router.get("/actions", response_model=list[Action])
async def list_actions(
    contact_id: str, handler: LinkHandler = Depends(get_link_handler)
) -> list[Action]:
    """This contact's full action history — see `/actions/due` (below) for
    the cross-contact, due-only view the reminders job uses."""
    return await handler.list_actions(contact_id)


@contact_links_router.get("/knows")
async def list_knows(
    contact_id: str, handler: LinkHandler = Depends(get_link_handler)
) -> list[dict]:
    return await handler.list_knows(contact_id)


@contact_links_router.get("/links")
async def list_dimension_links(
    contact_id: str, handler: LinkHandler = Depends(get_link_handler)
) -> list[dict]:
    return await handler.list_dimension_links(contact_id)


# --- Cross-contact views (not scoped to a single contact_id) ---

actions_router = APIRouter(prefix="/actions", tags=["actions"])


@actions_router.get("/due")
async def list_due_actions(
    before: date | None = None,
    include_completed: bool = False,
    handler: LinkHandler = Depends(get_link_handler),
) -> list[dict]:
    return await handler.list_due_actions(
        before=before or date.today(), include_completed=include_completed
    )


@actions_router.post("/{action_id}/complete", response_model=Action)
async def complete_action(
    action_id: str, handler: LinkHandler = Depends(get_link_handler)
) -> Action:
    try:
        return await handler.complete_action(action_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


misc_router = APIRouter(tags=["misc"])


@misc_router.get("/birthdays")
async def upcoming_birthdays(
    within_days: int = 30, handler: LinkHandler = Depends(get_link_handler)
) -> list[dict]:
    """Backs the CLI "birthdays" scenario (item 5): contacts' own birthdays
    plus their relatives'."""
    return await handler.upcoming_birthdays(within_days=within_days)
