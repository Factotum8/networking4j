"""One generic router factory for the six name-only dimension node types
(Company, Event, Community, Project, Interest, Tag) instead of six
near-identical routers — mirrors app.repositories.named_node_repository.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.api.deps import get_driver
from app.models.base import GraphNode
from app.models.dimensions import Community, Company, Event, Interest, Project, Tag
from app.repositories.named_node_repository import NamedNodeRepository


class DimensionCreate(BaseModel):
    name: str


def make_dimension_router[T: GraphNode](*, label: str, model: type[T], prefix: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[label.lower()])

    def get_repo(request: Request) -> NamedNodeRepository[T]:
        return NamedNodeRepository(get_driver(request), label, model)

    @router.get("", response_model=list[model])  # type: ignore[valid-type]
    async def list_all(repo: NamedNodeRepository[T] = Depends(get_repo)) -> list[T]:
        return await repo.list_all()

    @router.post("", response_model=model, status_code=status.HTTP_201_CREATED)
    async def create(body: DimensionCreate, repo: NamedNodeRepository[T] = Depends(get_repo)) -> T:
        """MERGE-based: creating an existing name returns the existing node
        rather than erroring (dimension nodes are deduplicated by name)."""
        return await repo.get_or_create(body.name)

    @router.get("/{name}", response_model=model)
    async def get_by_name(name: str, repo: NamedNodeRepository[T] = Depends(get_repo)) -> T:
        found = await repo.get_by_name(name)
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{label} '{name}' not found")
        return found

    return router


companies_router = make_dimension_router(label="Company", model=Company, prefix="/companies")
events_router = make_dimension_router(label="Event", model=Event, prefix="/events")
communities_router = make_dimension_router(
    label="Community", model=Community, prefix="/communities"
)
projects_router = make_dimension_router(label="Project", model=Project, prefix="/projects")
interests_router = make_dimension_router(label="Interest", model=Interest, prefix="/interests")
tags_router = make_dimension_router(label="Tag", model=Tag, prefix="/tags")

all_dimension_routers = [
    companies_router,
    events_router,
    communities_router,
    projects_router,
    interests_router,
    tags_router,
]
