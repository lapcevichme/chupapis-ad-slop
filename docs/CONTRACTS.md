# Контракты бэкенда

Рабочая памятка по внешнему контракту. Машинный источник — `frontend/openapi.json`,
генерируется из FastAPI; схемы tools — `docs/tools.json`. Изменения фиксируются здесь
и вносятся вместе с фронтендом и инструментами.

## HTTP кампаний

Серверные пути без `/api`; Vite проксирует `/api/*` с удалением префикса.

**Авторизация** (вместо заголовков `X-User`/`X-Role` из задания кейса, решение D15). Каждый запрос
доменного API несёт `Authorization: Bearer <access-токен>`; без него 401 `NOT_AUTHENTICATED`. Роль берётся
из аккаунта: `campaignManager`, `campaignModerator` или `admin`.

| Операция | Назначение |
|---|---|
| POST `/auth/register` | Аккаунт менеджера: `{email, username, password}`; можно закрыть `REGISTRATION_ENABLED=false` |
| POST `/auth/login` | `{email, password}` → `{access_token, expires_in}` |
| POST `/auth/refresh` | Ротация refresh-токена; веб — cookie `refresh_token` + заголовок `X-CSRF-Token`, мобильный — `Authorization: Bearer <refresh>` |
| POST `/auth/logout`, `/auth/logout-all` | Завершить сессию / все сессии и выданные токены |
| GET `/users/me` | Текущий пользователь |
| `/admin/users`… | Поиск, бан, смена роли (только `admin`) |

Веб-клиент заголовок `X-Client` не шлёт; мобильному нужен `X-Client: mobile`, тогда refresh-токен приходит в теле.
Коды ошибок авторизации: 401 `NOT_AUTHENTICATED`, `INVALID_TOKEN`, `TOKEN_EXPIRED`, `WRONG_CREDENTIALS`,
`SESSION_REVOKED`, `REFRESH_TOKEN_REUSED`; 403 `ROLE_FORBIDDEN`, `ACCOUNT_BANNED`, `CSRF_FAILED`; 409 `EMAIL_TAKEN`,
`USERNAME_TAKEN`; 429 `RATE_LIMITED`. Остальные операции доменного API не менялись.

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
подтверждение должны переживать перезапуск. Детали payload — [chat-api.md](contracts/chat.md).

## Распознавание речи

`POST /speech/transcriptions` — multipart с полем `file`, ответ `{"text": "..."}`; для тишины текст пустой. Нужен вход, роль не проверяется: ручка ничего не записывает. Ошибки в обычном JSON: 400 `AUDIO_EMPTY`, `AUDIO_TOO_LARGE`, `AUDIO_FORMAT_UNSUPPORTED`; 502 `TRANSCRIPTION_FAILED`; 503 `TRANSCRIPTION_UNAVAILABLE`, если нет ключа или `STT_MODEL` пуст. Клиент подставляет текст в поле ввода и сам сообщение не отправляет.

`POST /speech/synthesis` — тело `{"text": "..."}`, ответ `audio/mpeg`. Нужен вход. Ошибки: 400 `SPEECH_TEXT_EMPTY`, `SPEECH_TEXT_TOO_LONG`; 502 `SYNTHESIS_FAILED`; 503 `SYNTHESIS_UNAVAILABLE`.

`POST /speech/live/sessions` — старт основного голосового режима на GPT-Live. Тело `{"sdp": "<предложение браузера>"}`, ответ 201 `{"sessionId": "...", "sdp": "<ответ>"}`. Нужен вход. Ключ OpenAI остаётся на сервере. Ошибки: 502 `LIVE_VOICE_FAILED`; 503 `LIVE_VOICE_UNAVAILABLE`, если нет `OPENAI_API_KEY`: клиент тогда работает по запасной legacy-схеме. Описание — [gpt-live.md](../design/voice/gpt-live.md).

## Служебное и совместимость данных

- `/health` и `/mock/cbro/export` сохраняются. CBRO — успешная локальная заглушка.
- `POST /media/images` — multipart с полем `file`, только `campaignManager`, ответ 201 `{"url": "/api/media/upload-<hex>.jpg"}`. Формат определяется по содержимому: JPEG или PNG. Ошибки 400: `ROLE_FORBIDDEN`, `IMAGE_EMPTY`, `IMAGE_TOO_LARGE` (больше 5 МБ), `IMAGE_FORMAT_UNSUPPORTED`, `MEDIA_STORAGE_FULL` (все загрузки больше 300 МБ).
- `GET /media/{ключ}` отдаёт файл из S3 без авторизации, с вечным кешем; клиентский URL `/api/media/*` сохраняется.
- База — PostgreSQL, одна начальная ревизия `0001`; идентификаторы кампаний, баннеров, контента и креативов
  из кейса сохранены. Схема — [architecture.md](architecture.md).
- Контрактные тесты сравнивают OpenAPI с сохранённым JSON; сценарные тесты проверяют
  реальные запросы, подтверждения, аудит и роли.

## Студия (расширение продукта)

`POST /studio/generate`: `{document, prompt, count: 1..3}` → `{variants: StudioDocument[]}`. Менеджер, без записи кампаний; отсутствие настройки или ошибка модели возвращаются явно. Схема внутренних слоёв общая для HTTP и AI-инструмента, не является расширением официального JSON банка. Оффер и ссылки изображений модель менять не может.

`POST /studio/documents`: multipart `document` (JSON) + `file` (PNG 2×) → 201 `{id,url,document}`. Только менеджер, лимиты медиа и длины текста проверяются сервером. Файлы неизменяемые, повтор одинакового экспорта возвращает тот же ID. `GET /studio/documents/{id}` восстанавливает документ (нужен вход). Кампания меняется отдельным действующим PUT, её роль/состояние/аудит сохранены. Устройство редактора — [studio.md](studio.md).

## Границы заимствования из шаблона

Из шаблона берём `api → service → domain`, `db/infra`, UoW и фабрику приложения.
Из шаблона же взяты регистрация и JWT, Redis (rate limit), S3 (медиа) и worker (outbox). Внешние вызовы
агента и генерация медиа не выполняются внутри транзакции кампании.

Студия 01.11: слой `illustration` с `symbol` (`coffee/card/travel/car`) выбирает собственный прозрачный 3D-ассет клиента. `POST /studio/generate` также принимает `mode: edit`, `count: 1`, `selectedLayerIds`: правка возвращает новый вариант, неизменность невыделенных слоёв и фона проверяет сервер. Изменять текст можно только у выделенного текстового слоя. В режиме вариантов оффер по-прежнему неизменяем. Это внутренние поля редактора, не enum банковского API.
