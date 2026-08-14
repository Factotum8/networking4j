"""Picks the configured `LLMProvider` and wires in its API key.

Per the user's stage-8 decision: `Settings.llm_provider` selects Claude or
Codex via `.env`, and there is deliberately **no runtime fallback** to the
other provider if the selected one's key is missing — that's
`LLMProviderUnavailableError`, which `app/main.py` maps to a 500 with a clear
message rather than silently degrading to a different provider.

The key itself is just `settings.claude_api_key`/`codex_api_key` — resolved
from 1Password by `op run` before the process even starts (see
app/config.py's docstring), not by this module.
"""

from __future__ import annotations

from app.config import Settings
from app.providers.base import LLMProvider
from app.providers.claude_provider import ClaudeProvider
from app.providers.codex_provider import CodexProvider


class LLMProviderUnavailableError(Exception):
    """The configured provider's API key isn't set."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"LLM provider '{provider}' has no API key configured — check "
            "LLM_PROVIDER and the corresponding *_API_KEY env var."
        )
        self.provider = provider


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "claude":
        if not settings.claude_api_key:
            raise LLMProviderUnavailableError("claude")
        return ClaudeProvider(settings.claude_api_key, settings.llm_model_claude)

    if not settings.codex_api_key:
        raise LLMProviderUnavailableError("codex")
    return CodexProvider(settings.codex_api_key, settings.llm_model_codex)
