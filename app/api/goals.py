"""`/goals` — the overall networking goal (singleton) and the monthly goal
history (item 4: two separate objects)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_goal_handler
from app.handlers.goal_handler import GoalHandler
from app.models.goal import MonthlyGoal, NetworkingGoal

router = APIRouter(prefix="/goals", tags=["goals"])


class GoalTextUpdate(BaseModel):
    text: str


@router.get("/networking", response_model=NetworkingGoal | None)
async def get_networking_goal(
    handler: GoalHandler = Depends(get_goal_handler),
) -> NetworkingGoal | None:
    return await handler.get_networking_goal()


@router.put("/networking", response_model=NetworkingGoal)
async def set_networking_goal(
    body: GoalTextUpdate, handler: GoalHandler = Depends(get_goal_handler)
) -> NetworkingGoal:
    return await handler.set_networking_goal(body.text)


@router.get("/monthly/{month}", response_model=MonthlyGoal | None)
async def get_monthly_goal(
    month: str, handler: GoalHandler = Depends(get_goal_handler)
) -> MonthlyGoal | None:
    """`month` is "YYYY-MM"."""
    return await handler.get_monthly_goal(month)


@router.put("/monthly/{month}", response_model=MonthlyGoal)
async def set_monthly_goal(
    month: str, body: GoalTextUpdate, handler: GoalHandler = Depends(get_goal_handler)
) -> MonthlyGoal:
    return await handler.set_monthly_goal(month, body.text)


@router.get("/monthly", response_model=list[MonthlyGoal])
async def list_monthly_goal_history(
    handler: GoalHandler = Depends(get_goal_handler),
) -> list[MonthlyGoal]:
    return await handler.list_monthly_goal_history()
