"""Application configuration.

All configuration is read from environment variables (see ``.env.example``).
Nothing here holds an actual secret value — API keys for Claude/Codex are
fetched at runtime from 1Password (see ``app.services.secrets``); this module
only holds the *coordinates* needed to look them up (service account token,
vault, item names).
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide configuration, loaded once at import time."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App server ---
    app_host: str = Field(default="127.0.0.1")
    app_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")

    # --- Neo4j ---
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="neo4j")

    # --- 1Password (Service Account) — see item 5 in networking-app-ai-prompt.md ---
    op_service_account_token: str | None = Field(default=None)
    op_vault: str = Field(default="networking4j")
    op_item_claude_api_key: str = Field(default="claude-api-key")
    op_item_codex_api_key: str = Field(default="codex-api-key")
    op_field_claude_api_key: str = Field(default="credential")
    op_field_codex_api_key: str = Field(default="credential")

    # --- Networking defaults (overridable per-user via the Settings screen later) ---
    stale_contact_days_default: int = Field(default=60)

    # --- Stage 5: reminders (APScheduler) ---
    # When the daily digest job fires, local server time. No UI to change
    # this yet (stage 6 is the Settings screen) — an env var is enough for
    # a single-user app in the meantime.
    reminder_digest_hour: int = Field(default=8, ge=0, le=23)
    reminder_digest_minute: int = Field(default=0, ge=0, le=59)


settings = Settings()
