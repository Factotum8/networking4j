"""`/ai/*` — stage 8: the 5 endpoints `cli/main.py` calls for its AI-agent
scenarios (item 5 in `networking-app-ai-prompt.md`). Every response is
`{"message": "<LLM text>"}` (add-contact also includes the created
contact), so the CLI has one uniform shape to print across all five.

`LLMProviderUnavailableError` (missing 1Password key) and `LLMProviderError`
(the provider call itself failing) are handled globally in `app/main.py`,
not per-route here — see that module's exception handlers.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_ai_handler
from app.handlers.ai_handler import AiContactNotFoundError, AiHandler
from app.models.ai import AiAddContactRequest, AiAddContactResponse, AiTextResponse

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/contacts", response_model=AiAddContactResponse, status_code=status.HTTP_201_CREATED)
async def add_contact(
    body: AiAddContactRequest, handler: AiHandler = Depends(get_ai_handler)
) -> AiAddContactResponse:
    contact, message = await handler.add_contact_from_text(body.text)
    return AiAddContactResponse(message=message, contact=contact)


@router.get("/stale-contacts", response_model=AiTextResponse)
async def stale_contacts(handler: AiHandler = Depends(get_ai_handler)) -> AiTextResponse:
    return AiTextResponse(message=await handler.stale_contacts_summary())


@router.get("/last-meeting", response_model=AiTextResponse)
async def last_meeting(
    name: str = Query(...), handler: AiHandler = Depends(get_ai_handler)
) -> AiTextResponse:
    try:
        return AiTextResponse(message=await handler.last_meeting_summary(name))
    except AiContactNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found") from exc


@router.get("/birthdays", response_model=AiTextResponse)
async def birthdays(handler: AiHandler = Depends(get_ai_handler)) -> AiTextResponse:
    return AiTextResponse(message=await handler.birthdays_summary())


@router.get("/facts", response_model=AiTextResponse)
async def facts(
    name: str = Query(...), handler: AiHandler = Depends(get_ai_handler)
) -> AiTextResponse:
    try:
        return AiTextResponse(message=await handler.facts_summary(name))
    except AiContactNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found") from exc
