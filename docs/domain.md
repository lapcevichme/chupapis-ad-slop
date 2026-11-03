# Домен и контракт без типичных ловушек

Памятка по [task.md](../case/Кейс1/task.md) и [mock-data.md](../case/Кейс1/mock-data.md). Не заменяет исходные схемы и не вводит новых требований.

## Сущности

`CAMPAIGN` содержит шапку, места, включённые/исключённые сегменты; имеет несколько `BANNER`, `CONTENT` и `CREATIVE`. `CREATIVE` связывает баннер, необязательный контент и канал. Место не привязано к креативу напрямую: покрытие проверяется по типу баннера (`task.md` §§2.1–2.9).

Обязательная шапка: уникальное непустое имя ≤100, начало date+`HH:mm`, topic, audienceType, ≥1 место. `weight=0`, `initialCtr=15` — серверные дефолты. MarketingName ≤100, keywords ≤512; конец необязателен, при наличии позже начала. Даты и время — UTC.

| Справочник | Чтение / создание |
|---|---|
| TOPIC, 11; CHANNEL, 3; BANNER_TYPE, 2; SEGMENT_TYPE, 8; SEGMENT, 40 | Только чтение |
| PLACE, исходно 8 | Можно создать `{code, description}`; сервер назначает id, ACTIVE, без defaultBanner |
| TAG, исходно 6 | Можно создать `{name}`; id назначает сервер |

Создание места/тега и последующая привязка требуют показанного предложения и подтверждения. Недостающий сегмент не создаём (`task.md` §10.4).

## Аудитория

- `ALL_USERS`: оба списка сегментов пусты.
- `SEGMENTED`: ≥1 включение; включения соединяются **OR**, исключения вычитаются.
- Выбираются только `ACTIVE`. `SEG_DRAFT_WINTER` имеет `NEW`, count=0, не подходит.
- Смена на `ALL_USERS` требует сначала очистить сохранённые сегменты, затем заменить шапку.

## Баннер и PROMO

| Проверка | Правило |
|---|---|
| Тип и лимиты | STORY: title≤100, text≤500, iOS/ANDROID; SMART_BANNER: title≤250, text≤1000, iOS/ANDROID/WEB |
| Минимальный баннер | `{"actionType":"default"}` валиден; текст/изображение/кнопка опциональны |
| Стиль текста | fontSize 10–40; fontWeight из enum §2.6; цвета `#RRGGBBAA` |
| Действие | `default`, `externalLink`, `openSmartLink`, `closeCampaign`, `doneCampaign` |
| Ссылка | Нужна при externalLink/openSmartLink; запрещена при closeCampaign/doneCampaign |
| Платформы | Каналы: `iOS`, `ANDROID`, `WEB`; **ключи link другие**: `iOS`, `android`, `web` |
| Частичные ссылки | Разрешены; соответствие ключа link каналу креатива в MVP не проверяется |
| Медиа | По исходной схеме https; локальный `/api/media/` — расширение старой реализации, не правило задания |
| PROMO | `{role:"promo", component:{role:"linearContainer", axis:"v", components:[...]}}`, 1–6 компонентов |
| Компоненты | text с обязательным format `none`/`html`; image с обязательным url; button с actionType и правилами link |
| Креатив | bannerId + optional contentId + channelCode; уникальна тройка campaign+banner+channel |

`aligns`, HTML-подмножество, aspectRatio и стили контейнера не получают придуманных серверных ограничений: исходный каталог ошибок для них не задаёт проверок (§2.7). При этом UI не должен исполнять произвольный HTML от модели; текущий безопасный парсер поддерживает только `<b>`.

## Жизненный цикл

```text
DRAFT ─to-moderation→ ON_MODERATION ─approve→ APPROVED ─activate→ ACTIVE
                          │                                      │
                       decline                                 правка
                          ↓                                      ↓
                      NEEDS_WORK ─to-moderation→ …          ACTIVE_EDITING
                                                              │
                                                        to-moderation→ …
```

| Действие | Предусловие | Результат |
|---|---|---|
| Создать | campaignManager | DRAFT, published=false |
| Править | DRAFT / NEEDS_WORK / APPROVED / ACTIVE / ACTIVE_EDITING | APPROVED→DRAFT; ACTIVE→ACTIVE_EDITING; остальные сохраняют позицию |
| На модерацию | DRAFT / NEEDS_WORK / ACTIVE_EDITING, errors пусты | ON_MODERATION |
| Approve / decline | campaignModerator, ON_MODERATION; для decline обязателен comment | APPROVED / NEEDS_WORK |
| Activate | campaignManager, APPROVED | ACTIVE, published=true, успешный CBRO-export |
| Stop | campaignManager, published=true, независимо от позиции в конвейере | STOPPED, published=false |
| Delete | campaignManager, DRAFT / NEEDS_WORK и published=false | Удаление |

Сервер сначала проверяет роль, затем состояние; при двух нарушениях возвращается `ROLE_FORBIDDEN`. Все пишущие операции, кроме approve/decline, доступны менеджеру. `STOPPED` не редактируется и не возобновляется. `ARCHIVED` только объявлен в enum.

`published` меняют только activate/stop. Переходы повторной модерации не останавливают старый показ. Замена JSON в паспорте ещё не означает публикацию новой версии. Правку дочерних сущностей сервер должен учитывать при повторной модерации; текущее применение тех же переходов — решение команды, отмеченное в [DECISIONS.md](DECISIONS.md).

## API и ошибки

§3 перечисляет **31 операцию**: 7 GET-справочников, 2 POST справочников и 22 операции кампаний/детей. Это 11 чтений и 20 записей. Необходима схема и соответствующий инструмент для каждой; служебные UI-tools не заменяют покрытие API.

- POST/PUT: topic, tags, places — `{value,label}`. Для place label равен **code**, а не description. GET: topic — строка, tags/places — id.
- Каждый PUT — полная замена. Частичное изменение: GET → изменение → PUT полного объекта; чтение перед правкой защищает от потери остальных полей.
- Каждый запрос по заданию содержит `X-User` и `X-Role`; ответ возвращает эти заголовки. В текущем коде GET без заголовков разрешён — отличие реализации, не основание убирать заголовки у клиента.
- Бизнес-ошибки: HTTP 400, `{"errors":[{"code","message","field"}]}`. Несуществующая сущность: 404, `ENTITY_NOT_FOUND`.
- Errors блокируют модерацию; warnings не блокируют. Пустые баннеры/креативы кампании 104 — пример допустимого серверного состояния с warning.

Warning `PLACE_NO_CREATIVE`: для каждого места нужен хотя бы один креатив с `bannerType.code == place.defaultBanner`. Не требуется по креативу на каждый канал. Место без defaultBanner считается покрытым. Другие warnings — неактивные места и отсутствие тегов (`mock-data.md` §7).

Аудит — серверная таблица всех записей и переходов: сущность, id, действие, diff, UTC-время, actor, comment. Комментарий модератора читаем из аудита, отдельного поля кампании нет. Полный формат — §3; для CREATE/переходов changes=null. Журнал переходов в моках — только часть полного аудита.

## Эталонные данные

101/108 — проверка заведомо невалидного баннера на редактируемом черновике; 103 — минимальный payload, креатив без контента валиден; 104 — цикл decline→исправление и три warnings; 106/109 — published=true при ACTIVE_EDITING; 107 — APPROVED; 114 — замороженный STOPPED. Новые ограничения должны сохранять эти эталоны.
