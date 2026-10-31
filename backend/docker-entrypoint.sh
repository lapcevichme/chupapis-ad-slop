#!/bin/sh
# Запуск контейнера: готовим данные и сбрасываем права до uid 999.
# Том (Fly Volume, Docker volume) монтируется от root, поэтому владельца правим здесь, а не в Dockerfile.
set -eu

if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/data
    chown -R 999:999 /app/data
    exec setpriv --reuid=999 --regid=999 --clear-groups "$0" "$@"
fi

# Миграции и сид идемпотентны: на существующей БД ничего не меняют.
# На Fly их нельзя вынести в release_command: он идёт на временной машине без тома.
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    alembic upgrade head
    python -m app.seed
fi

exec "$@"
