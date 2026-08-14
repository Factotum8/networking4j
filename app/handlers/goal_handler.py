"""Business logic for the two goal objects (item 4)."""

from __future__ import annotations

from loguru import logger

from app.models.goal import MonthlyGoal, NetworkingGoal
from app.repositories.goal_repository import MonthlyGoalRepository, NetworkingGoalRepository


class GoalHandler:
    def __init__(
        self, goal_repo: NetworkingGoalRepository, monthly_repo: MonthlyGoalRepository
    ) -> None:
        self._goal_repo = goal_repo
        self._monthly_repo = monthly_repo

    async def get_networking_goal(self) -> NetworkingGoal | None:
        goal = await self._goal_repo.get()
        if goal is None:
            logger.debug("No networking goal set yet")
        return goal

    async def set_networking_goal(self, text: str) -> NetworkingGoal:
        goal = await self._goal_repo.set_text(text)
        logger.info("Networking goal updated")
        return goal

    async def get_monthly_goal(self, month: str) -> MonthlyGoal | None:
        goal = await self._monthly_repo.get_by_month(month)
        if goal is None:
            logger.debug("No monthly goal set for {}", month)
        return goal

    async def set_monthly_goal(self, month: str, text: str) -> MonthlyGoal:
        goal = await self._monthly_repo.upsert(month, text)
        logger.info("Monthly goal for {} updated", month)
        return goal

    async def list_monthly_goal_history(self) -> list[MonthlyGoal]:
        history = await self._monthly_repo.list_history()
        logger.debug("Listed {} monthly goal(s)", len(history))
        return history
