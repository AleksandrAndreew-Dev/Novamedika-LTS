FROM python:3.12-slim AS dev

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl gcc python3-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && pip install uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen

COPY src/ ./src/
WORKDIR /app/src

CMD ["/bin/bash", "-c", "source /app/.venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"]
