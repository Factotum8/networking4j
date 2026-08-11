"""Unit tests for `build_llm_provider` — pure selection logic, no network
calls (constructing a Claude/CodexProvider just stores the key/model, it
doesn't touch the API)."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.providers.claude_provider import ClaudeProvider
from app.providers.codex_provider import CodexProvider
from app.providers.factory import LLMProviderUnavailableError, build_llm_provider
from app.services.secrets import LLMApiKeys


def _settings(provider: str) -> Settings:
    return Settings(llm_provider=provider)  # type: ignore[arg-type]


def test_build_llm_provider_returns_claude_when_configured_and_key_present() -> None:
    provider = build_llm_provider(
        _settings("claude"), LLMApiKeys(claude_api_key="sk-claude", codex_api_key=None)
    )
    assert isinstance(provider, ClaudeProvider)


def test_build_llm_provider_returns_codex_when_configured_and_key_present() -> None:
    provider = build_llm_provider(
        _settings("codex"), LLMApiKeys(claude_api_key=None, codex_api_key="sk-codex")
    )
    assert isinstance(provider, CodexProvider)


def test_build_llm_provider_raises_when_claude_selected_but_key_missing() -> None:
    with pytest.raises(LLMProviderUnavailableError, match="claude"):
        build_llm_provider(
            _settings("claude"), LLMApiKeys(claude_api_key=None, codex_api_key="sk-codex")
        )


def test_build_llm_provider_raises_when_codex_selected_but_key_missing() -> None:
    with pytest.raises(LLMProviderUnavailableError, match="codex"):
        build_llm_provider(
            _settings("codex"), LLMApiKeys(claude_api_key="sk-claude", codex_api_key=None)
        )


def test_build_llm_provider_does_not_fall_back_to_the_other_provider() -> None:
    """Explicit user decision (stage 8): no automatic fallback even when the
    other provider's key *is* available."""
    with pytest.raises(LLMProviderUnavailableError):
        build_llm_provider(
            _settings("claude"), LLMApiKeys(claude_api_key=None, codex_api_key="sk-codex")
        )
