FROM python:3.12-slim as prod

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl gcc libpq-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install --upgrade pip && pip install uv
RUN uv sync --frozen --no-cache

# Copy source code
COPY src/ ./src/

EXPOSE 8000

# Use uvicorn directly
CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
