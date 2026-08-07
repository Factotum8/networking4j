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

Below are the questions that have already been asked, along with the user's answers to them. **There is no need to ask about these items again.** Some answers have open loose ends — they are marked **⚠️ Still needs clarification**; these must be resolved with the user before moving on to the plan.

### 1. The "FC SC SC" circles
**Question:** what are the circles actually called, by what criteria does a contact fall into one circle or another, and how is this reflected in the UI/on the graph?
**Answer:** Support Circle, Functional Circles, Success Circle. The user manually decides where to place a contact (manually, not automatically). On the graph — 3 concentric zones: core, middle layer, outer layer — similar to a target/bullseye.
**⚠️ Still needs clarification:** "Support Circle" and "Success Circle" abbreviate the same way ("SC") — the code/UI should use full names rather than abbreviations to avoid confusion. Also, the explicit mapping "circle → target zone" (which of the three circles = core, which = middle layer, which = outer zone) has not been fixed — this needs to be clarified with the user before designing the graph model and UI.

### 2. Contact types
**Question:** the exact terms need to be checked against the source material; is this a fixed single-value enum, or can a contact have multiple types?
**Answer:** a fixed enum, exactly one value per contact. Terms to check against the source material: connector, condenser, insider (private contact).
**⚠️ Still needs clarification:** the original spec listed 4 types (connector, condenser, **bridge**, insider/private contact); in the answer "bridge" disappeared, and "condenser" is listed twice — this looks like a typo when typing the answer. Before implementation, confirm with the user the final, deduplicated list of types (does "bridge" belong in the final enum).

### 3. Contact criteria
**Question:** is this an enum/tags? Can they be combined? Manual or calculated?
**Answer:** three numeric attributes (dangerous, interesting, difficult), each on a scale of 1 to 10. These are not tags. Closed, no further clarification needed.

### 4. Networking goal and monthly goal
**Question:** free text or metrics? A single overall goal, or a month-by-month history?
**Answer:** free text; a history of goals by month is kept, with the ability to look at past periods.
**⚠️ Still needs clarification:** the spec distinguishes between the "networking goal" (overall) and the "specific goal for the coming month" — the answer only describes the mechanics for the monthly goal. Clarify with the user: is this one and the same field (the overall goal is simply the current month) or two separate objects — a separate, unchanging overall goal plus a separate monthly history?

### 5. CLI for connecting an AI agent
**Question:** what scenarios does the CLI cover, which AI does it work through, is it a standalone utility or a built-in command?
**Answer:** scenarios — add a contact via text, ask "who haven't I talked to in a while," request context from the last meeting, a contact's birthday and the birthdays of their relatives, important facts about a contact and their interests. Works through the Claude API and the Codex API.
**⚠️ Still needs clarification:**
- "Contact's relatives" and their birthdays — this is a new entity, absent from the graph model (the "Graph Model" section below). Clarify the structure: a separate `(:Relative)` node linked to `Contact`, or a set of properties on the contact itself?
- "Important facts about a contact" — is this the same as the existing "notes" field, or a separate structured entity (a list of facts with dates/sources)?
- The use of two LLM providers (Claude API and Codex API) is not reflected in the "Recommended stack" section — need to clarify the architecture with the user: direct calls to both SDKs, a single abstract interface over the providers, where and how API keys are stored, and whether the CLI runs as a separate process or as a command within the main application.

### 6. Other
Also clarify any other spec items you consider insufficiently defined for designing the data schema, UI, or logic (for example: what counts as "haven't been in touch for a while" — a specific threshold in days, user-configurable or not; what counts as "photos" — one or several per contact; the backup format, etc.).

## Technical specification

### 1. Description

The application is intended for maintaining a personal networking base and visually analyzing connections between people. The application is based on the book "Networking for Spies."

The user will be able to create and edit contact cards, add photos, contact details, job title, company, city, tags, interests, notes, and the place and date they met. For each person, a history of meetings, calls, correspondence, referrals, and joint projects will be available.

Contacts can be linked to one another, as well as to companies, events, communities, projects, and professional interests. For each connection, its type, date, comment, and degree of closeness are specified.

The main screen will contain search, filters, recently added contacts, upcoming reminders, and a list of people who haven't been in touch for a while. The user will be able to assign the next action: write, call, meet, or come back to the contact later.

A graphical map will allow viewing contacts and connections interactively, expanding the surroundings of a selected person, finding chains of acquaintances, and filtering the graph by companies, tags, events, and interests. The interface should be split into 3 circles — FC SC SC — per the book.

Import and export of data, duplicate search, contact archiving, and backups are also provided. Data deletion is performed only after user confirmation.

There is a CLI for connecting an AI agent.

The application allows describing a networking goal. There is a specific goal for the coming month.
The application allows specifying a contact type: connector, condenser, bridges, insiders (private contacts).
Contact criteria: dangerous, interesting, difficult.

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
(:Contact)-[:HAD_INTERACTION]->(:Interaction {type, date, comment})   // meetings/calls/correspondence/referrals
(:Contact)-[:KNOWS {type, date, comment, closeness}]->(:Contact)
(:Contact)-[:WORKS_AT]->(:Company)
(:Contact)-[:ATTENDED]->(:Event)
(:Contact)-[:MEMBER_OF]->(:Community)
(:Contact)-[:INVOLVED_IN]->(:Project)
(:Contact)-[:INTERESTED_IN]->(:Interest)
(:Contact)-[:TAGGED]->(:Tag)
(:Contact)-[:NEXT_ACTION]->(:Action {type, due_date})                 // write/call/meet/come back later
```
The interaction history consists of separate nodes rather than a list in a contact property: this enables aggregations ("when did we last see each other") and is easy to extend.

#### Frontend / UI
- CRUD, dashboard (search, filters, recent, reminders, "haven't been in touch for a while") — **NiceGUI**.
- Graph screen: Cypher query (`shortestPath`, variable-length paths, filters by labels/properties) → JSON → rendered via **NVL** (Neo4j Visualization Library) or **Cytoscape.js**, embedded as an HTML/JS component in NiceGUI.

#### Search and dedup
- Neo4j **Full-text index** (Lucene) over name/notes/tags.
- **rapidfuzz** in Python — fuzzy comparison of duplicate candidates (name/phone/email) before archiving.

#### Import/export
- **pandas** (CSV/Excel) + **vobject** (vCard) for input/output; import — batched `UNWIND ... MERGE`.

#### Reminders
- **APScheduler** — periodic retrieval of due `Action`s/overdue contacts via Cypher, without Celery/Redis.

#### Deletion with confirmation / archiving
- Soft delete: an `archived: true` / `deleted_at` property on the `Contact` node instead of a physical `DELETE` — confirmation at the UI level (a modal); physical deletion is a separate, rare operation.

#### Tests
- **pytest** + **testcontainers[neo4j]** — integration tests with a real Neo4j container.

#### CLI / AI integration (needs clarification — see item 5 in the "Clarifications on the spec" section)
- Work is planned through the **Claude API** and the **Codex API** — the specific architecture (a single abstract interface over the providers vs. direct calls to each SDK, key storage, a separate CLI process or a command within the main application) has not been defined and must be clarified with the user before designing this layer.

### 3. Final technology set

```
FastAPI + neo4j async driver + Pydantic v2 (Cypher repositories)
Neo4j Community in Docker (or Aura Free)
NiceGUI + NVL/Cytoscape.js (graph screen)
pandas + vobject, rapidfuzz
APScheduler
pytest + testcontainers[neo4j]
```

---

**Start with step 1**, but keep in mind: some of the clarifying questions have already been resolved by the user's answers in the "Clarifications on the spec" section — there is no need to ask about them again. Be sure to ask about the items marked **⚠️ Still needs clarification** within that section (the final, deduplicated list of contact types; the circle↔target-zone mapping; the status of the overall networking goal as distinct from the monthly one; the structure of a contact's "relatives"/"important facts"; the architecture for integrating with the Claude API and the Codex API), plus any other ambiguities you notice yourself in the spec above. Only after these questions have been resolved should you move on to step 2 (the plan), wait for confirmation (step 3), and only then proceed to code (step 4).
