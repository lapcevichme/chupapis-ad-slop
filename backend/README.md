# Бэкенд AdPilot AI

Архитектура адаптирована из Monolith-backend-template: `api → service → domain`,
`db/infra`, async SQLAlchemy и UoW, фабрика приложения, явная конфигурация и request id.
Сохранён API кампаний и чата. Карта слоёв — [architecture.md](../docs/architecture.md),
внешний контракт — [CONTRACTS.md](../docs/CONTRACTS.md).

## Запуск

Из корня репозитория:

```bash
cp .env.example .env
make install
make migrate
make seed
make run
```

API/Swagger: http://localhost:8000/docs. Для чата заполнить `LLM_API_KEY` в `.env`.
Модели и провайдер выбираются конфигом; доступность конкретных моделей проверяется отдельно.
Без ключа доступны API кампаний и справочники. Изображения — необязательная функция.

Весь проект: `docker compose up --build`. Сервис `migrate` применяет миграции и загружает
синтетику, API запускается после его успеха. Образ API работает под uid 999; рабочие данные
и checkpointer хранятся в постоянном volume. Старые ревизии и таблицы сохранены.

## Работа с кодом

```bash
make check       # ruff, формат, mypy --strict всего app, pytest
make format      # привести код к стилю шаблона
make openapi     # OpenAPI, schemas tools и TS-типы
```

Сервисы не коммитят: запросный UoW сохраняет изменения и аудит одной транзакцией до ответа.
Доменные правила без фреймворков; ORM не выходит из db/service. Общие схемы API/tools —
`app/contracts/`, валидаторы креатива — `app/infra/creative_validation.py`, каталог ошибок —
`app/core/codes.py`. Правила расширения — [AGENTS.md](AGENTS.md).

Агент обращается к API кампаний через HTTP (`CAMPAIGNS_API_URL`). Его tools и граф —
`app/infra/agent/`, промпты — `app/infra/agent/prompts/`, оркестрация чата — `app/service/chat.py`.
Пишущие операции выполняются после явного подтверждения; схемы — [tools.json](../docs/tools.json).
Подробный SSE-контракт — [chat.md](../docs/contracts/chat.md).

## Картинки

Картинки генерируются только по согласию пользователя и необязательны для сценария. Вид выбирает
`IMAGE_MODE`: `illustration` (по умолчанию: предметная иллюстрация), `mixed` (фон баннера паттерном, промо-экран иллюстрацией), `ask`
(агент спрашивает кнопками), `pattern`.

- **Иллюстрация** — растровая модель `IMAGE_MODEL` через `/images/generations`.
- **Фон-паттерн** — SVG от `PATTERN_MODEL` (`app/infra/agent/patterns.py`, промпт `prompts/pattern.md`).
  Тема передаётся только цветом. Ответ проверяется как XML и по белому списку тегов и атрибутов,
  при ошибке модель исправляет SVG, до трёх попыток.
- Если иллюстрация не получилась, вместо неё ставится паттерн. Без ключа модели паттерны отключены.
- Файлы сохраняются в `MEDIA_DIR`, в баннер пишется `/api/media/<файл>`.

Эталонные диалоги: `uv run python -m app.run_dialogs` из backend. Команда использует временную
БД, вызывает живую модель и обновляет транскрипты в `docs/dialogs/transcripts/`.
Обычные тесты внешние модели не вызывают и рабочие данные не изменяют.
