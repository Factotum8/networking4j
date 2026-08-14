"""Neo4j driver lifecycle and schema bootstrap.

Per networking-app-ai-prompt.md: no Alembic-style migrations — the schema is
kept up to date with idempotent ``CREATE CONSTRAINT/INDEX IF NOT EXISTS``
statements run once at startup. The actual constraint/index list is added in
stage 1 (data model) once the node labels are defined; ``ensure_schema`` is
the single place that will grow.
"""

from __future__ import annotations

from loguru import logger
from neo4j import AsyncDriver, AsyncGraphDatabase

from app.config import settings


def create_driver() -> AsyncDriver:
    """Build the async Neo4j driver from configured credentials."""
    return AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


async def ensure_schema(driver: AsyncDriver) -> None:
    """Create constraints/indexes if they don't already exist.

    Deliberately idempotent (``IF NOT EXISTS``) so it's safe to run on every
    startup rather than tracking migration state.
    """
    statements: list[str] = [
        # Dimension nodes deduplicated by name (Event/Project deliberately
        # excluded — their names may legitimately repeat, e.g. a recurring
        # event or a project name reused across companies).
        "CREATE CONSTRAINT tag_name_unique IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE",
        "CREATE CONSTRAINT company_name_unique IF NOT EXISTS "
        "FOR (c:Company) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT community_name_unique IF NOT EXISTS "
        "FOR (c:Community) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT interest_name_unique IF NOT EXISTS "
        "FOR (i:Interest) REQUIRE i.name IS UNIQUE",
        # One MonthlyGoal per month (item 4).
        "CREATE CONSTRAINT monthly_goal_month_unique IF NOT EXISTS "
        "FOR (m:MonthlyGoal) REQUIRE m.month IS UNIQUE",
        # Lookup indexes for non-unique, frequently-filtered properties.
        "CREATE INDEX event_name_index IF NOT EXISTS FOR (e:Event) ON (e.name)",
        "CREATE INDEX project_name_index IF NOT EXISTS FOR (p:Project) ON (p.name)",
        "CREATE INDEX contact_circle_index IF NOT EXISTS FOR (c:Contact) ON (c.circle)",
        "CREATE INDEX contact_archived_index IF NOT EXISTS FOR (c:Contact) ON (c.archived)",
        "CREATE INDEX contact_birthday_index IF NOT EXISTS FOR (c:Contact) ON (c.birthday)",
        "CREATE INDEX action_due_date_index IF NOT EXISTS FOR (a:Action) ON (a.due_date)",
        # Full-text search over name/notes/tags (stage 3: search and dedup).
        "CREATE FULLTEXT INDEX contact_fulltext IF NOT EXISTS "
        "FOR (c:Contact) ON EACH [c.name, c.notes]",
        "CREATE FULLTEXT INDEX tag_fulltext IF NOT EXISTS FOR (t:Tag) ON EACH [t.name]",
    ]
    async with driver.session() as session:
        for statement in statements:
            logger.debug("Applying schema statement: {}", statement)
            await session.run(statement)
    logger.info("Neo4j schema ensured ({} statement(s))", len(statements))
