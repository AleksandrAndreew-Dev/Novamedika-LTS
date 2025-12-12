# tasks_increment.py — упорядоченные импорты

import os
import sys
import csv
import re
import uuid
import logging
import asyncio
import asyncpg
from pathlib import Path
from datetime import datetime, date, timezone
from io import StringIO
from typing import List, Tuple, Dict, Set, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем все модели, чтобы они были зарегистрированы
from db import Base
from db.models import Pharmacy, Product
from db.booking_models import BookingOrder, PharmacyAPIConfig, SyncLog

# Импорты из проекта
from db.database import init_models, async_session_maker, get_async_connection

logger = logging.getLogger(__name__)

# Глобальная переменная для отслеживания инициализации
_models_initialized = False

# Импортируем общий celery app
from tasks.celery_app import celery

# tasks_increment.py - УЛУЧШЕННАЯ ИНИЦИАЛИЗАЦИЯ

# tasks_increment.py - ЗАМЕНИТЕ initialize_task_models


async def initialize_task_models():
    """Потокобезопасная инициализация с очисткой connection pool"""
    global _models_initialized

    if _models_initialized:
        return

    init_lock = asyncio.Lock()
    async with init_lock:
        if _models_initialized:
            return

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Initializing database models (attempt {attempt + 1}/{max_retries})"
                )

                # Явно закрываем старые соединения перед инициализацией
                from db.database import engine, _engine

                if _engine:
                    try:
                        await _engine.dispose()
                    except:
                        pass

                await init_models()

                # Тестовое соединение с полным закрытием
                async with async_session_maker() as session:
                    await session.execute(select(1))
                    await session.close()

                _models_initialized = True
                logger.info("Database models initialized successfully for Celery")
                return

            except Exception as e:
                logger.error(f"Error initializing models (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    logger.error("All attempts to initialize models failed")
                    raise
                await asyncio.sleep(2**attempt)


# tasks_increment.py - ДОБАВЬТЕ ЭТУ ФУНКЦИЮ


async def get_asyncpg_connection():
    """Создает новое соединение asyncpg для каждой операции"""
    database_url = os.getenv(
        "ASYNCPG_DATABASE_URL",
        "postgresql://novamedika:novamedika@postgres:5432/novamedika_prod",
    )

    # Парсим URL для asyncpg
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgres://", 1)

    return await asyncpg.connect(database_url)


def generate_product_hash(product_data: dict) -> str:
    # Преобразуем дату в строку безопасным способом
    expiry_date = product_data["expiry_date"]
    expiry_date_str = ""
    if expiry_date:
        if isinstance(expiry_date, (datetime, date)):
            expiry_date_str = expiry_date.isoformat()
        else:
            expiry_date_str = str(expiry_date)

    hash_fields = [
        product_data["name"],
        product_data["form"],
        product_data["serial"],
        expiry_date_str,
        product_data["manufacturer"],
        product_data["country"],
    ]
    return str(hash("|".join(str(field) for field in hash_fields)))


def validate_numeric_value(
    value: float, field_name: str, max_value: float = 99999999.99
) -> float:
    """Проверяет и ограничивает числовые значения для полей Numeric"""
    try:
        if abs(value) > max_value:
            logger.warning(
                f"Value {value} for {field_name} exceeds maximum {max_value}. Truncating to {max_value}"
            )
            return max_value if value > 0 else -max_value
        return value
    except (TypeError, ValueError):
        logger.warning(f"Invalid value {value} for {field_name}. Using 0.0")
        return 0.0


@celery.task(bind=True, max_retries=3, soft_time_limit=3600)
def process_csv_incremental(
    self, file_content: str, pharmacy_name: str, pharmacy_number: str
):
    """Синхронная обертка для асинхронной функции с использованием существующего event loop"""
    try:
        # Используем существующий event loop из worker процесса
        loop = asyncio.get_event_loop()

        # Проверяем, не закрыт ли loop
        if loop.is_closed():
            logger.warning("Event loop was closed, creating new one")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Запускаем асинхронную функцию
        if loop.is_running():
            # Если loop уже запущен (редкий случай в Celery), используем create_task
            async def run_async():
                return await process_csv_incremental_async(
                    file_content, pharmacy_name, pharmacy_number
                )

            future = asyncio.run_coroutine_threadsafe(run_async(), loop)
            return future.result(timeout=3600)
        else:
            # Стандартный случай - запускаем в существующем loop
            return loop.run_until_complete(
                process_csv_incremental_async(
                    file_content, pharmacy_name, pharmacy_number
                )
            )

    except Exception as e:
        logger.error(f"Error in process_csv_incremental: {str(e)}")
        raise self.retry(exc=e, countdown=60)


async def process_csv_incremental_async_wrapper(
    file_content: str, pharmacy_name: str, pharmacy_number: str
):
    """Обертка для правильной инициализации и выполнения асинхронного кода"""
    # Используем нашу безопасную инициализацию
    await initialize_task_models()

    # Выполняем основную логику
    return await process_csv_incremental_async(
        file_content, pharmacy_name, pharmacy_number
    )


# tasks_increment.py - КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ


async def process_csv_incremental_async(
    file_content: str, pharmacy_name: str, pharmacy_number: str
):
    try:
        # НЕ инициализируем модели здесь - они уже инициализированы в worker_init
        # await initialize_task_models()

        pharmacy_map = {"novamedika": "Новамедика", "ekliniya": "ЭКЛИНИЯ"}
        normalized_name = pharmacy_map.get(pharmacy_name.lower())
        if not normalized_name:
            raise ValueError(f"Invalid pharmacy: {pharmacy_name}")

        # Используем существующий event loop
        loop = asyncio.get_event_loop()

        # СОЗДАЕМ ОТДЕЛЬНУЮ СЕССИЮ ДЛЯ КАЖДОЙ ОПЕРАЦИИ
        async with async_session_maker() as session:
            # Ищем аптеку по названию и номеру
            result = await session.execute(
                select(Pharmacy).where(
                    and_(
                        Pharmacy.name == normalized_name,
                        Pharmacy.pharmacy_number == str(pharmacy_number),
                    )
                )
            )
            pharmacy = result.scalar_one_or_none()

            if not pharmacy:
                logger.info(
                    f"Creating new pharmacy: {normalized_name}, number: {pharmacy_number}"
                )
                pharmacy = Pharmacy(
                    uuid=uuid.uuid4(),
                    name=normalized_name,
                    pharmacy_number=str(pharmacy_number),
                    chain=normalized_name,
                    city="",
                    address="",
                    phone="",
                    opening_hours="",
                )
                session.add(pharmacy)
                await session.commit()
                await session.refresh(pharmacy)
                logger.info(f"Created new pharmacy: {pharmacy.uuid}")

            logger.info(f"Using pharmacy: {pharmacy.uuid}")

        # Обрабатываем CSV для найденной/созданной аптеки
        csv_data, csv_hashes = process_csv_data_with_hashes(file_content, pharmacy.uuid)

        # Получаем существующие продукты с НОВОЙ сессией
        async with async_session_maker() as session:
            existing_hashes = await get_existing_products_with_hashes(
                session, pharmacy.uuid
            )

        # Определяем изменения
        to_add, to_update, to_remove = compare_products(
            csv_hashes, existing_hashes, csv_data
        )

        logger.info(
            f"Changes: {len(to_add)} to add, {len(to_update)} to update, {len(to_remove)} to remove"
        )

        # Выполняем изменения ТОЛЬКО для продуктов
        stats = await execute_incremental_changes_async(
            to_add, to_update, to_remove, pharmacy.uuid
        )

        return {
            "status": "success",
            "pharmacy_id": str(pharmacy.uuid),
            "stats": stats,
            "processed_rows": len(csv_data),
            "pharmacy_created": not pharmacy,
        }

    except Exception as e:
        logger.error(f"Error in process_csv_incremental_async: {str(e)}")
        raise


def normalize_encoding(text: str) -> str:
    """Нормализация кодировки текста с улучшенной обработкой"""
    if not text:
        return text

    # Если текст уже в UTF-8, возвращаем как есть
    try:
        text.encode("utf-8")
        return text
    except UnicodeEncodeError:
        pass

    # Популярные кодировки для CSV файлов, особенно для русского языка
    encodings = [
        "utf-8",
        "windows-1251",
        "cp1251",
        "iso-8859-5",
        "koi8-r",
        "cp866",
        "maccyrillic",
    ]

    for encoding in encodings:
        try:
            # Пробуем декодировать и закодировать обратно в UTF-8
            encoded = text.encode(encoding, errors="replace")
            return encoded.decode("utf-8", errors="replace")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue

    # Если ни одна кодировка не подошла, возвращаем оригинал с заменой ошибок
    try:
        return text.encode("utf-8", errors="replace").decode("utf-8")
    except:
        return text


def normalize_file_content(file_content: str) -> str:
    """Нормализация всего содержимого файла с определением кодировки"""
    if not file_content:
        return file_content

    # Попробуем определить кодировку по BOM (Byte Order Mark)
    bom_map = {
        b"\xff\xfe": "utf-16-le",
        b"\xfe\xff": "utf-16-be",
        b"\xef\xbb\xbf": "utf-8",
        b"\xff\xfe\x00\x00": "utf-32-le",
        b"\x00\x00\xfe\xff": "utf-32-be",
    }

    # Преобразуем строку в байты через latin-1 (сохраняет все байты)
    try:
        byte_content = file_content.encode("latin-1")

        # Проверяем BOM
        for bom, encoding in bom_map.items():
            if byte_content.startswith(bom):
                try:
                    return byte_content[len(bom) :].decode(encoding)
                except UnicodeDecodeError:
                    continue

        # Пробуем определить кодировку по содержимому
        encodings = ["utf-8", "windows-1251", "cp1251", "iso-8859-5"]

        for encoding in encodings:
            try:
                return byte_content.decode(encoding)
            except UnicodeDecodeError:
                continue

    except Exception as e:
        logger.warning(f"Error detecting encoding: {e}")

    # Если все остальное не удалось, используем нормализацию построчно
    lines = file_content.split("\n")
    normalized_lines = []

    for line in lines:
        normalized_line = normalize_encoding(line)
        normalized_lines.append(normalized_line)

    return "\n".join(normalized_lines)


def normalize_field_value(value: str) -> str:
    """Нормализация значения поля"""
    if not value:
        return ""

    # Нормализуем кодировку
    normalized = normalize_encoding(str(value))

    # Убираем лишние пробелы
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def convert_date_format(date_string: str) -> Optional[date]:
    """Конвертирует строку даты в объект date"""
    if not date_string or not date_string.strip():
        return None

    try:
        # Убираем лишние пробелы
        date_string = date_string.strip()

        # Проверяем, что это действительно дата, а не число или текст
        if re.match(r"^-?\d*\.?\d+$", date_string):  # Число типа "2.26", "230.90"
            logger.warning(f"Skipping numeric value as date: {date_string}")
            return None

        if any(
            keyword in date_string.lower()
            for keyword in ["товар", "мед", "назначен", "техник"]
        ):
            logger.warning(f"Skipping text value as date: {date_string}")
            return None

        # Пробуем разные форматы дат
        formats = [
            "%d.%m.%Y",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d.%m.%y",
            "%d/%m/%y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt).date()
            except ValueError:
                continue

        # Если ни один формат не подошел
        logger.warning(f"Unable to parse date: {date_string}")
        return None

    except Exception as e:
        logger.error(f"Error converting date {date_string}: {str(e)}")
        return None


def process_csv_data_with_hashes(
    file_content: str, pharmacy_uuid: uuid.UUID
) -> Tuple[List[dict], Dict[str, dict]]:
    """Обрабатывает CSV данные и генерирует хеши для сравнения"""
    fieldnames = [
        "name",
        "manufacturer",
        "country",
        "serial",
        "price",
        "quantity",
        "total_price",
        "expiry_date",
        "category",
        "import_date",
        "internal_code",
        "wholesale_price",
        "retail_price",
        "distributor",
        "internal_id",
        "pharmacy_number",
    ]

    # Нормализуем кодировку всего содержимого файла
    normalized_content = normalize_file_content(file_content)
    logger.info(f"Normalized CSV content (first 500 chars): {normalized_content[:500]}")

    # Обработка BOM и невидимых символов
    normalized_content = normalized_content.lstrip("\ufeff").lstrip("\ufffe")

    # Разделяем на строки и обрабатываем каждую вручную для лучшего контроля
    lines = normalized_content.strip().split("\n")
    processed_data = []
    hashes = {}
    processed_products = set()

    for row_num, line in enumerate(lines, 1):
        try:
            # Пропускаем пустые строки
            if not line.strip():
                continue

            # Разделяем строку по точкам с запятой
            fields = line.split(";")

            # Должно быть 15 полей (без pharmacy_number)
            if len(fields) < 15:
                logger.warning(
                    f"Row {row_num} has only {len(fields)} fields, expected 15"
                )
                continue

            # Пропускаем заголовок
            if row_num == 1 and any("name" in str(value).lower() for value in fields):
                continue

            # Создаем словарь с полями
            row = {}
            for i, field_name in enumerate(
                fieldnames[:15]
            ):  # Берем только первые 15 полей из CSV
                if i < len(fields):
                    row[field_name] = fields[i].strip()
                else:
                    row[field_name] = ""

            # Нормализация данных с учетом кодировки
            product_name = normalize_field_value(row["name"])
            if not product_name or product_name.strip() == "":
                continue

            product_form = "-"
            if row.get("category") == "Лексредства":
                product_name, product_form = parse_product_details(product_name)

            # Обработка серийного номера - объединяем поля если их больше одного
            serial_raw = normalize_field_value(row.get("serial", ""))
            if "Поступление" in serial_raw or "РОЦ" in serial_raw:
                # Если в поле serial есть дополнительная информация, извлекаем только числовую часть
                # Ищем паттерны типа "Поступление 16.10.25; РОЦ 0"
                # Мы оставляем это поле как есть, но важно правильно парсить последующие поля
                pass
            serial = re.sub(r"[\s\-_]+", "", serial_raw).upper() if serial_raw else ""

            # Нормализуем остальные текстовые поля
            manufacturer = normalize_field_value(row.get("manufacturer", ""))
            country = normalize_field_value(row.get("country", ""))
            distributor = normalize_field_value(row.get("distributor", ""))
            internal_id = normalize_field_value(row.get("internal_id", ""))
            internal_code = normalize_field_value(row.get("internal_code", ""))

            # Обработка expiry_date - всегда должно быть значение
            expiry_date = None
            if row.get("expiry_date"):
                expiry_date_str = normalize_field_value(row["expiry_date"])
                expiry_date = convert_date_format(expiry_date_str)

            # Если дата не установлена или невалидна, устанавливаем дату по умолчанию
            if not expiry_date:
                # Для медтехники и товаров без срока годности устанавливаем далекую будущую дату
                expiry_date = date(2099, 12, 31)
                logger.info(f"Set default expiry date for product: {product_name}")

            import_date = None
            if row.get("import_date"):
                import_date_str = normalize_field_value(row["import_date"])
                import_date = convert_date_format(import_date_str)

            # Ключевое исправление: правильное определение полей цены и количества
            # В вашем CSV формат: ...;price;quantity;total_price;...
            # Нужно убедиться, что мы берем правильные индексы

            # Получаем значения полей, проверяя их корректность
            price_raw = row.get("price", "0").strip()
            quantity_raw = row.get("quantity", "0").strip()
            total_price_raw = row.get("total_price", "0").strip()

            # Отладочная информация
            logger.debug(
                f"Row {row_num}: price_raw='{price_raw}', quantity_raw='{quantity_raw}', total_price_raw='{total_price_raw}'"
            )

            # Если price содержит "РОЦ 0" или другие проблемы, пытаемся исправить
            if "РОЦ" in price_raw or "Поступление" in price_raw:
                # Если price содержит нечисловые данные, ищем числовое значение в следующих полях
                # Это может быть ошибка смещения полей
                for i in range(4, min(8, len(fields))):
                    field_val = fields[i].strip() if i < len(fields) else ""
                    if re.match(r"^\d+\.?\d*$", field_val) and float(field_val) > 0:
                        price_raw = field_val
                        # Корректируем остальные поля
                        if i + 1 < len(fields):
                            quantity_raw = fields[i + 1].strip()
                        if i + 2 < len(fields):
                            total_price_raw = fields[i + 2].strip()
                        break

            price = validate_numeric_value(safe_float(price_raw), "price")
            quantity = validate_numeric_value(
                safe_float(quantity_raw), "quantity", 9999999.999
            )
            total_price = validate_numeric_value(
                safe_float(total_price_raw), "total_price"
            )
            wholesale_price = validate_numeric_value(
                safe_float(row.get("wholesale_price", "0")), "wholesale_price"
            )
            retail_price = validate_numeric_value(
                safe_float(row.get("retail_price", "0")), "retail_price"
            )

            # Пропускаем дубликаты в CSV
            product_key = (
                product_name,
                serial,
                str(expiry_date) if expiry_date else "",
            )
            if product_key in processed_products:
                continue
            processed_products.add(product_key)

            # Создаем объект продукта
            product_data = {
                "uuid": uuid.uuid4(),
                "name": product_name,
                "form": product_form,
                "manufacturer": manufacturer,
                "country": country,
                "serial": serial,
                "price": price,
                "quantity": quantity,
                "total_price": total_price,
                "expiry_date": expiry_date,
                "category": normalize_field_value(row.get("category", "")),
                "import_date": import_date,
                "internal_code": internal_code,
                "wholesale_price": wholesale_price,
                "retail_price": retail_price,
                "distributor": distributor,
                "internal_id": internal_id,
                "pharmacy_id": pharmacy_uuid,
                "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
            }

            # Генерируем хеш для сравнения
            product_hash = generate_product_hash(product_data)
            hashes[product_hash] = product_data

            processed_data.append(product_data)

            logger.debug(
                f"Processed product: {product_name}, price={price}, quantity={quantity}"
            )

        except Exception as e:
            logger.error(f"Error processing row {row_num}: {e}", exc_info=True)
            continue

    logger.info(f"Processed {len(processed_data)} valid rows from CSV")
    return processed_data, hashes


async def get_existing_products_with_hashes(
    session: AsyncSession, pharmacy_uuid: uuid.UUID
) -> Dict[str, dict]:
    """Асинхронное получение существующих продуктов (включая удаленные)"""
    from sqlalchemy import or_

    # Получаем ВСЕ продукты, включая удаленные
    result = await session.execute(
        select(Product).where(Product.pharmacy_id == pharmacy_uuid)
    )
    existing_products = result.scalars().all()

    existing_hashes = {}
    for product in existing_products:
        product_data = {
            "name": product.name,
            "form": product.form,
            "serial": product.serial,
            "expiry_date": product.expiry_date,
            "manufacturer": product.manufacturer,
            "country": product.country,
        }
        product_hash = generate_product_hash(product_data)
        existing_hashes[product_hash] = {
            "uuid": product.uuid,
            "is_removed": product.is_removed,  # Добавляем флаг удаления
        }

    return existing_hashes


def compare_products(
    csv_hashes: Dict[str, dict],
    existing_hashes: Dict[str, dict],  # Теперь содержит is_removed
    csv_data: List[dict],
) -> Tuple[List[dict], List[dict], List[uuid.UUID]]:
    """Сравнивает CSV данные с существующими и определяет изменения"""
    to_add = []
    to_update = []
    to_remove = []

    # Находим новые продукты (есть в CSV, но нет в базе)
    for product_hash, product_data in csv_hashes.items():
        if product_hash not in existing_hashes:
            to_add.append(product_data)

    # Находим продукты для удаления (есть в базе, но нет в CSV, и НЕ удалены)
    for product_hash, product_info in existing_hashes.items():
        if product_hash not in csv_hashes:
            # Удаляем только если продукт еще не помечен как удаленный
            if not product_info.get("is_removed", False):
                to_remove.append(product_info["uuid"])

    # Находим продукты для обновления (совпадают по хешу)
    for product_hash, product_data in csv_hashes.items():
        if product_hash in existing_hashes:
            existing_info = existing_hashes[product_hash]
            existing_uuid = existing_info["uuid"]
            # Добавляем UUID существующего продукта для обновления
            product_data["existing_uuid"] = existing_uuid
            # Добавляем флаг is_removed для информации
            product_data["is_removed"] = existing_info.get("is_removed", False)
            to_update.append(product_data)

    return to_add, to_update, to_remove


# tasks_increment.py - ИСПРАВЛЕННАЯ ФУНКЦИЯ


async def execute_incremental_changes_async(
    to_add: List[dict],
    to_update: List[dict],
    to_remove: List[uuid.UUID],
    pharmacy_uuid: uuid.UUID,
) -> Dict:
    """Асинхронное выполнение инкрементальных изменений с мягким удалением"""
    stats = {"added": 0, "updated": 0, "removed": 0, "cancelled_orders": 0}

    conn = await get_asyncpg_connection()

    try:
        await conn.execute("BEGIN")

        # ШАГ 1: ОБРАБОТКА УДАЛЯЕМЫХ ПРОДУКТОВ (мягкое удаление)
        if to_remove:
            # Создаем временную таблицу
            await conn.execute(
                """
                CREATE TEMP TABLE products_to_remove (product_uuid UUID PRIMARY KEY)
                """
            )

            # Заполняем временную таблицу
            batch_size = 100
            for i in range(0, len(to_remove), batch_size):
                batch = to_remove[i : i + batch_size]
                values = ",".join([f"('{str(uuid)}')" for uuid in batch])
                await conn.execute(
                    f"""
                    INSERT INTO products_to_remove (product_uuid)
                    VALUES {values}
                    ON CONFLICT (product_uuid) DO NOTHING
                    """
                )

            # 1. Сохраняем данные продукта в заказах перед отвязкой
            await conn.execute(
                """
                UPDATE booking_orders bo
                SET
                    product_name = p.name,
                    product_form = p.form,
                    product_manufacturer = p.manufacturer,
                    product_country = p.country,
                    product_price = p.price,
                    product_serial = p.serial,
                    product_id = NULL
                FROM products p
                WHERE bo.product_id = p.uuid
                AND p.uuid IN (SELECT product_uuid FROM products_to_remove)
                """
            )

            # 2. Отменяем активные заказы на удаляемые продукты
            # Исправлено: убрано RETURNING COUNT(*), используем отдельный запрос
            await conn.execute(
                """
                UPDATE booking_orders
                SET
                    status = 'cancelled',
                    cancelled_at = NOW(),
                    cancellation_reason = 'Товар снят с продажи'
                WHERE product_id IN (SELECT product_uuid FROM products_to_remove)
                AND status IN ('pending', 'confirmed')
                """
            )

            # Получаем количество отмененных заказов отдельным запросом
            cancelled_orders = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM booking_orders
                WHERE product_id IN (SELECT product_uuid FROM products_to_remove)
                AND status = 'cancelled'
                AND cancelled_at >= NOW() - INTERVAL '1 minute'
                """
            )
            stats["cancelled_orders"] = cancelled_orders or 0
            logger.info(f"Cancelled {cancelled_orders} active orders")

            # 3. Мягкое удаление продуктов
            # Исправлено: убрано RETURNING COUNT(*), используем отдельный запрос
            await conn.execute(
                """
                UPDATE products
                SET
                    is_removed = TRUE,
                    removed_at = NOW(),
                    quantity = 0,
                    updated_at = NOW()
                WHERE uuid IN (SELECT product_uuid FROM products_to_remove)
                AND pharmacy_id = $1
                AND is_removed = FALSE
                """,
                str(pharmacy_uuid),
            )

            # Получаем количество удаленных продуктов отдельным запросом
            removed_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM products
                WHERE uuid IN (SELECT product_uuid FROM products_to_remove)
                AND pharmacy_id = $1
                AND is_removed = TRUE
                """,
                str(pharmacy_uuid),
            )
            stats["removed"] = removed_count or 0

            await conn.execute("DROP TABLE products_to_remove")
            logger.info(f"Soft removed {stats['removed']} products")

        # ШАГ 2: ВОССТАНОВЛЕНИЕ И ОБНОВЛЕНИЕ ПРОДУКТОВ
        if to_update:
            for product in to_update:
                updated_at = product["updated_at"]
                if updated_at and updated_at.tzinfo is not None:
                    updated_at = updated_at.replace(tzinfo=None)

                # Восстанавливаем удаленные продукты
                await conn.execute(
                    """
                    UPDATE products SET
                        name = $1, form = $2, manufacturer = $3, country = $4,
                        serial = $5, price = $6, quantity = $7, total_price = $8,
                        expiry_date = $9, category = $10, import_date = $11,
                        internal_code = $12, wholesale_price = $13, retail_price = $14,
                        distributor = $15, internal_id = $16, updated_at = $17,
                        is_removed = FALSE, removed_at = NULL  -- Восстанавливаем
                    WHERE uuid = $18 AND pharmacy_id = $19
                    """,
                    product["name"],
                    product["form"],
                    product["manufacturer"],
                    product["country"],
                    product["serial"],
                    float(product["price"]),
                    float(product["quantity"]),
                    float(product["total_price"]),
                    product["expiry_date"],
                    product["category"],
                    product["import_date"],
                    product["internal_code"],
                    float(product["wholesale_price"]),
                    float(product["retail_price"]),
                    product["distributor"],
                    product["internal_id"],
                    updated_at,
                    str(product["existing_uuid"]),
                    str(pharmacy_uuid),
                )
            stats["updated"] = len(to_update)
            logger.info(f"Updated {len(to_update)} products")

        # ШАГ 3: ДОБАВЛЕНИЕ НОВЫХ ПРОДУКТОВ
        if to_add:
            batch_size = 25
            for i in range(0, len(to_add), batch_size):
                batch = to_add[i : i + batch_size]
                values_placeholders = []
                params = []
                param_counter = 1

                for product in batch:
                    if product["expiry_date"] is None:
                        product["expiry_date"] = date(2099, 12, 31)

                    placeholders = []
                    for field in [
                        "uuid",
                        "name",
                        "form",
                        "manufacturer",
                        "country",
                        "serial",
                        "price",
                        "quantity",
                        "total_price",
                        "expiry_date",
                        "category",
                        "import_date",
                        "internal_code",
                        "wholesale_price",
                        "retail_price",
                        "distributor",
                        "internal_id",
                        "pharmacy_id",
                        "updated_at",
                        "is_removed",
                        "removed_at",
                    ]:
                        placeholders.append(f"${param_counter}")

                        if field == "updated_at":
                            value = product.get(field)
                            if value and value.tzinfo is not None:
                                value = value.replace(tzinfo=None)
                        elif field in [
                            "price",
                            "quantity",
                            "total_price",
                            "wholesale_price",
                            "retail_price",
                        ]:
                            value = float(product.get(field, 0))
                        elif field == "is_removed":
                            value = False
                        elif field == "removed_at":
                            value = None
                        else:
                            value = product.get(field)

                        params.append(value)
                        param_counter += 1

                    values_placeholders.append(f"({', '.join(placeholders)})")

                query = f"""
                    INSERT INTO products (
                        uuid, name, form, manufacturer, country, serial, price, quantity,
                        total_price, expiry_date, category, import_date, internal_code,
                        wholesale_price, retail_price, distributor, internal_id,
                        pharmacy_id, updated_at, is_removed, removed_at
                    ) VALUES {', '.join(values_placeholders)}
                """
                await conn.execute(query, *params)
            stats["added"] = len(to_add)
            logger.info(f"Added {len(to_add)} new products")

        await conn.execute("COMMIT")
        logger.info(f"Changes completed: {stats}")
        return stats

    except Exception as e:
        await conn.execute("ROLLBACK")
        logger.error(f"Error executing incremental changes: {str(e)}")
        raise
    finally:
        await conn.close()


# Вспомогательные функции
def safe_float(value: str) -> float:
    """Безопасное преобразование в float"""
    if not value:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0


def parse_product_details(product_string: str) -> Tuple[str, str]:
    form_keywords = [
        "КАПС",
        "КАПС.",
        "КАПС.,",
        "КАПС,",
        "АМП",
        "ТАБЛ",
        "ТАБЛ.",
        "ТАБЛ,",
        "ТАБЛ.П/О",
        "ТАБЛ.РАСТВ.",
        "МАЗЬ",
        "СУПП",
        "ГЕЛЬ",
        "КАПЛИ",
        "ФЛ",
        "Р-Р",
        "ТУБА",
        "уп",
        "паста",
        "пак",
        "пак.,",
        "пак.",
        "пор",
        "пор.",
        "жев.табл",
        "жев.табл.",
        "фильтр-пакет",
        "фильтр-пакет,",
        "табл.шип",
        "ТАБЛ.РАССАС",
        "конт",
        "крем",
        "табл.жев",
        "драже",
        "ф-кап",
        "линим",
        "капс.рект",
        "фл.,",
        "супп.ваг",
        "саше",
        "пастилки",
    ]

    if not product_string:
        return "-", "-"

    # Ищем ключевые слова формы как отдельные слова (с пробелом перед ними)
    # Это предотвратит обрезку "КАПС" в названии "ЭССЕНЦИКАПС"
    form_regex = re.compile(
        r"\s(" + "|".join(re.escape(kw) for kw in form_keywords) + r")([\s\.,].*)?$",
        re.IGNORECASE,
    )

    match = form_regex.search(product_string)
    if match:
        # Форма найдена как отдельное слово
        form_start = match.start(1)  # Используем start(1) для группы с ключевым словом
        name_part = product_string[:form_start].strip()
        form_part = product_string[form_start:].strip()
        form_part = re.sub(r"^[\s\.,]+", "", form_part)
        return (name_part if name_part else "-", form_part)

    # Если не нашли форму как отдельное слово, проверяем специальные случаи
    # Для "ЭССЕНЦИКАПС КАПС., №50" - "КАПС.," это форма
    if "КАПС.," in product_string:
        # Разделяем по "КАПС.,"
        parts = product_string.split("КАПС.,", 1)
        if len(parts) == 2:
            name_part = parts[0].strip()
            form_part = "КАПС., " + parts[1].strip()
            return (name_part if name_part else "-", form_part)

    # Также проверяем другие варианты с "КАПС"
    if re.search(r"\bКАПС[\.\,]", product_string, re.IGNORECASE):
        # Находим позицию "КАПС" с точкой или запятой
        match = re.search(r"\b(КАПС[\.\,])", product_string, re.IGNORECASE)
        if match:
            form_start = match.start()
            name_part = product_string[:form_start].strip()
            form_part = product_string[form_start:].strip()
            return (name_part if name_part else "-", form_part)

    return (product_string, "-")


@celery.task
def sync_pharmacy_orders_task():
    """Периодическая задача для синхронизации заказов"""
    # Импортируем здесь чтобы избежать циклических импортов
    from backend.src.tasks.sync_service import SyncService

    sync_service = SyncService()

    # Запускаем в event loop для async функций
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(sync_service.sync_all_pharmacies_orders())


@celery.task
def retry_failed_orders_task():
    """Повторная отправка неудачных заказов"""
    # Импортируем здесь чтобы избежать циклических импортов
    from backend.src.tasks.sync_service import SyncService

    sync_service = SyncService()

    # Запускаем в event loop для async функций
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(sync_service.retry_failed_orders())


celery.conf.beat_schedule = {
    "sync-orders-every-10-min": {
        "task": "celery_app.sync_pharmacy_orders_task",
        "schedule": 600.0,
    },
    "retry-failed-orders-every-5-min": {
        "task": "celery_app.retry_failed_orders_task",
        "schedule": 300.0,
    },
}
