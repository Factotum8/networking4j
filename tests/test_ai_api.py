"""HTTP-layer tests for `/ai/*` — wiring and the two global exception
handlers registered in app/main.py (LLMProviderUnavailableError -> 500,
AiContactNotFoundError -> 404). Mirrors test_health.py's approach: mock out
lifespan startup, no real Neo4j/1Password/LLM involved. `AiHandler`'s own
logic is covered against fakes in test_ai_handler.py; this only checks that
the router calls it and maps its exceptions correctly.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.handlers.ai_handler import AiContactNotFoundError
from app.providers.factory import LLMProviderUnavailableError
from app.services.secrets import LLMApiKeys


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr("app.main.ensure_schema", AsyncMock(return_value=None))
    monkeypatch.setattr(
        "app.main.load_llm_api_keys",
        AsyncMock(return_value=LLMApiKeys(claude_api_key=None, codex_api_key=None)),
    )
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class _FakeHandler:
    """Duck-typed `AiHandler` stand-in — each kwarg becomes an async method.
    Pass a plain value for a method that should just return it, or a
    callable (e.g. one that raises) for anything else."""

    def __init__(self, **methods: Any) -> None:
        for name, result in methods.items():
            mock = (
                AsyncMock(side_effect=result)
                if callable(result)
                else AsyncMock(return_value=result)
            )
            setattr(self, name, mock)


def _override(fake: _FakeHandler) -> None:
    from app.api.deps import get_ai_handler
    from app.main import app

    app.dependency_overrides[get_ai_handler] = lambda: fake


def test_stale_contacts_returns_llm_message(client: TestClient) -> None:
    _override(_FakeHandler(stale_contacts_summary="Nobody's stale."))

    response = client.get("/ai/stale-contacts")

    assert response.status_code == 200
    assert response.json() == {"message": "Nobody's stale."}


def test_last_meeting_returns_404_when_contact_not_found(client: TestClient) -> None:
    def _raise(*_args: object, **_kwargs: object) -> None:
        raise AiContactNotFoundError("Nobody")

    _override(_FakeHandler(last_meeting_summary=_raise))

    response = client.get("/ai/last-meeting", params={"name": "Nobody"})

    assert response.status_code == 404


def test_ai_endpoint_returns_500_when_llm_provider_unavailable(client: TestClient) -> None:
    from app.api.deps import get_ai_handler
    from app.main import app

    def _raise_unavailable() -> None:
        raise LLMProviderUnavailableError("claude")

    app.dependency_overrides[get_ai_handler] = _raise_unavailable

    response = client.get("/ai/birthdays")

    assert response.status_code == 500
    assert "claude" in response.json()["detail"]


def test_add_contact_returns_created_contact_and_message(client: TestClient) -> None:
    from app.models.contact import Contact

    contact = Contact(id="c1", name="Ada Lovelace")
    _override(_FakeHandler(add_contact_from_text=(contact, "Added Ada Lovelace.")))

    response = client.post("/ai/contacts", json={"text": "met Ada Lovelace today"})

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Added Ada Lovelace."
    assert body["contact"]["name"] == "Ada Lovelace"
