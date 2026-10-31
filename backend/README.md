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

## Агент

Контракт с фронтом: `docs/ours/chat-api.md`. Код: `app/agent/`, эндпоинты `/chat` — `app/routers/chat.py`.

```text
START → agent ⇄ tools → confirm → agent → … → END
```

- **agent** — чат-модель (`CHAT_MODEL`) с инструментами. Промпт: `app/agent/prompts/chat.md`.
- **tools** — выполняет инструменты чтения, копит пакет операций `propose_*`, шлёт превью (`draft_updated`), шаги (`step`), кнопки и предупреждения.
- **confirm** — `interrupt()` с пакетом. Только этот узел пишет в API, и только после «да» пользователя. Обойти промптом нельзя.
- **Дизайн-агент** (`app/agent/designer.py`, `DESIGN_MODEL`, промпт `prompts/design.md`) — вызывается инструментом `design_creative`. Возвращает JSON баннера и PROMO-экрана, который проверяется теми же схемами, что и API. Ошибки уходят модели обратно, до 3 попыток.
- **Картинки** (`IMAGE_MODEL`) — по согласию пользователя. Файл сохраняется в `data/media`, в баннер пишется `/api/media/<файл>`. Если генерация недоступна, баннер остаётся без картинки.
- Агент ходит в API кампаний по HTTP (`CAMPAIGNS_API_URL`, `app/agent/api_client.py`), а не в БД. Состояние диалогов хранит checkpointer LangGraph в `data/checkpoints.db`.
- LLM спрятана за `app/agent/llm.py`: любой OpenAI-совместимый провайдер, модели меняются переменными окружения.

### Модели (OpenRouter)

| Роль | Модель по умолчанию | Почему |
|---|---|---|
| Чат-агент | `anthropic/claude-haiku-5.5` | Надёжный tool calling на 36 инструментах, быстрый ответ, $0.10/$0.50 за 1M токенов |
| Дизайн-агент | `anthropic/claude-sonnet-5.5` | Строгое следование JSON-схеме и хорошие тексты на русском; вызывается редко |
| Картинки | `openai/gpt-5-image-mini` | ~40 секунд и ~$0.04 за картинку. Модели Google (`gemini-*-image`) отвечают 403 «Blocked by Google AI Studio» для нашего аккаунта |

Если чат-агент путается в длинных сценариях, поставьте `CHAT_MODEL=anthropic/claude-sonnet-5.5`. Качественнее, но дольше и дороже (~85 секунд, ~$0.22) — `openai/gpt-5.4-image-2`.

### Инструменты

Один инструмент на каждый вызов API §3. GET модель вызывает напрямую, пишущие вызовы кладёт в пакет через `propose_*`. Схемы аргументов генерируются из Pydantic-моделей (`app/agent/tools.py`, `app/agent/operations.py`).

| Инструмент | Вызов API |
|---|---|
| `list_topics`, `list_tags`, `list_channels`, `list_banner_types`, `list_segment_types`, `list_segments`, `list_places` | `GET /topics` … `GET /places` |
| `list_campaigns`, `get_campaign`, `get_warnings`, `get_audit` | `GET /campaigns`, `/campaigns/{id}`, `/warnings`, `/audit` |
| `propose_create_campaign`, `propose_update_campaign`, `propose_delete_campaign` | `POST /campaigns`, `PUT`/`DELETE /campaigns/{id}` |
| `propose_set_segments` | `PUT /campaigns/{id}/segments` |
| `propose_create_banner`, `propose_update_banner`, `propose_delete_banner` | `POST`/`PUT`/`DELETE /campaigns/{id}/banners` |
| `propose_create_content`, `propose_update_content`, `propose_delete_content` | `POST`/`PUT`/`DELETE /campaigns/{id}/contents` |
| `propose_create_creative`, `propose_update_creative`, `propose_delete_creative` | `POST`/`PUT`/`DELETE /campaigns/{id}/creatives` |
| `propose_create_place`, `propose_create_tag` | `POST /places`, `POST /tags` |
| `propose_to_moderation`, `propose_decline`, `propose_approve`, `propose_activate`, `propose_stop` | `POST /campaigns/{id}/<действие>` |

Служебные: `design_creative` (дизайн-агент), `request_confirmation` (запрос подтверждения пакета), `discard_pending` (убрать операции до подтверждения), `warn_user` (предупреждение о спорном решении без отказа), `suggest_options` (кнопки-варианты).

Внутри пакета ещё не созданные сущности связываются временными ссылками `tmp-N`, при выполнении они заменяются настоящими id.
