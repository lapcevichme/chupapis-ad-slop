.PHONY: install check lint format typecheck test run up migrate seed openapi

install:
	cd backend && uv sync --locked

check: lint typecheck test

lint:
	cd backend && uv run ruff check app tests alembic
	cd backend && uv run ruff format --check app tests alembic

format:
	cd backend && uv run ruff check app tests alembic --fix
	cd backend && uv run ruff format app tests alembic

typecheck:
	cd backend && uv run mypy app

test:
	cd backend && uv run pytest -q

run:
	cd backend && uv run uvicorn app.main:create_app --factory --reload --port 8000 --no-access-log

up:
	docker compose up --build

migrate:
	cd backend && uv run alembic upgrade head

seed:
	cd backend && uv run python -m app.seed

openapi:
	cd backend && uv run python -m app.export_openapi
	cd backend && uv run python -m app.export_tools
	cd frontend && npm run gen:api
