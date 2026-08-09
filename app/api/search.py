"""`/search` — stage 3: full-text search and duplicate-candidate detection.

Detection only: there's no merge/resolve endpoint here by explicit user
decision — a surfaced duplicate is cleaned up via the existing
`/contacts/{id}/archive` endpoint, not by rewiring relationships.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_search_handler
from app.handlers.search_handler import SearchHandler
from app.models.contact import Contact
from app.models.duplicate import DuplicateCandidate

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[Contact])
async def search_contacts(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    handler: SearchHandler = Depends(get_search_handler),
) -> list[Contact]:
    return await handler.search(q, limit=limit)


@router.get("/duplicates", response_model=list[DuplicateCandidate])
async def list_duplicate_candidates(
    threshold: float | None = Query(default=None, ge=0, le=100),
    handler: SearchHandler = Depends(get_search_handler),
) -> list[DuplicateCandidate]:
    return await handler.find_duplicates(threshold=threshold)
