# Сид-данные

Копии моков организаторов (`case/Кейс1/mocks/`) и фикстур фронта (`segments`, `places`, `tags`), которые бэкенд загружает в пустую БД.

Файлов `topics`, `segment_types`, `lifecycle_transitions` в моках нет, они восстановлены из `case/Кейс1/mock-data.md`:

- `topics.json`: подписи `EXTRA`, `FINANCIAL_TIPS`, `RETARGET`, `HINTS`, `OTHER` придуманы, остальные взяты из payload-ов моков.
- `segment_types.json`: названия типов придуманы, коды из `mock-data.md` §1.3.
- `lifecycle_transitions.json`: даты и комментарии из `mock-data.md`, время суток условное. Для 114 известен только `STOP`, для 115 — только факт отклонения по креативу.

Каталог ошибок валидации живёт в коде: `app/core/codes.py`.
