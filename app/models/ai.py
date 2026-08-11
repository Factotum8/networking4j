"""Request/response shapes for stage 8's `/ai/*` endpoints.

`ParsedContactFields` is what an `LLMProvider.parse_contact` call returns —
its field set mirrors the subset of `Contact` an LLM can plausibly infer
from a sentence or two of free text (no archived flag, scores, or
timestamps — nobody describes those in running text). Both `ClaudeProvider`
and `CodexProvider` hand this model's own `model_json_schema()` to their
respective tool/function-calling APIs, so the schema is defined once, here,
not duplicated per provider.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.models.contact import Contact
from app.models.enums import Circle, ContactType


class ParsedContactFields(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    position: str | None = None
    city: str | None = None
    birthday: date | None = None
    notes: str | None = None
    met_place: str | None = None
    met_date: date | None = None
    contact_type: ContactType | None = None
    circle: Circle | None = None


class AiAddContactRequest(BaseModel):
    text: str


class AiAddContactResponse(BaseModel):
    message: str
    contact: Contact


class AiTextResponse(BaseModel):
    """Uniform response shape for every `/ai/*` endpoint except add-contact —
    a single LLM-generated natural-language `message`. Per the user's
    stage-8 decision, the LLM formats *every* `/ai/*` response, not just
    add-contact's parse, so the CLI has one shape (`response.json()
    ["message"]`) to print for all five scenarios."""

    message: str
