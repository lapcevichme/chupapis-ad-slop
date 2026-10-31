# Контракты бэкенда

Рабочая памятка для переноса на Monolith-backend-template. Машинный источник —
`frontend/openapi.json`, генерируется из FastAPI; схемы tools — `docs/tools.json`.
Перенос меняет устройство бэкенда, не внешний контракт. Исключения фиксируются здесь
и меняются вместе с фронтендом и инструментами.

## HTTP кампаний

Серверные пути без `/api`; Vite проксирует `/api/*` с удалением префикса. Пользователь —
`X-User`, роль — `X-Role`: `campaignManager` или `campaignModerator`.

| Группа | Операции |
|---|---|
| Справочники | GET `/topics`, `/tags`, `/channels`, `/banner-types`, `/segment-types`, `/segments`, `/places` |
| Создание справочников | POST `/places` и `/tags` |
| Кампания | GET/POST `/campaigns`, GET/PUT/DELETE `/campaigns/{id}` |
| Аудитория | PUT `/campaigns/{id}/segments` |
| Дочерние сущности | POST `/{banners,contents,creatives}`, PUT/DELETE `/{collection}/{childId}` внутри кампании |
| Проверка и история | GET `/campaigns/{id}/warnings`, `/audit` |
| Переходы | POST `/campaigns/{id}/{to-moderation,decline,approve,activate,stop}` |

Всего 31 операция доменного API. Имена `operationId` сохраняются: на них опираются схемы
и генерация клиента. PUT заменяет объект целиком. POST/PUT принимают `topic`, `tags`,
`places` в обёртках `{value,label}`, GET возвращает строку/ID. Время кампаний — UTC.

Ошибки домена и схем запроса: HTTP 400, `{"errors":[{"code","message","field"}]}`.
Несуществующая сущность: 404, `ENTITY_NOT_FOUND`. Формат Problem Details из шаблона
сюда не переносим: это сломало бы текущий клиент и агента.

На каждую запись нужен серверный аудит. Роль проверяется раньше состояния.
`ON_MODERATION` не равен публикации; `published` меняют только activate/stop.
Полные правила — [domain.md](domain.md), первичный источник — `case/Кейс1/task.md`.

## Чат и SSE

| Операция | Результат |
|---|---|
| POST `/chat` с `{campaignId?}` | 201 `{sessionId}`; с кампанией используется диалог пары кампания+логин |
| GET `/chat/{sessionId}` | История, campaignId, draft, validation, pendingConfirmation |
| POST `/chat/{sessionId}/messages` с `{text}` | SSE |
| POST `/chat/{sessionId}/confirmations/{id}` с `{approved,comment?}` | SSE |
| POST `/chat/{sessionId}/retry` | SSE, продолжение сохранённого хода |

События: `message_delta`, `step`, `suggestions`, `confirmation_required`, `draft_updated`,
`campaign_updated`, `warning`, `error`, `done`. Схемы `ChatEvent*` включены в OpenAPI.
Читаем fetch, heartbeat — SSE-комментарий, не пользовательское сообщение.

Модель читает API и предлагает `propose_*`; контролируемый узел исполняет пакет после
подтверждения. Несохранённое превью не является записанной кампанией. Диалог и ожидающее
подтверждение должны переживать перезапуск. Детали payload — [chat-api.md](ours/chat-api.md).

## Служебное и совместимость данных

- `/health` и `/mock/cbro/export` сохраняются. CBRO — успешная локальная заглушка.
- `/media/*` отдаёт файлы; текущий клиентский URL `/api/media/*` сохраняется.
- Существующие SQLite-таблицы и две ревизии Alembic сохраняют имена/идентификаторы.
  Изменение слоёв само по себе не требует сбрасывать БД и диалоги.
- Контрактные тесты сравнивают OpenAPI с сохранённым JSON; сценарные тесты проверяют
  реальные запросы, подтверждения, аудит и роли.

## Границы переноса

Из шаблона берём `api → service → domain`, `db/infra`, UoW и фабрику приложения.
Здесь остаются кампании и существующие роли; регистрация, Redis, S3 и worker добавляются
только под отдельный продуктовый сценарий. Внешние вызовы агента и генерация медиа
не выполняются внутри транзакции кампании.
