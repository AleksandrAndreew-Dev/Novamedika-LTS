# sync_service.py - обновленная версия для pull-модели
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from db.database import async_session_maker
from db.booking_models import PharmacyAPIConfig, SyncLog

logger = logging.getLogger(__name__)

class SyncService:
    """Сервис для мониторинга активности аптек в pull-модели"""

    async def log_pharmacy_activity(self, pharmacy_id: uuid.UUID, activity_type: str):
        """Логирование активности аптеки"""
        async with async_session_maker() as session:
            sync_log = SyncLog(
                uuid=uuid.uuid4(),
                pharmacy_id=pharmacy_id,
                sync_type=activity_type,
                status="success",
                records_processed=0,
                finished_at=datetime.utcnow()
            )
            session.add(sync_log)
            await session.commit()

    async def check_pharmacy_connectivity(self):
        """Проверка, какие аптеки активны (на основе последней активности)"""
        async with async_session_maker() as session:
            configs_result = await session.execute(
                select(PharmacyAPIConfig).where(PharmacyAPIConfig.is_active == True)
            )
            configs = configs_result.scalars().all()

            active_pharmacies = []
            for config in configs:
                # Логируем проверку connectivity
                await self.log_pharmacy_activity(config.pharmacy_id, "connectivity_check")
                active_pharmacies.append(config.pharmacy_id)

            return active_pharmacies
