# AdPilot AI

AI-помощник для создания рекламных кампаний в приложении банка: бриф → подбор справочников
→ кампания и креатив → превью → подтверждение → модерация. SibКод, кейс 1.

## Запуск

```bash
cp .env.example .env  # заполнить LLM_API_KEY для чата
docker compose up --build
```

Интерфейс — http://localhost:5173, API/Swagger — http://localhost:8000/docs.
Миграции и синтетические данные загружаются отдельным шагом перед запуском API.
Без ключа модели доступны API кампаний и интерфейс; полноценный диалог требует провайдера.

## Проверка

```bash
make check
```

Для разработки бэкенда: `make install && make migrate && make seed && make run`.
Для фронтенда: `cd frontend && npm ci && npm run dev` при запущенном API.

Основной сценарий: менеджер `ivanov.p` задаёт бриф, проверяет черновик и подтверждает
сохранение, затем отправку на модерацию. Модератор `petrova.m` одобряет либо возвращает
с комментарием. Правки и переходы журналируются; изображение не обязательно для сценария.

## Деплой

- Фронтенд: Vercel, проект `adpilot-ai`, https://adpilot-ai-navy.vercel.app. `frontend/vercel.json` проксирует `/api/*` на бэкенд, как dev-прокси Vite, поэтому CORS не нужен.
- Бэкенд: Fly.io, приложение `adpilot-ai-api` (`backend/fly.toml`), https://adpilot-ai-api.fly.dev. SQLite, checkpointer и картинки лежат на томе `adpilot_data`, поэтому машина одна (`--ha=false`). Миграции и сид идут при старте контейнера.
- Ключ модели задаётся один раз: `fly secrets set LLM_API_KEY=... -a adpilot-ai-api`. Остальные переменные — в `[env]` файла `fly.toml` или через `fly secrets set`.
- Автодеплой: [.github/workflows/ci.yml](.github/workflows/ci.yml). На каждый PR и пуш идут линтеры, типы, тесты и сборка. После зелёного пуша в `main` деплоятся только изменившиеся части: сначала бэкенд, затем фронт. Нужны секреты репозитория `FLY_API_TOKEN` (`fly tokens create deploy -a adpilot-ai-api`), `VERCEL_TOKEN`, `VERCEL_ORG_ID` и `VERCEL_PROJECT_ID` (из `frontend/.vercel/project.json` после `vercel link`). Без них шаги деплоя пропускаются с предупреждением. Вручную: вкладка Actions → CI → Run workflow.

## Контекст и артефакты

- [Навигация](docs/README.md), [статус проверок](docs/STATUS.md), [решения](docs/DECISIONS.md).
- [Контракт бэкенда](docs/CONTRACTS.md), [архитектура](docs/architecture.md), [backend README](backend/README.md).
- [Продукт](docs/PRODUCT.md), [дизайн](docs/DESIGN.md), [исходный кейс](case/README.md).
- [Схемы tools](docs/tools.json), [промпты](backend/app/infra/agent/prompts/) (чат, дизайн, фон-паттерн),
  [сценарии диалогов](docs/dialogs/), [прежние транскрипты](docs/dialogs/transcripts/).

Перенос бэкенда сохраняет внешний API и данные. Готовность живой модели и интерфейса
к защите проверяется отдельно; актуальные результаты — в STATUS.
