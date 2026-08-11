"""Abstract LLM-provider interface — stage 8, item 5 in
`networking-app-ai-prompt.md`: "a single abstract provider interface
(LLMProvider) with ClaudeProvider/CodexProvider implementations behind it;
the concrete provider is chosen via config."

Two responsibilities, one per shape of CLI scenario (see
`app.handlers.ai_handler`):

- `parse_contact` — turn free text into structured contact fields (the
  `add-contact` scenario).
- `complete` — turn already-fetched app data into a natural-language
  response (`stale`/`last-meeting`/`birthdays`/`facts`) — per the user's
  stage-8 decision that the LLM formats every `/ai/*` response, not just
  add-contact's parse.

Concrete implementations live in `claude_provider.py`/`codex_provider.py`;
`app.providers.factory` picks between them via `Settings.llm_provider`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.ai import ParsedContactFields


class LLMProviderError(Exception):
    """A provider call itself failed — bad response shape, API error, etc.
    Distinct from `app.providers.factory.LLMProviderUnavailableError`, which
    means no key was ever resolved for the configured provider. Registered
    as a FastAPI exception handler (see `app/main.py`) -> 502."""


class LLMProvider(ABC):
    @abstractmethod
    async def parse_contact(self, text: str) -> ParsedContactFields: ...

    @abstractmethod
    async def complete(self, *, system: str, data: Any) -> str: ...
