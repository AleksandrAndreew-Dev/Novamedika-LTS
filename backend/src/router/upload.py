
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

import logging
from tasks.tasks_increment import process_csv_incremental

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBasic()  # обязательно

CORRECT_USERNAME = os.getenv('CORRECT_USERNAME')
CORRECT_PASSWORD = os.getenv('CORRECT_PASSWORD')

def authenticate_pharmacy(credentials: HTTPBasicCredentials = Depends(security)):
    """Проверка аутентификации BasicAuth"""
    correct_username_bytes = CORRECT_USERNAME.encode("utf8")
    correct_password_bytes = CORRECT_PASSWORD.encode("utf8")

    current_username_bytes = credentials.username.encode("utf8")
    current_password_bytes = credentials.password.encode("utf8")

    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@router.post("/upload/{pharmacy_name}/{pharmacy_number}/")
async def upload_file(
    pharmacy_name: str, pharmacy_number: str, file: UploadFile = File(...),
    username: str = Depends(authenticate_pharmacy)  # Добавляем аутентификацию
):

    try:
        logger.info(
            f"Starting upload for pharmacy: {pharmacy_name}, number: {pharmacy_number}, user: {username}"
        )
        logger.info(f"File: {file.filename}, size: {file.size}")

        # Читаем файл как байты
        file_bytes = await file.read()
        logger.info(f"File read successfully, size: {len(file_bytes)} bytes")

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
        task = process_csv_incremental.delay(content, pharmacy_name, pharmacy_number)
        logger.info(f"Celery task created: {task.id}")

        return {
            "status": "success",
            "task_id": task.id,
            "message": "File upload processing started",
        }

    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}",
        )
