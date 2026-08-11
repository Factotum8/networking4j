"""Standalone CLI entry point for the AI-agent integration.

Thin HTTP client over the main app's API — no direct DB/LLM access from
here (see item 5 in networking-app-ai-prompt.md). The ``/ai/*`` endpoints
(stage 8, ``app/api/ai.py``) always respond with a JSON body carrying a
``message`` key holding the LLM-generated text; every command below just
prints that.

Run with: ``pixi run python -m cli.main --help``
"""

from __future__ import annotations

import httpx
import typer
from loguru import logger

from app.logging_config import configure_logging
from cli.config import settings

app = typer.Typer(help="AI-agent CLI for the personal networking base.")


def _client() -> httpx.Client:
    return httpx.Client(base_url=settings.api_base_url, timeout=30.0)


@app.command("add-contact")
def add_contact(text: str) -> None:
    """Add a contact from free-form text (parsed by the LLM provider)."""
    logger.info("Requesting contact creation from free text")
    with _client() as client:
        response = client.post("/ai/contacts", json={"text": text})
        response.raise_for_status()
        typer.echo(response.json()["message"])


@app.command("stale")
def stale() -> None:
    """List contacts nobody has talked to in a while."""
    logger.info("Requesting stale-contact list")
    with _client() as client:
        response = client.get("/ai/stale-contacts")
        response.raise_for_status()
        typer.echo(response.json()["message"])


@app.command("last-meeting")
def last_meeting(name: str) -> None:
    """Show the context of the last meeting with a contact."""
    logger.info("Requesting last-meeting context for '{}'", name)
    with _client() as client:
        response = client.get("/ai/last-meeting", params={"name": name})
        response.raise_for_status()
        typer.echo(response.json()["message"])


@app.command("birthdays")
def birthdays() -> None:
    """Show upcoming birthdays for contacts and their relatives."""
    logger.info("Requesting upcoming birthdays")
    with _client() as client:
        response = client.get("/ai/birthdays")
        response.raise_for_status()
        typer.echo(response.json()["message"])


@app.command("facts")
def facts(name: str) -> None:
    """Show important facts and interests for a contact."""
    logger.info("Requesting facts/interests for '{}'", name)
    with _client() as client:
        response = client.get("/ai/facts", params={"name": name})
        response.raise_for_status()
        typer.echo(response.json()["message"])


if __name__ == "__main__":
    configure_logging()
    app()
