# Deploying networking4j

Stage 9/10 of the build plan. Scope, confirmed with the user: a single VPS
running the whole stack via Docker Compose, plain HTTP (no TLS/reverse proxy
yet), manual deploys (no CI-driven autodeploy/registry push). Revisit all
three if this ever needs to be reachable from the open internet or to
support more than one person deploying it.

## Prerequisites on the VPS

- Docker Engine + the Docker Compose plugin (`docker compose version` should
  work — this is the `docker-compose.yml` in this repo, not the standalone
  `docker-compose` v1 binary).
- `git`.
- Nothing else — the app itself runs inside its own container (built from
  the repo's `Dockerfile`), so no local Python/pixi install is needed on the
  server.

## First deploy

```bash
git clone git@github.com:Factotum8/networking4j.git
cd networking4j
cp .env.example .env
```

Edit `.env`:

- `NEO4J_PASSWORD` — set a real password. Neo4j 5 refuses to start if this
  equals the default username (`neo4j`) — see the stage-2 note in
  `app/db.py`'s history if that error ever resurfaces.
- `CLAUDE_API_KEY` / `CODEX_API_KEY` — leave as the literal `op://...`
  placeholders from `.env.example` for now. Resolving them for real requires
  either the 1Password CLI signed in on this VPS (no desktop app here, so
  that's an interactive `op signin` per session — not solved yet, deferred
  on purpose) or a 1Password Service Account (needs a Business/Teams plan;
  the account in use is Individual, so that's off the table too). Everything
  except the `/ai/*` endpoints (stage 8) works fine with the placeholders
  left unresolved; those return a 500 with a clear message instead.
- `APP_PORT` — which host port the app listens on (default `8000`).
- Leave `NEO4J_URI` alone — `docker-compose.yml`'s `app` service overrides it
  to point at the `neo4j` container by service name regardless of what's in
  `.env` (that value is for the CLI/bare-metal `make run` workflow instead).

Then:

```bash
make deploy-up
```

This builds the app image and starts both `neo4j` and `app` (the compose
file's `prod` profile — see the comment above the `app` service in
`docker-compose.yml` for why it's gated behind a profile rather than always
running). First run also builds the Docker image, so it takes a minute or
two; `neo4j` needs to report healthy before `app` starts (compose enforces
this automatically), so the app container reliably finds a working database
on its first request rather than crash-looping.

Verify:

```bash
curl http://<server-ip>:${APP_PORT:-8000}/health
# {"status":"ok"}
```

The dashboard is at `http://<server-ip>:8000/`, the REST API at the same
host/port (`/contacts`, `/search`, etc — see `app/main.py` for the full
router list).

## No TLS yet — read this before opening the port to the internet

The published port is plain HTTP. If this VPS is reachable from the open
internet, put a firewall in front of it (allow only your own IP, or put the
whole thing behind a VPN/SSH tunnel) rather than leaving `${APP_PORT}` (and
Neo4j's `7474`/`7687`, published by the `neo4j` service for local dev
convenience) open to everyone. Adding a reverse proxy with real TLS
(Caddy/nginx + Let's Encrypt) is deliberately out of scope for this pass —
revisit if/when this needs to be reachable from untrusted networks.

## Updating after a code change

```bash
git pull
make deploy-up
```

`docker compose --profile prod up -d --build` (what `make deploy-up` runs)
rebuilds the `app` image only if something changed and restarts just that
container — `neo4j`'s data volume (`neo4j_data`) is untouched.

## Stopping

```bash
make deploy-down
```

Stops and removes both containers; `neo4j_data` (the actual graph data)
lives in a named Docker volume and survives this.

## Backups

Unrelated to this stage but easy to forget on a fresh server: `make backup`
(binary `neo4j-admin dump` + the structured JSON/CSV export from stage 4)
writes to `./backups/` on the host. Point a cron job at it — nothing sets
this up automatically.

## CI

`.github/workflows/ci.yml` runs `ruff check`, `mypy`, and `pytest` on every
push/PR to `main`/`develop`, on GitHub-hosted runners. This repository is
public, so those runs are free and unmetered — no minute budget to manage.
CI only gates merges; it does not build/push a deploy image or trigger
anything on the VPS (no registry, no autodeploy — deploys are the manual
steps above, by design for now).
