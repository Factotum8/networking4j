# AGENTS.md — Personal Networking Base

> This file follows the `AGENTS.md` convention, picked up by default by AI agents (Codex CLI, Claude Code, etc.).

Related documents:
- [`networking-app-ai-prompt.md`](./networking-app-ai-prompt.md) — the starting prompt for the first session with the agent (spec questions/answers, plan before code).

## What this project is

A personal networking base with visual analysis of connections between people (a graph of contacts, companies, events, communities, projects, and interests). See the spec above for details.

## Technology stack

```
FastAPI + neo4j async driver + Pydantic v2 (Cypher repositories)
Neo4j Community in Docker (or Aura Free)
NiceGUI + NVL/Cytoscape.js (graph screen)
pandas + vobject, rapidfuzz
APScheduler
pytest + testcontainers[neo4j]
CLI integration: Claude API and Codex API (architecture — see open questions in networking-app-ai-prompt.md)
```

## Agent working rules (always apply, not just in the first session)

1. **Do not invent or guess.** Ambiguity in a task is a reason to stop and ask, not to silently pick an option.
2. **Questions first → then a plan → agreement → then code.** Don't start writing code without an approved plan, unless the task is trivial (a one-line fix/typo can go straight through).
3. A fork in the road or missing information during work — ask again, don't proceed "at your own discretion."
4. After a major stage — a short report on what's done and what's next, wait for confirmation.
5. Explicit user permission ("your call") waives rule 1 for that specific decision — but not by default.

---

## Code style

> Draft structure below, to be extended by the user.

### Python
- Version 3.14
- Use a Makefile for commands.
- Use Pixi as the package manager.
- Use t-strings.
- Use lazy annotation evaluation.
- Use generic syntax.
- Use f-strings.
- Use Loguru.
- Use `ExceptionGroup` & `except*`.

### Code review guidelines

Please analyze the code and provide a review, including manual changes given in the merge request. Important notes that must be considered by the developer:
за
- Follow PEP 8.
- Follow SOLID principles.
- Follow the Zen of Python.
- Pattern matching is better than if/else.
- Prefer "look before you leap" (LBYL) over "ask for forgiveness" (EAFP).
- Don't forget to write tests.
- Don't forget to write docstrings and comments.
- Use Object-Oriented Programming.
- Use Pydantic models, dataclasses, or named tuples instead of dictionaries.
- Use async/await consistently throughout the codebase.
- To prevent blocking operations from halting the main application flow, execute them in a separate thread or process.
- Avoid wrapping many lines in a single try/except block.
- Keep the code consistent.
- Ensure a sufficient and necessary logging level throughout the code.
- Every `return` statement must be logged with appropriate context.
- Every `if`/`else` condition must be logged to track code flow and decision points.
- Use structured logging with proper log levels (DEBUG, INFO, WARNING, ERROR).
- Log messages should include meaningful context (variables, state, business logic context).
- Every `return` statement inside a method of a class that has access to a logger must be preceded by a log entry.