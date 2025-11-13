# routers/upload.py (или где у вас endpoint для загрузки)
from fastapi import APIRouter, UploadFile, File, HTTPException, status
import logging
from tasks.tasks_increment import process_csv_incremental

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload/{pharmacy_name}/{pharmacy_number}/")
async def upload_file(
    pharmacy_name: str, pharmacy_number: str, file: UploadFile = File(...)
):
    try:
        logger.info(
            f"Starting upload for pharmacy: {pharmacy_name}, number: {pharmacy_number}"
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
