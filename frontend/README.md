# Фронтенд AdPilot AI

```bash
npm install
npm run dev     # http://localhost:5173
npm run build
npm run lint
```

Запросы к `/api/*` Vite проксирует на бэкенд без префикса `/api`. Адрес задаётся переменной `API_PROXY_TARGET`, по умолчанию `http://localhost:8000`.

Дизайн и токены описаны в `docs/ours/design.md`. Для работы нужен бэкенд: `docker compose up backend` из корня репо или `uv run uvicorn app.main:app` в `backend/` (см. `backend/README.md`).

Чат по умолчанию работает на имитации сценария §9 (`src/api/chatMock.ts`): диалог заскриптован, а кампании создаются через настоящий API. Настоящий чат: `VITE_CHAT_MOCK=false npm run dev`.

После смены контракта бэкенда: `uv run python -m app.export_openapi` в `backend/`, затем `npm run gen:api` здесь.
