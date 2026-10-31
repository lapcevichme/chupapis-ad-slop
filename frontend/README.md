# Фронтенд AdPilot AI

```bash
npm install
npm run dev     # http://localhost:5173
npm run build
npm run lint
```

Запросы к `/api/*` Vite проксирует на бэкенд без префикса `/api`. Адрес задаётся переменной `API_PROXY_TARGET`, по умолчанию `http://localhost:8000`.

Дизайн и токены описаны в `docs/ours/design.md`. Бэкенда пока нет: `src/api/campaigns.ts` отдаёт данные из копии моков в `src/fixtures`.
