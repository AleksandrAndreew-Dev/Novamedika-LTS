FROM python:3.12-slim as prod

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    HOME=/app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl wget gcc libpq-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Создаём непривилегированного пользователя
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install --upgrade pip --root-user-action=ignore && pip install uv --root-user-action=ignore
RUN uv sync --frozen --no-cache

# Copy source code
COPY src/ ./src/

# Передаём права на директорию приложения пользователю
RUN chown -R appuser:appgroup /app

# Копируем alembic конфигурацию (на уровень выше src/)
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Копируем entrypoint скрипт
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh && chown appuser:appgroup ./entrypoint.sh

# Переключаемся на непривилегированного пользователя
USER appuser

EXPOSE 8000

# Entry point: сначала миграции, потом команда из CMD
ENTRYPOINT ["/app/entrypoint.sh"]

# Production: gunicorn с uvicorn workers (3 worker для 4 CPU)
CMD ["/app/.venv/bin/gunicorn", "main:app", "-w", "3", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "120", "--graceful-timeout", "30", "--keep-alive", "5", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "warning", "--max-requests", "500", "--max-requests-jitter", "50"]
