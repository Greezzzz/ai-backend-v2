# Stage 1: builder — install deps dengan uv
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

# Salin hanya manifest dulu (cache layer install)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Stage 2: runtime ringan
FROM python:3.14-slim

WORKDIR /app

# Deps production dari builder
COPY --from=builder /app/.venv ./.venv

# Kode app + migrasi
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# App: uvicorn. Worker pakai image sama dengan command berbeda:
#   docker compose run worker python -m app.jobs.worker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
