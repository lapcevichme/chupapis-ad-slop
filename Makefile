.DEFAULT_GOAL := help
.PHONY: help install env keys check lint format typecheck test test-deps test-down run worker up down logs migrate migration seed admin openapi

BACKEND := backend
UV := cd $(BACKEND) && uv run
TEST_COMPOSE := docker compose -p adpilot-test -f docker-compose.test.yml

help: ## Список команд
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# --- подготовка ----------------------------------------------------------------

install: ## Зависимости бэкенда, .env и ключи JWT
	cd $(BACKEND) && uv sync --locked
	@$(MAKE) --no-print-directory env keys

env: ## Создать .env из примера (существующий не трогает)
	@test -f .env || (cp .env.example .env && echo "создан .env")

keys: ## Пара ключей RS256 для JWT в backend/secrets (существующие не трогает)
	@mkdir -p $(BACKEND)/secrets
	@test -f $(BACKEND)/secrets/jwt_private_key.pem || ( \
		openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out $(BACKEND)/secrets/jwt_private_key.pem && \
		openssl rsa -in $(BACKEND)/secrets/jwt_private_key.pem -pubout -out $(BACKEND)/secrets/jwt_public_key.pem && \
		echo "созданы backend/secrets/jwt_*.pem")

# --- локальная разработка -------------------------------------------------------

run: ## API с автоперезагрузкой (нужны Postgres, Redis и S3: docker compose up -d db redis s3)
	$(UV) uvicorn app.main:create_app --factory --reload --port 8000 --no-access-log

worker: ## Воркер outbox
	$(UV) python -m app.worker

migrate: ## Миграции, таблицы чекпоинтов агента и справочники
	$(UV) alembic upgrade head
	$(UV) python -m app.cli setup-checkpointer
	$(UV) python -m app.seed

migration: ## Новая миграция по изменениям моделей: make migration m="add posts"
	@test -n "$(m)" || (echo 'usage: make migration m="что изменилось"' && exit 1)
	$(UV) alembic revision --autogenerate -m "$(m)"

seed: ## Справочники (и демо-данные, если задан DEMO_USERS_PASSWORD)
	$(UV) python -m app.seed

admin: ## Администратор: make admin email=you@example.com
	@test -n "$(email)" || (echo 'usage: make admin email=you@example.com' && exit 1)
	$(UV) python -m app.cli create-user "$(email)" --role admin

openapi: ## OpenAPI, схемы инструментов агента и типы фронтенда
	$(UV) python -m app.export_openapi
	$(UV) python -m app.export_tools
	cd frontend && npm run gen:api

# --- проверки -------------------------------------------------------------------

lint: ## Ruff
	$(UV) ruff check app tests alembic
	$(UV) ruff format --check app tests alembic

format: ## Форматирование и автоисправления
	$(UV) ruff check app tests alembic --fix
	$(UV) ruff format app tests alembic

typecheck: ## mypy --strict
	$(UV) mypy app

test-deps: ## Одноразовые Postgres, Redis и S3 для тестов (остаются между запусками)
	$(TEST_COMPOSE) up -d --wait

test: test-deps ## Все тесты на настоящих зависимостях
	$(UV) pytest -q

test-down: ## Убрать тестовые контейнеры
	$(TEST_COMPOSE) down -v

check: lint typecheck test ## То же, что гоняет CI

# --- весь стек в Docker ---------------------------------------------------------

up: env keys ## Собрать и запустить всё: http://localhost:5173
	docker compose up --build

down: ## Остановить стек (данные сохраняются)
	docker compose down --remove-orphans

logs: ## Логи стека
	docker compose logs -f --tail=200
