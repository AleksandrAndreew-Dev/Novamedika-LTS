# upload.py - обновленная версия
import os
import re
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import uuid

import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from tasks.tasks_increment import process_csv_incremental

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBasic()
limiter = Limiter(key_func=get_remote_address)

CORRECT_USERNAME = os.getenv("CORRECT_USERNAME")
CORRECT_PASSWORD = os.getenv("CORRECT_PASSWORD")

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".csv"}

# Safe pattern: only alphanumeric, hyphens, underscores allowed
SAFE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def authenticate_pharmacy(credentials: HTTPBasicCredentials = Depends(security)):
    # Проверка конфигурации сервера
    if not CORRECT_USERNAME or not CORRECT_PASSWORD:
        logger.error(
            "Auth credentials not configured: CORRECT_USERNAME/CORRECT_PASSWORD missing"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server auth not configured",
        )

    # безопасное сравнение строк (no need to .encode)
    is_user = secrets.compare_digest(credentials.username, CORRECT_USERNAME)
    is_pass = secrets.compare_digest(credentials.password, CORRECT_PASSWORD)

    if not (is_user and is_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": 'Basic realm="Upload"'},
        )
    return credentials.username


@router.post("/upload/{pharmacy_name}/{pharmacy_number}/")
@limiter.limit("5/minute")
async def upload_file(
    request: Request,
    pharmacy_name: str,
    pharmacy_number: str,
    file: UploadFile = File(...),
    district: str | None = None,
    username: str = Depends(authenticate_pharmacy),
):
    """Загрузка CSV файла аптеки. Максимум 50MB, только CSV.

    Параметры:
    - district: район аптеки (напр. 'Фрунзенский р-н') — извлекается из адреса tabletka.by
    """

    # Sanitize path parameters — prevent path traversal
    if not SAFE_NAME_PATTERN.match(pharmacy_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pharmacy name. Only letters, numbers, hyphens, and underscores allowed.",
        )
    if not SAFE_NAME_PATTERN.match(pharmacy_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pharmacy number. Only letters, numbers, hyphens, and underscores allowed.",
        )

    # Проверка расширения файла (MIME type при upload часто application/octet-stream)
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый формат файла: {ext or 'нет расширения'}. Разрешены только CSV",
        )

    try:
        logger.info(
            f"Starting upload for pharmacy: {pharmacy_name}, number: {pharmacy_number}, user: {username}"
        )

        # Читаем файл как байты
        file_bytes = await file.read()

        # Проверка размера
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Файл слишком большой. Максимум: {MAX_FILE_SIZE // (1024*1024)}MB",
            )

        logger.info(
            f"File: {file.filename}, size: {len(file_bytes)} bytes ({len(file_bytes) / 1024:.1f} KB)"
        )

        # Сохраняем в /app/uploaded_csv (смонтированный volume)
        save_dir = "/app/uploaded_csv"
        os.makedirs(save_dir, exist_ok=True)
        file_name = f"{pharmacy_name}_{pharmacy_number}.csv"
        file_path = os.path.join(save_dir, file_name)

        # Double-check: ensure file_path is within save_dir (defense in depth)
        if not file_path.startswith(save_dir + os.sep):
            logger.critical(f"Path traversal attempt blocked: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path",
            )

        # Просто перезаписываем файл
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # Пробуем разные кодировки
        content = None
        encodings_to_try = ["utf-8", "windows-1251", "cp1251", "iso-8859-5"]

        for encoding in encodings_to_try:
            try:
                content = file_bytes.decode(encoding)
                logger.info(f"Successfully decoded file with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                continue

        # Если ни одна кодировка не подошла, используем utf-8 с заменой ошибок
        if content is None:
            logger.warning(
                "Could not decode file with any encoding, using utf-8 with error replacement"
            )
            content = file_bytes.decode("utf-8", errors="replace")

        # Запускаем задачу Celery
        from tasks.tasks_increment import process_csv_incremental

        try:
            task = process_csv_incremental.delay(
                content, pharmacy_name, pharmacy_number, district
            )
            logger.info(f"Celery task created: {task.id} (district={district})")
        except Exception as celery_error:
            logger.error(
                f"Failed to enqueue Celery task: {celery_error}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="CSV processing service unavailable. Please try again later.",
            )

        return {
            "status": "success",
            "task_id": task.id,
            "message": "File upload processing started",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {type(e).__name__}",
        )
