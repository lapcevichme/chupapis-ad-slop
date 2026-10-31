# Бэкенд AdPilot AI

Заглушка API кампаний по §3 `docs/oragnisators/task.md`: справочники, кампании и дочерние сущности, жизненный цикл, роли, валидация, аудит, CBRO-заглушка. Данные — моки организаторов из `seed/`.

```bash
docker compose up --build                  # из корня репо: бэкенд на :8000, фронт на :5173
uv run pytest                              # тесты
uv run alembic upgrade head                # миграции
uv run python -m app.seed                  # загрузить моки в пустую БД
uv run uvicorn app.main:app --reload       # локальный запуск
uv run python -m app.export_openapi        # обновить frontend/openapi.json после смены контракта
```

Swagger: http://localhost:8000/docs.

## Устройство

- `app/schemas/creative_json.py` — JSON-схемы баннера и PROMO-контента. Ими же агент проверяет сгенерированный креатив до отправки.
- `app/domain/creatives.py` — правила поверх схемы: лимиты по типу баннера, `actionType` ↔ `link`, https у картинок.
- `app/domain/validation.py` — прогон всей кампании для `GET /warnings` и `to-moderation`.
- `app/domain/lifecycle.py` — переходы состояний. Роль проверяется раньше состояния.
- `app/domain/rules.py` — каталог кодов ошибок и warnings.
- `app/routers/` — эндпоинты. `operationId` равен имени функции.

Решения, которых нет в задании явно:

- Правка баннера, контента, креатива или сегментов меняет состояние так же, как правка шапки: `APPROVED → DRAFT`, `ACTIVE → ACTIVE_EDITING`. Иначе одобренную кампанию можно было бы изменить без повторной модерации.
- Баннер или контент, на который ссылается креатив, не удаляется (`BANNER_IN_USE`, `CONTENT_IN_USE`).
- Дата и время окончания задаются только вместе (`END_DATETIME_INCOMPLETE`).
- Ошибки схемы запроса отдаются как 400 с кодами каталога, а не как 422 FastAPI.
- `X-User` обязателен для пишущих запросов, GET работают без заголовков.
