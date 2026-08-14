"""Application configuration.

All configuration is read from environment variables (see ``.env.example``).
The Claude/Codex API keys are **not** resolved by this app at all: `.env`
holds `op://vault/item/field` references, and the process is launched via
`op run --env-file=.env -- ...` (1Password CLI), which substitutes the real
secret values into the environment *before* this module ever reads them —
so `claude_api_key`/`codex_api_key` below just look like any other setting.
See DEPLOY.md for why (Individual/Families 1Password plans have no Service
Accounts, so the Stage 8 SDK-based approach only works on a Business plan).
"""

from __future__ import annotations

from typing import Literal

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

    # --- LLM provider API keys ---
    # Resolved from 1Password *before* this process starts (`op run
    # --env-file=.env -- ...`), not by this app — see the module docstring.
    claude_api_key: str | None = Field(default=None)
    codex_api_key: str | None = Field(default=None)

    # --- Networking defaults (overridable per-user via the Settings screen later) ---
    stale_contact_days_default: int = Field(default=60)

    # --- Stage 5: reminders (APScheduler) ---
    # When the daily digest job fires, local server time. No UI to change
    # this yet (stage 6 is the Settings screen) — an env var is enough for
    # a single-user app in the meantime.
    reminder_digest_hour: int = Field(default=8, ge=0, le=23)
    reminder_digest_minute: int = Field(default=0, ge=0, le=59)

    # --- Stage 8: LLM provider (CLI/AI integration) ---
    # Which provider backs every `/ai/*` endpoint — see
    # app.providers.factory. No runtime fallback if the selected provider's
    # key doesn't resolve from 1Password (explicit user decision).
    llm_provider: Literal["claude", "codex"] = Field(default="claude")
    llm_model_claude: str = Field(default="claude-sonnet-4-5-20250929")
    llm_model_codex: str = Field(default="gpt-5-codex")


settings = Settings()
