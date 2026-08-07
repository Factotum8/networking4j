"""CLI configuration.

Deliberately separate from ``app.config``: the CLI is a standalone utility
that only ever talks to the main application over HTTP (see item 5 in
networking-app-ai-prompt.md) — it has no direct access to Neo4j, 1Password,
or any other backend-only dependency.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CliSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_base_url: str = Field(default="http://127.0.0.1:8000")
    log_level: str = Field(default="INFO")


settings = CliSettings()
