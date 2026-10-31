FROM ghcr.io/astral-sh/uv:0.11.8-python3.13-trixie-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project

FROM python:3.13-slim-trixie

RUN groupadd --system --gid 999 app \
    && useradd --system --gid 999 --uid 999 --no-create-home app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app app ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app seed ./seed
COPY --chown=app:app alembic.ini ./alembic.ini
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN mkdir -p /app/data && chown app:app /app/data
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
# Стартуем от root только чтобы поправить владельца тома, дальше entrypoint работает под uid 999.
EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
