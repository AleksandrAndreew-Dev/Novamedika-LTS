FROM python:3.12-slim as prod

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl wget gcc libpq-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Создаём непривилегированного пользователя
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install --upgrade pip && pip install uv
RUN uv sync --frozen --no-cache

# Install gunicorn для production
RUN /app/.venv/bin/pip install gunicorn

# Copy source code
COPY src/ ./src/

# Передаём права на директорию приложения пользователю
RUN chown -R appuser:appgroup /app

# Переключаемся на непривилегированного пользователя
USER appuser

EXPOSE 8000

# Production: gunicorn с uvicorn workers (3 worker для 4 CPU)
CMD ["/app/.venv/bin/gunicorn", "main:app", \
    "-w", "3", \
    "-k", "uvicorn.workers.UvicornWorker", \
    "-b", "0.0.0.0:8000", \
    "--timeout", "120", \
    "--graceful-timeout", "30", \
    "--keep-alive", "5", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--log-level", "warning"]
