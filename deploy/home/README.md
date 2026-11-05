# Домашний сервер: размещение AdPilot AI

Внутренний файл (не часть сдачи: локальный запуск идёт через корневой `docker-compose.yml`).

Весь стек (PostgreSQL, Redis, S3, миграции, API, воркер и веб-приложение) работает на домашнем сервере под Coolify на одном домене: **https://adpilot.prooood.ru** (приложение, `/api/docs` со Swagger, `/api/health`).

```text
push в main → GitHub Actions: сборка образов linux/amd64 → GHCR (тег = SHA коммита)
            → вход в Tailscale (временный узел tag:ci) → SSH с ограниченным ключом
            → сервер ставит IMAGE_TAG=<sha>, Coolify перезапускает стек, ждёт healthy
            → Actions проверяет публичный https://adpilot.prooood.ru/api/health
```

- [`../../.github/workflows/deploy-home.yml`](../../.github/workflows/deploy-home.yml): сборка и деплой. Деплой выполняется только из `main`; с ветки `deploy/home-server` образы лишь собираются.
- [`frontend.Dockerfile`](frontend.Dockerfile): боевой образ веб-приложения (статическая сборка за nginx). Dockerfile в `frontend/` запускает dev-сервер Vite и остаётся для локальной разработки.
- [`nginx.conf`](nginx.conf): раздаёт статику и проксирует `/api/*` в бэкенд с отрезанием префикса, как dev-прокси Vite; ответы чата идут потоком (SSE) без буферизации.

Секреты GitHub Actions: `SARA_DEPLOY_KEY`, `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET`; переменные: `SARA_TAILSCALE_IP`, `SARA_HOST_KEY`, `ADPILOT_HOST`. Ключи LLM и пароли хранятся только на сервере (переменные сервиса в Coolify), в репозиторий не попадают. Как устроены сервер, Tailscale и compose: `docs/DEPLOY-GUIDE.md` в проекте sara-hosting на Mac владельца (`/Users/laughinme/Code/python/sara-hosting`).
