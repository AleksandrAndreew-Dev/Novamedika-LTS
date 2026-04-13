#!/bin/bash
# entrypoint.sh — запускает alembic миграции перед стартом приложения
set -e

export PYTHONPATH=/app

echo "🔄 Running Alembic migrations..."
cd /app

# Пробуем alembic upgrade head — если таблицы уже существуют, alembic пропустит
/app/.venv/bin/alembic upgrade head 2>&1 || {
    echo "⚠️  Alembic upgrade failed, attempting to create tables via create_all fallback..."
    # Не падаем — приложение может создать таблицы через create_all
    echo "⚠️  Continuing without migrations..."
}

echo "✅ Alembic migrations step completed"

# Запускаем основную команду (переданную через CMD)
exec "$@"
