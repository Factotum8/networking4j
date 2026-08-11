"""`ClaudeProvider` — Claude API backend for `LLMProvider` (stage 8)."""

from __future__ import annotations

import json
from typing import Any

from anthropic import AsyncAnthropic
from loguru import logger

from app.models.ai import ParsedContactFields
from app.providers.base import LLMProvider, LLMProviderError

_PARSE_CONTACT_TOOL = "record_contact"

_PARSE_CONTACT_SYSTEM = (
    "Extract contact details from the user's free-form text describing "
    "someone they met. Call record_contact with whatever fields you can "
    "confidently infer from the text; omit anything that isn't mentioned. "
    "`name` is the only field you must always fill in."
)


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def parse_contact(self, text: str) -> ParsedContactFields:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=_PARSE_CONTACT_SYSTEM,
                messages=[{"role": "user", "content": text}],
                tools=[
                    {
                        "name": _PARSE_CONTACT_TOOL,
                        "description": "Record the contact fields extracted from the text.",
                        "input_schema": ParsedContactFields.model_json_schema(),
                    }
                ],
                tool_choice={"type": "tool", "name": _PARSE_CONTACT_TOOL},
            )
        except Exception as exc:  # anthropic.APIError and its subclasses
            logger.error("Claude parse_contact call failed: {}", exc)
            raise LLMProviderError(str(exc)) from exc

        tool_use = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_use is None:
            logger.error(
                "Claude parse_contact response had no tool_use block: {}", response.content
            )
            raise LLMProviderError("Claude response had no tool_use block")
        return ParsedContactFields.model_validate(tool_use.input)

    async def complete(self, *, system: str, data: Any) -> str:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": json.dumps(data, default=str)}],
            )
        except Exception as exc:
            logger.error("Claude complete call failed: {}", exc)
            raise LLMProviderError(str(exc)) from exc

        text_block = next((b for b in response.content if b.type == "text"), None)
        if text_block is None:
            logger.error("Claude complete response had no text block: {}", response.content)
            raise LLMProviderError("Claude response had no text block")
        return text_block.text
