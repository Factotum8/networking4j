"""Minimal "dimension" nodes a Contact links to.

None of these carry extra properties beyond `name` in the graph model given
in networking-app-ai-prompt.md — `WORKS_AT`/`ATTENDED`/`MEMBER_OF`/
`INVOLVED_IN`/`INTERESTED_IN`/`TAGGED` are plain, property-less relationships
there, unlike `KNOWS`/`HAD_INTERACTION`/`NEXT_ACTION`. Keeping these node
models name-only mirrors that spec exactly rather than inventing extra
fields.
"""

from __future__ import annotations

from app.models.base import GraphNode


class Company(GraphNode):
    name: str


class Event(GraphNode):
    name: str


class Community(GraphNode):
    name: str


class Project(GraphNode):
    name: str


class Interest(GraphNode):
    name: str


class Tag(GraphNode):
    name: str
