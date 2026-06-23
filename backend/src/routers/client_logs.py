import os
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["client-logs"])

# Путь для сохранения клиентских логов (tmp — гарантированно writable)
CLIENT_LOG_DIR = os.getenv("CLIENT_LOG_DIR", "/tmp/novamedika-client-logs")
CLIENT_LOG_FILE = os.path.join(CLIENT_LOG_DIR, "client-errors.jsonl")


class ClientError(BaseModel):
    error: str = Field(default="", description="Error message or empty string")
    componentStack: str | None = Field(
        default=None, description="React component stack trace"
    )
    url: str | None = Field(default=None, description="Page URL where error occurred")
    userAgent: str | None = Field(default=None, description="Browser user agent")
    timestamp: str | None = Field(default=None, description="ISO timestamp")


@router.post("/api/log/client-error")
async def log_client_error(payload: ClientError, request: Request):
    """Endpoint for collecting client-side errors from Telegram Web App."""
    try:
        os.makedirs(CLIENT_LOG_DIR, exist_ok=True)

        log_entry = {
            "type": "client_error",
            "error": payload.error,
            "componentStack": payload.componentStack,
            "url": payload.url or str(request.url),
            "userAgent": payload.userAgent or request.headers.get("user-agent", ""),
            "timestamp": payload.timestamp or datetime.utcnow().isoformat(),
            "ip": request.client.host if request.client else "unknown",
        }

        # Append as JSONL
        with open(CLIENT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        logger.info(f"Client error logged from {log_entry['url']}")
        return {"status": "logged"}

    except Exception as e:
        logger.error(f"Failed to log client error: {e}")
        return {"status": "error", "detail": str(e)}
