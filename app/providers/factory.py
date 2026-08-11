"""Picks the configured `LLMProvider` and wires in its 1Password-resolved
API key.

Per the user's stage-8 decision: `Settings.llm_provider` selects Claude or
Codex via `.env`, and there is deliberately **no runtime fallback** to the
other provider if the selected one's key never resolved from 1Password —
that's `LLMProviderUnavailableError`, which `app/main.py` maps to a 500 with
a clear message rather than silently degrading to a different provider.
"""

from __future__ import annotations

from app.config import Settings
from app.providers.base import LLMProvider
from app.providers.claude_provider import ClaudeProvider
from app.providers.codex_provider import CodexProvider
from app.services.secrets import LLMApiKeys


class LLMProviderUnavailableError(Exception):
    """The configured provider's API key never resolved from 1Password."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"LLM provider '{provider}' has no API key resolved from 1Password — "
            "check LLM_PROVIDER and the corresponding vault item."
        )
        self.provider = provider


def build_llm_provider(settings: Settings, api_keys: LLMApiKeys) -> LLMProvider:
    if settings.llm_provider == "claude":
        if not api_keys.claude_api_key:
            raise LLMProviderUnavailableError("claude")
        return ClaudeProvider(api_keys.claude_api_key, settings.llm_model_claude)

    if not api_keys.codex_api_key:
        raise LLMProviderUnavailableError("codex")
    return CodexProvider(api_keys.codex_api_key, settings.llm_model_codex)
