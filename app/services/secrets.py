"""1Password-backed secret retrieval.

Per the resolved answer in networking-app-ai-prompt.md (item 5): API keys for
the Claude API and the Codex API are never stored in `.env`/config directly.
They are fetched from a 1Password vault through a **Service Account token +
the official 1Password SDK**, so this works headless in Docker/production —
no 1Password desktop app required.

If ``settings.op_service_account_token`` is not set (e.g. local dev without
1Password configured yet), secret resolution is skipped and callers get
``None`` back — the LLM-provider layer built in stage 8 is responsible for
deciding whether that's fatal.
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from onepassword.client import Client

from app.config import settings

_INTEGRATION_NAME = "networking4j"
_INTEGRATION_VERSION = "v0.1.0"


@dataclass(frozen=True, slots=True)
class LLMApiKeys:
    """Bag of provider API keys resolved from 1Password at startup."""

    claude_api_key: str | None
    codex_api_key: str | None


async def load_llm_api_keys() -> LLMApiKeys:
    """Resolve the Claude/Codex API keys from 1Password.

    Returns keys as ``None`` (rather than raising) when the service account
    token isn't configured, so the app can still start in environments where
    the CLI/LLM integration isn't needed yet (e.g. early local development).
    """
    if not settings.op_service_account_token:
        logger.warning(
            "OP_SERVICE_ACCOUNT_TOKEN not set — skipping 1Password secret "
            "resolution, LLM providers will be unavailable"
        )
        return LLMApiKeys(claude_api_key=None, codex_api_key=None)

    client = await Client.authenticate(
        auth=settings.op_service_account_token,
        integration_name=_INTEGRATION_NAME,
        integration_version=_INTEGRATION_VERSION,
    )

    claude_ref = (
        f"op://{settings.op_vault}/{settings.op_item_claude_api_key}/"
        f"{settings.op_field_claude_api_key}"
    )
    codex_ref = (
        f"op://{settings.op_vault}/{settings.op_item_codex_api_key}/"
        f"{settings.op_field_codex_api_key}"
    )

    claude_api_key = await client.secrets.resolve(claude_ref)
    codex_api_key = await client.secrets.resolve(codex_ref)
    logger.info("Resolved Claude/Codex API keys from 1Password vault '{}'", settings.op_vault)
    return LLMApiKeys(claude_api_key=claude_api_key, codex_api_key=codex_api_key)
