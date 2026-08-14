"""Stage 0 smoke test: the app boots (lifespan runs) and /health responds.

Now that `ensure_schema` has real constraint/index statements (stage 1), it
needs a live Neo4j to run — which this test deliberately avoids, since it's
only meant to check the FastAPI wiring, not the schema. `app.db.ensure_schema`
itself is validated against a real container in test_db_schema.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


def test_health(monkeypatch) -> None:
    monkeypatch.setattr("app.main.ensure_schema", AsyncMock(return_value=None))

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
