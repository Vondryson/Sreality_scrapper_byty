# syntax=docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.13.15-slim-bookworm@sha256:00faa2debb87529f9f0764e9491d8ba400a3678976616c3bd7cb193745ac20d1

FROM ${PYTHON_IMAGE} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/venv/bin:$PATH

WORKDIR /build

COPY requirements-prod.txt pyproject.toml README.md ./
COPY backend/src ./backend/src

RUN python -m venv /opt/venv \
    && python -m pip install -r requirements-prod.txt \
    && python -m pip install --no-deps .


FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PATH=/opt/venv/bin:$PATH \
    PORT=8080

WORKDIR /app

RUN addgroup --system --gid 10001 app \
    && adduser --system --uid 10001 --ingroup app --home /app app \
    && mkdir -p /app/data/raw \
    && chown -R 10001:10001 /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=10001:10001 alembic.ini ./alembic.ini
COPY --chown=10001:10001 backend/alembic ./backend/alembic

USER 10001:10001


FROM runtime AS api

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8080')+'/api/v1/health/live', timeout=3)"]

CMD ["sh", "-c", "exec uvicorn sreality_tracker.api.app:create_app --factory --host 0.0.0.0 --port \"${PORT:-8080}\" --no-access-log"]


FROM runtime AS scraper

CMD ["sreality-scrape", "check"]
