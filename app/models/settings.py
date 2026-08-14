"""User-configurable application settings, persisted as a single
`(:AppSettings)` node (single-user app — one row is enough).

Not to be confused with `app.config.Settings`, which is process-level
configuration (env vars, secrets coordinates) and never touches Neo4j.
"""

from __future__ import annotations

from pydantic import Field

from app.models.base import GraphNode


class UserSettings(GraphNode):
    # Item 6: the "haven't been in touch for a while" threshold — resolved
    # as a single, user-configurable global value (not hardcoded, not
    # per-contact).
    stale_contact_days: int = Field(default=60, ge=1)

    # Stage 3 (search & dedup): minimum score (0-100, rapidfuzz scale) for a
    # contact pair to surface as a duplicate candidate. Same
    # global-and-overridable pattern as stale_contact_days.
    dedup_score_threshold: float = Field(default=85.0, ge=0, le=100)
