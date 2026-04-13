#!/bin/bash
# celery-entrypoint.sh — запуск Celery worker без alembic миграций
# Миграции выполняет только backend контейнер при старте
set -e

echo "✅ Skipping Alembic migrations (handled by backend service)"

# Запускаем основную команду (переданную через CMD)
exec "$@"
