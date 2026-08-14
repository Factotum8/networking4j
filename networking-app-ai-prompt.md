# Prompt for an AI agent: developing a "Personal Networking Base" application

> Copy the entire contents of this file as the first message in a session with an AI agent (Claude Code, etc.).

You are an AI developer agent. Your task is to design and implement an application according to the specification (spec) below.

## Rules of engagement (mandatory, no exceptions)

1. **Do not invent or guess on the user's behalf.** If something in the spec is not described, is described ambiguously, or allows multiple interpretations — stop and ask a clarifying question instead of making the decision yourself and silently baking it into the architecture or code. Silent assumptions are prohibited.
2. **Questions first, then a plan, then code — strictly in this order.**
   - Step 1: study the spec and ask all clarifying questions needed for design (a list of known ambiguities is below — add your own findings to it). Wait for the user's answers.
   - Step 2: only after receiving the answers, put together a step-by-step chain of actions (development stages: data model, backend, frontend, integrations, tests, deployment, etc.) with a brief description of what is done at each stage and in what order.
   - Step 3: present this plan to the user and wait for explicit confirmation or edits. Do not start writing code before confirmation.
   - Step 4: only after confirmation, move on to implementation, following the plan item by item.
3. If, during the implementation of any stage, you encounter a fork in the road, a non-obvious architectural decision, or missing information — stop and ask again, do not proceed "at your own discretion."
4. After completing each major stage of the plan — briefly report what has been done and what's next, and wait for confirmation before moving on to the next stage.
5. If the user explicitly asks you to make the decision yourself ("your call," "whatever you think is best") — then you may decide on your own, but such permission must be explicit, not implied.

## Clarifications on the spec (question → user's answer)

Below are the questions that have already been asked, along with the user's final answers. **All items below are resolved — there is no need to ask about them again.**

### 1. The "FC SC SC" circles
**Question:** what are the circles actually called, by what criteria does a contact fall into one circle or another, how is this reflected in the UI/on the graph, and which circle maps to which of the 3 concentric target zones?
**Answer:** Support Circle, Functional Circles, Success Circle. The user manually decides which circle to place a contact in (manually, not automatically). On the graph — 3 concentric zones, like a target: **Support Circle = core (innermost)**, **Functional Circles = middle layer**, **Success Circle = outer zone**. Full names are used everywhere in code/UI (never the "SC" abbreviation, since Support Circle and Success Circle both abbreviate to it).

### 2. Contact types
**Question:** exact terms, and is "bridge" part of the final enum?
**Answer:** a fixed enum, exactly one value per contact, **4 types**: connector, condenser, bridge, insider (private contact).

### 3. Contact criteria
**Question:** is this an enum/tags? Can they be combined? Manual or calculated?
**Answer:** three numeric attributes (dangerous, interesting, difficult), each on a scale of 1 to 10. These are not tags.

### 4. Networking goal and monthly goal
**Question:** free text or metrics? A single overall goal, or a month-by-month history?
**Answer:** free text. **Two separate objects**: a single, standalone overall "networking goal" (not tied to a month, edited in place) **plus** an independent month-by-month goal history (with the ability to look back at past periods).

### 5. CLI for connecting an AI agent
**Question:** what scenarios does the CLI cover, which AI does it work through, is it a standalone utility or a built-in command; how are "relatives" and "important facts" modeled; what's the architecture for two LLM providers and where are API keys stored?
**Answer:**
- Scenarios: add a contact via text, ask "who haven't I talked to in a while," request context from the last meeting, a contact's birthday and the birthdays of their relatives, important facts about a contact and their interests.
- **Relatives**: a separate `(:Relative {name, relation_type, birthday})` node linked to `Contact` (e.g. `(:Contact)-[:HAS_RELATIVE]->(:Relative)`) — not properties on the contact itself.
- **Important facts about a contact**: **the same thing as the existing "notes" field** — no separate structured entity.
- **LLM architecture**: a single abstract provider interface (`LLMProvider`) with `ClaudeProvider`/`CodexProvider` implementations behind it; the concrete provider is chosen via config.
- **CLI shape**: a standalone utility (its own entry point/executable), calling the main application's API over HTTP — not a command baked into the main app process.
- **API key storage**: **1Password integration** — specifically a **1Password Service Account + the official 1Password SDK**. The app fetches the Claude API / Codex API keys from the vault via the SDK at startup, using a service-account token; no desktop app dependency, works in Docker/production.

### 6. Other open items
**Question:** threshold for "haven't been in touch for a while"; how many photos per contact; backup format.
**Answer:**
- **"Haven't been in touch" threshold**: a single global value, **user-configurable** in application settings (not hardcoded, not per-contact).
- **Photos**: **one photo per contact** (an avatar/profile picture) — no gallery.
- **Backups**: **`neo4j-admin database dump` plus an additional structured export (JSON/CSV)** for portability/migration/audit, not the raw dump alone.

## Technical specification

### 1. Description

The application is intended for maintaining a personal networking base and visually analyzing connections between people. The application is based on the book "Networking for Spies."

The user will be able to create and edit contact cards, add a photo, contact details, job title, company, city, tags, interests, notes, and the place and date they met. For each person, a history of meetings, calls, correspondence, referrals, and joint projects will be available.

Contacts can be linked to one another, as well as to companies, events, communities, projects, and professional interests. For each connection, its type, date, comment, and degree of closeness are specified.

The main screen will contain search, filters, recently added contacts, upcoming reminders, and a list of people who haven't been in touch for a while (threshold configurable in settings). The user will be able to assign the next action: write, call, meet, or come back to the contact later.

A graphical map will allow viewing contacts and connections interactively, expanding the surroundings of a selected person, finding chains of acquaintances, and filtering the graph by companies, tags, events, and interests. The interface is split into 3 concentric circles per the book: **Support Circle** (core), **Functional Circles** (middle layer), **Success Circle** (outer zone); the user manually assigns each contact to one of the three.

Import and export of data, duplicate search, contact archiving, and backups are also provided. Data deletion is performed only after user confirmation.

There is a CLI for connecting an AI agent (Claude API / Codex API), running as a standalone utility that talks to the main application over its API.

The application allows describing an overall networking goal, plus a separate goal for the coming month (with history by month).
The application allows specifying a contact type: connector, condenser, bridge, insider (private contact).
Contact criteria: dangerous, interesting, difficult (1–10 scale each).

### 2. Recommended technology stack

#### Backend
- **FastAPI** — API layer (`api → handlers → repositories`).
- **neo4j** (official async driver, `AsyncGraphDatabase`) — repositories write Cypher and map the result to **Pydantic v2** models.
- Database schema without Alembic migrations: idempotent `CREATE CONSTRAINT/INDEX IF NOT EXISTS`, executed at application startup (lifespan hook).

#### Database — Neo4j
- Locally: **Docker** (`neo4j:5-community` + the **APOC** plugin).
- Or managed: **Neo4j Aura Free** (removes the backup/devops concern).
- ⚠️ Community Edition does not support online backup (an Enterprise feature). On Community — `neo4j-admin database dump` on a stopped instance via cron; on Aura, backups are handled by the provider.

#### Graph model
```
(:Contact {circle})                                                    // circle: SupportCircle | FunctionalCircles | SuccessCircle
(:Contact)-[:HAD_INTERACTION]->(:Interaction {type, date, comment})   // meetings/calls/correspondence/referrals
(:Contact)-[:KNOWS {type, date, comment, closeness}]->(:Contact)
(:Contact)-[:WORKS_AT]->(:Company)
(:Contact)-[:ATTENDED]->(:Event)
(:Contact)-[:MEMBER_OF]->(:Community)
(:Contact)-[:INVOLVED_IN]->(:Project)
(:Contact)-[:INTERESTED_IN]->(:Interest)
(:Contact)-[:TAGGED]->(:Tag)
(:Contact)-[:NEXT_ACTION]->(:Action {type, due_date})                 // write/call/meet/come back later
(:Contact)-[:HAS_RELATIVE]->(:Relative {name, relation_type, birthday})
```
The interaction history consists of separate nodes rather than a list in a contact property: this enables aggregations ("when did we last see each other") and is easy to extend.

#### Frontend / UI
- CRUD, dashboard (search, filters, recent, reminders, "haven't been in touch for a while") — **NiceGUI**.
- Graph screen: Cypher query (`shortestPath`, variable-length paths, filters by labels/properties) → JSON → rendered via **NVL** (Neo4j Visualization Library) or **Cytoscape.js**, embedded as an HTML/JS component in NiceGUI. Draws the 3 concentric circles (Support/Functional/Success) as background zones, placing each contact per its `circle` property.

#### Search and dedup
- Neo4j **Full-text index** (Lucene) over name/notes/tags.
- **rapidfuzz** in Python — fuzzy comparison of duplicate candidates (name/phone/email) before archiving.

#### Import/export
- **pandas** (CSV/Excel) + **vobject** (vCard) for input/output; import — batched `UNWIND ... MERGE`.

#### Reminders
- **APScheduler** — periodic retrieval of due `Action`s/overdue contacts via Cypher, without Celery/Redis. The "haven't been in touch" threshold is read from user-configurable settings.

#### Deletion with confirmation / archiving
- Soft delete: an `archived: true` / `deleted_at` property on the `Contact` node instead of a physical `DELETE` — confirmation at the UI level (a modal); physical deletion is a separate, rare operation.

#### Backups
- `neo4j-admin database dump` (Community, on a stopped instance, via cron) **plus** a structured export (JSON/CSV, via a small export script over the repositories) for a portable, human-readable copy alongside the binary dump.

#### Tests
- **pytest** + **testcontainers[neo4j]** — integration tests with a real Neo4j container.

#### CLI / AI integration
- Standalone CLI utility (separate entry point/executable), calling the main application's HTTP API — not a command inside the main app process.
- LLM access goes through a single abstract **`LLMProvider`** interface, with `ClaudeProvider` (Claude API) and `CodexProvider` (Codex API) implementations; the active provider is chosen via configuration.
- API keys for both providers are **not** stored in `.env`/config directly: the app fetches them from **1Password** via a **Service Account token + the official 1Password SDK** at startup (no 1Password desktop app dependency — works in Docker/production).

### 3. Final technology set

```
FastAPI + neo4j async driver + Pydantic v2 (Cypher repositories)
Neo4j Community in Docker (or Aura Free)
NiceGUI + NVL/Cytoscape.js (graph screen, 3 concentric circles)
pandas + vobject, rapidfuzz
APScheduler
pytest + testcontainers[neo4j]
Standalone CLI (own entry point) → main app HTTP API → LLMProvider abstraction (Claude API / Codex API)
1Password Service Account + official SDK (Claude/Codex API key retrieval)
```

---

**All clarifications are resolved** (see "Clarifications on the spec" above). Proceed to step 2: draft the step-by-step implementation plan, present it for confirmation (step 3), and only then move to code (step 4).
