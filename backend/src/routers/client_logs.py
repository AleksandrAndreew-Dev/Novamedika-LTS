import os
import json
import logging
import hashlib
import time
from datetime import datetime
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["client-logs"])

# Путь по умолчанию = путь, который читает agent/diagnostics.sh
# (см. diagnostics.sh: LOG_FILE=/opt/novamedika-prod/logs/client-errors.jsonl)
CLIENT_LOG_DIR = os.getenv("CLIENT_LOG_DIR", "/opt/novamedika-prod/logs")
CLIENT_LOG_FILE = os.path.join(CLIENT_LOG_DIR, "client-errors.jsonl")

# Дедупликация: одни и те же ошибки не должны спамить логи
# (в логах 20261006 один и тот же URL повторялся десятки раз подряд)
_DEDUP_WINDOW_SECONDS = 60
_recent_errors: dict[str, float] = {}


class ClientError(BaseModel):
    error: str = Field(default="", description="Error message or empty string")
    componentStack: str | None = Field(
        default=None, description="React component stack trace"
    )
    url: str | None = Field(default=None, description="Page URL where error occurred")
    userAgent: str | None = Field(default=None, description="Browser user agent")
    timestamp: str | None = Field(default=None, description="ISO timestamp")


def _short_url(url: str | None) -> str:
    """URL без hash/query (tgWebAppData не должен попадать в логи)."""
    if not url:
        return ""
    return url.split("#", 1)[0].split("?", 1)[0]


def _is_duplicate(error_key: str) -> bool:
    """True, если такая же ошибка уже приходила в последние 60 секунд."""
    now = time.monotonic()
    # Очистка протухших записей (размер ограничен окном дедупликации)
    for key in [k for k, ts in _recent_errors.items() if now - ts > _DEDUP_WINDOW_SECONDS]:
        del _recent_errors[key]

    last = _recent_errors.get(error_key)
    if last is not None and now - last <= _DEDUP_WINDOW_SECONDS:
        return True
    _recent_errors[error_key] = now
    return False


@router.post("/api/log/client-error")
async def log_client_error(payload: ClientError, request: Request):
    """Endpoint for collecting client-side errors from Telegram Web App."""
    try:
        # Сути ошибки в логи: текст ошибки (обрезанный), а НЕ полный URL
        error_text = (payload.error or "").strip()[:500]
        page = _short_url(payload.url)

        # Дедупликация: одинаковая ошибка в течение 60 сек — один раз
        dedup_key = hashlib.sha1(
            f"{error_text}|{page}".encode("utf-8", "ignore")
        ).hexdigest()
        if error_text and _is_duplicate(dedup_key):
            return {"status": "duplicate"}

        os.makedirs(CLIENT_LOG_DIR, exist_ok=True)

        log_entry = {
            "type": "client_error",
            "error": error_text,
            "componentStack": payload.componentStack,
            "url": page or _short_url(str(request.url)),
            "userAgent": payload.userAgent or request.headers.get("user-agent", ""),
            "timestamp": payload.timestamp or datetime.utcnow().isoformat(),
            "ip": request.client.host if request.client else "unknown",
        }

        # Append as JSONL
        with open(CLIENT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        logger.info(
            "Client error from %s: %s",
            log_entry["url"] or "unknown page",
            error_text[:300] or "(empty message)",
        )
        return {"status": "logged"}

    except Exception as e:
        logger.error(f"Failed to log client error: {e}")
        return {"status": "error", "detail": str(e)}
