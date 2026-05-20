"""
Сервис для безопасной обработки фото рецептов.
Все файлы хранятся на серверах РБ в защищенном хранилище.
"""

import os
import logging
from pathlib import Path
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PrescriptionService:
    """Сервис для управления рецептами"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # Путь к защищенному хранилищу на сервере РБ
        self.storage_path = Path("/opt/novamedika/prescriptions")
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def save_prescription_file(
        self,
        prescription_id: str,
        file_content: bytes,
        filename: str,
    ) -> str:
        """
        Сохраняет фото рецепта в защищенное хранилище.
        
        Args:
            prescription_id: UUID рецепта
            file_content: Содержимое файла
            filename: Имя оригинального файла
            
        Returns:
            Путь к сохраненному файлу
        """
        # Генерируем уникальное имя файла
        file_extension = Path(filename).suffix or ".jpg"
        unique_filename = f"{prescription_id}{file_extension}"
        file_path = self.storage_path / unique_filename
        
        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Устанавливаем права доступа (только для владельца)
        os.chmod(file_path, 0o600)
        
        logger.info(f"Prescription file saved: {file_path}")
        
        return str(file_path)
    
    async def get_prescription_file(self, prescription_id: str) -> bytes:
        """
        Читает фото рецепта из хранилища.
        Только для фармацевтов в режиме просмотра.
        
        Args:
            prescription_id: UUID рецепта
            
        Returns:
            Содержимое файла
            
        Raises:
            FileNotFoundError: Если файл не найден
        """
        from db.prescription_models import Prescription
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(Prescription).where(Prescription.uuid == prescription_id)
        )
        prescription = result.scalar_one_or_none()
        
        if not prescription:
            raise FileNotFoundError(f"Prescription {prescription_id} not found")
        
        file_path = Path(prescription.file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} not found")
        
        with open(file_path, "rb") as f:
            return f.read()
    
    async def delete_prescription_file(self, prescription_id: str):
        """
        Удаляет фото рецепта из хранилища и БД.
        Используется для автоудаления через 48 часов.
        
        Args:
            prescription_id: UUID рецепта
        """
        from db.prescription_models import Prescription
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(Prescription).where(Prescription.uuid == prescription_id)
        )
        prescription = result.scalar_one_or_none()
        
        if not prescription:
            logger.warning(f"Prescription {prescription_id} not found for deletion")
            return
        
        # Удаляем файл из файловой системы
        if prescription.file_path:
            file_path = Path(prescription.file_path)
            if file_path.exists():
                os.remove(file_path)
                logger.info(f"Deleted prescription file: {file_path}")
        
        # Обновляем статус в БД
        prescription.status = "deleted"
        prescription.deleted_at = datetime.utcnow()
        prescription.file_path = None
        
        await self.db.commit()
        
        logger.info(f"Prescription {prescription_id} deleted successfully")
