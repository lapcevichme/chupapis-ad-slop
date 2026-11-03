# Фронтенд AdPilot AI

```bash
npm install
npm run dev     # http://localhost:5173
npm run build
npm run lint
```

Запросы к `/api/*` Vite проксирует на бэкенд без префикса `/api`. Адрес задаётся переменной `API_PROXY_TARGET`, по умолчанию `http://localhost:8000`.

Дизайн и токены описаны в `docs/ours/design.md`. Для работы нужен бэкенд: `docker compose up backend` из корня репо или `uv run uvicorn app.main:create_app --factory` в `backend/` (см. `backend/README.md`).

Чату нужен `LLM_API_KEY` в `.env` в корне репо, см. `.env.example`.

После смены контракта бэкенда: `uv run python -m app.export_openapi` в `backend/`, затем `npm run gen:api` здесь.
