.PHONY: install run run-cli test lint lint-fix format docker-up docker-down deploy-up deploy-down dump backup clean

install:
	pixi install

run:
	pixi run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-cli:
	pixi run python -m cli.main $(ARGS)

test:
	pixi run -e default pytest -v

lint:
	pixi run -e default ruff check .
	pixi run -e default mypy app cli

lint-fix:
	pixi run -e default ruff check --fix .
	pixi run -e default ruff format .

format:
	pixi run -e default ruff format .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

# Stage 9/10: single-VPS deploy — brings up neo4j AND the containerized app
# (the "prod" profile, see docker-compose.yml). Separate from docker-up/down
# above so local dev (uvicorn --reload via `make run`) is unaffected.
deploy-up:
	docker compose --profile prod up -d --build

deploy-down:
	docker compose --profile prod down

# Community Edition has no online backup — dump on a stopped instance.
# Intended to be invoked by cron against the neo4j container.
dump:
	docker compose exec neo4j neo4j-admin database dump neo4j --to-path=/backups

# Structured JSON/CSV export alongside the binary dump (see stage 4/backups
# in networking-app-ai-prompt.md). Implemented in stage 4.
backup: dump
	pixi run python -m app.services.backup_export

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
