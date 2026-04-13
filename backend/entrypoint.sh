#!/bin/bash
# entrypoint.sh — запускает alembic миграции перед стартом приложения
set -e

echo "🔄 Running Alembic migrations..."

# Alembic находится в /app/alembic (на уровень выше src/)
cd /app

# Запускаем alembic upgrade head
# alembic.ini ожидает что src/ в sys.path (prepend_sys_path = . в alembic.ini)
/app/.venv/bin/alembic upgrade head

echo "✅ Alembic migrations completed"

# Запускаем основную команду (переданную через CMD или command)
exec "$@"
