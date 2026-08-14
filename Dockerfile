# Production image for the FastAPI app (stage 9/10 — single-VPS Docker
# Compose deploy, see DEPLOY.md). Not multi-stage: this is a personal
# project, not a size-optimized public image, so a plain pixi-managed
# image is simpler to reason about than a distroless/venv-copy build.
FROM ghcr.io/prefix-dev/pixi:0.63.2 AS runtime

WORKDIR /app

# Copy the manifest/lock first so `pixi install` is Docker-layer-cached
# across rebuilds that only touch application code.
COPY pixi.toml pixi.lock ./
RUN pixi install -e default --locked

COPY . .

EXPOSE 8000

# `pixi run` re-activates the resolved `default` environment; -- passes the
# rest of the line straight to uvicorn (mirrors the `make run` target,
# minus --reload, which has no place in production).
ENTRYPOINT ["pixi", "run", "-e", "default", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
