#!/bin/bash
# entrypoint.sh — запускает alembic миграции перед стартом приложения
set -e

echo "🔄 Running Alembic migrations..."
cd /app

# Alembic env.py добавляет /app в sys.path самостоятельно (sys.path.insert)
# Не перезаписываем PYTHONPATH — он установлен в Dockerfile как /app/src
/app/.venv/bin/alembic upgrade head 2>&1 || {
    echo "⚠️  Alembic upgrade failed, continuing without migrations..."
}

echo "✅ Alembic migrations step completed"

# Запускаем основную команду (переданную через CMD)
exec "$@"
