"""`CodexProvider` — Codex API (OpenAI SDK) backend for `LLMProvider` (stage 8)."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageFunctionToolCall

from app.models.ai import ParsedContactFields
from app.providers.base import LLMProvider, LLMProviderError

_PARSE_CONTACT_TOOL = "record_contact"

_PARSE_CONTACT_SYSTEM = (
    "Extract contact details from the user's free-form text describing "
    "someone they met. Call record_contact with whatever fields you can "
    "confidently infer from the text; omit anything that isn't mentioned. "
    "`name` is the only field you must always fill in."
)


class CodexProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def parse_contact(self, text: str) -> ParsedContactFields:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _PARSE_CONTACT_SYSTEM},
                    {"role": "user", "content": text},
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": _PARSE_CONTACT_TOOL,
                            "description": "Record the contact fields extracted from the text.",
                            "parameters": ParsedContactFields.model_json_schema(),
                        },
                    }
                ],
                tool_choice={"type": "function", "function": {"name": _PARSE_CONTACT_TOOL}},
            )
        except Exception as exc:  # openai.APIError and its subclasses
            logger.error("Codex parse_contact call failed: {}", exc)
            raise LLMProviderError(str(exc)) from exc

        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            logger.error("Codex parse_contact response had no tool call: {}", response)
            raise LLMProviderError("Codex response had no tool call")
        tool_call = tool_calls[0]
        if not isinstance(tool_call, ChatCompletionMessageFunctionToolCall):
            # Only a custom (freeform) tool call lacks `.function` — we always
            # request a specific function tool via tool_choice, so this
            # shouldn't happen, but keep mypy honest and fail clearly if it did.
            logger.error("Codex parse_contact returned a non-function tool call: {}", tool_call)
            raise LLMProviderError("Codex returned a non-function tool call")
        arguments = json.loads(tool_call.function.arguments)
        return ParsedContactFields.model_validate(arguments)

    async def complete(self, *, system: str, data: Any) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(data, default=str)},
                ],
            )
        except Exception as exc:
            logger.error("Codex complete call failed: {}", exc)
            raise LLMProviderError(str(exc)) from exc

        content = response.choices[0].message.content
        if not content:
            logger.error("Codex complete response had no content: {}", response)
            raise LLMProviderError("Codex response had no content")
        return content
