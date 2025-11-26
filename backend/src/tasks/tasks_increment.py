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

from celery import Celery
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

async def initialize_task_models():
    """Потокобезопасная инициализация моделей с улучшенной обработкой ошибок"""
    global _models_initialized

    if _models_initialized:
        return

    # Используем блокировку на уровне модуля
    import asyncio
    init_lock = asyncio.Lock()

    async with init_lock:
        # Double-check pattern
        if _models_initialized:
            return

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Initializing database models (attempt {attempt + 1}/{max_retries})")
                await init_models()

                # Тестовое соединение с базой
                async with async_session_maker() as session:
                    await session.execute(select(1))

                _models_initialized = True
                logger.info("Database models initialized successfully for Celery")
                return

            except Exception as e:
                logger.error(f"Error initializing models (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    logger.error("All attempts to initialize models failed")
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

redis_password = os.getenv('REDIS_PASSWORD', '')

celery = Celery(
    'tasks',
    broker=f'redis://:{redis_password}@redis:6379/0',
    backend=f'redis://:{redis_password}@redis:6379/0'
)

# Важные настройки Celery для стабильности
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_ignore_result=False,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
)

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
    """Синхронная обертка для асинхронной функции с изолированным event loop"""
    try:
        # Создаем новый event loop для каждой задачи
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                process_csv_incremental_async_wrapper(file_content, pharmacy_name, pharmacy_number)
            )
            return result
        finally:
            loop.close()
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
    return await process_csv_incremental_async(file_content, pharmacy_name, pharmacy_number)

async def process_csv_incremental_async(
    file_content: str, pharmacy_name: str, pharmacy_number: str
):
    try:
        pharmacy_map = {"novamedika": "Новамедика", "ekliniya": "ЭКЛИНИЯ"}
        normalized_name = pharmacy_map.get(pharmacy_name.lower())
        if not normalized_name:
            raise ValueError(f"Invalid pharmacy: {pharmacy_name}")

        # Создаем новую сессию для каждой задачи
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

            # ЕСЛИ АПТЕКА НЕ НАЙДЕНА - СОЗДАЕМ НОВУЮ
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
                    opening_hours=""
                )
                session.add(pharmacy)
                await session.commit()
                await session.refresh(pharmacy)
                logger.info(f"Created new pharmacy: {pharmacy.uuid}")

            logger.info(f"Using pharmacy: {pharmacy.uuid}")

            # ЗАКРЫВАЕМ СЕССИЮ перед массовыми операциями
            await session.close()

        # Обрабатываем CSV для найденной/созданной аптеки
        csv_data, csv_hashes = process_csv_data_with_hashes(
            file_content, pharmacy.uuid
        )

        # Получаем существующие продукты с НОВОЙ сессией
        async with async_session_maker() as session:
            existing_hashes = await get_existing_products_with_hashes(
                session, pharmacy.uuid
            )
            await session.close()

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

    reader = csv.DictReader(
        StringIO(normalized_content), fieldnames=fieldnames, delimiter=";"
    )
    processed_data = []
    hashes = {}
    processed_products = set()

    for row_num, row in enumerate(reader, 1):
        try:
            # Пропускаем пустые строки и заголовки
            if not any(row.values()) or (
                row_num == 1
                and any("name" in str(value).lower() for value in row.values())
            ):
                continue

            # Нормализация данных с учетом кодировки
            product_name = normalize_field_value(row["name"])
            if not product_name or product_name.strip() == "":
                continue

            product_form = "-"
            if row.get("category") == "Лексредства":
                product_name, product_form = parse_product_details(product_name)

            serial = (
                re.sub(r"[\s\-_]+", "", normalize_field_value(row["serial"])).upper()
                if row.get("serial")
                else ""
            )

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

            # Пропускаем дубликаты в CSV
            product_key = (
                product_name,
                serial,
                str(expiry_date) if expiry_date else "",
            )
            if product_key in processed_products:
                continue
            processed_products.add(product_key)

            price = validate_numeric_value(safe_float(row.get("price")), "price")
            quantity = validate_numeric_value(
                safe_float(row.get("quantity")), "quantity", 9999999.999
            )
            total_price = validate_numeric_value(
                safe_float(row.get("total_price")), "total_price"
            )
            wholesale_price = validate_numeric_value(
                safe_float(row.get("wholesale_price")), "wholesale_price"
            )
            retail_price = validate_numeric_value(
                safe_float(row.get("retail_price")), "retail_price"
            )

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

        except Exception as e:
            logger.error(f"Error processing row {row_num}: {e}")
            continue

    logger.info(f"Processed {len(processed_data)} valid rows from CSV")
    return processed_data, hashes


async def get_existing_products_with_hashes(
    session: AsyncSession, pharmacy_uuid: uuid.UUID
) -> Dict[str, uuid.UUID]:
    """Асинхронное получение существующих продуктов"""
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
        existing_hashes[product_hash] = product.uuid

    return existing_hashes


def compare_products(
    csv_hashes: Dict[str, dict],
    existing_hashes: Dict[str, uuid.UUID],
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

    # Находим продукты для удаления (есть в базе, но нет в CSV)
    for product_hash, product_uuid in existing_hashes.items():
        if product_hash not in csv_hashes:
            to_remove.append(product_uuid)

    # Находим продукты для обновления (совпадают по хешу, но разные данные)
    for product_hash, product_data in csv_hashes.items():
        if product_hash in existing_hashes:
            existing_uuid = existing_hashes[product_hash]
            # Добавляем UUID существующего продукта для обновления
            product_data["existing_uuid"] = existing_uuid
            to_update.append(product_data)

    return to_add, to_update, to_remove


async def execute_incremental_changes_async(
    to_add: List[dict],
    to_update: List[dict],
    to_remove: List[uuid.UUID],
    pharmacy_uuid: uuid.UUID,
) -> Dict:
    """Асинхронное выполнение инкрементальных изменений с правильным управлением соединениями"""
    stats = {"added": 0, "updated": 0, "removed": 0}

    try:
        # Используем переменную из окружения
        database_url = os.getenv('ASYNCPG_DATABASE_URL', "postgresql://novamedika:novamedika@postgres:5432/novamedika_prod")
        conn = await asyncpg.connect(database_url)

        try:
            # Удаление продуктов пакетами
            if to_remove:
                batch_size = 500  # Уменьшим размер батча еще больше
                for i in range(0, len(to_remove), batch_size):
                    batch = to_remove[i : i + batch_size]
                    placeholders = ",".join([f"${j+1}" for j in range(len(batch))])
                    query = f"""
                        DELETE FROM products
                        WHERE uuid IN ({placeholders}) AND pharmacy_id = ${len(batch)+1}
                    """
                    await conn.execute(
                        query, *[str(uuid) for uuid in batch], str(pharmacy_uuid)
                    )
                stats["removed"] = len(to_remove)
                logger.info(f"Removed {len(to_remove)} products")

            # Обновление продуктов пакетами
            if to_update:
                batch_size = 50  # Уменьшим размер батча для обновлений
                for i in range(0, len(to_update), batch_size):
                    batch = to_update[i : i + batch_size]
                    for product in batch:
                        updated_at = product["updated_at"]
                        if updated_at and updated_at.tzinfo is not None:
                            updated_at = updated_at.replace(tzinfo=None)

                        await conn.execute(
                            """
                            UPDATE products SET
                                name = $1, form = $2, manufacturer = $3, country = $4,
                                serial = $5, price = $6, quantity = $7, total_price = $8,
                                expiry_date = $9, category = $10, import_date = $11,
                                internal_code = $12, wholesale_price = $13, retail_price = $14,
                                distributor = $15, internal_id = $16, updated_at = $17
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

            # Добавление продуктов пакетами
            if to_add:
                batch_size = 50  # Уменьшим размер батча для вставок
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
                            "uuid", "name", "form", "manufacturer", "country", "serial",
                            "price", "quantity", "total_price", "expiry_date", "category",
                            "import_date", "internal_code", "wholesale_price", "retail_price",
                            "distributor", "internal_id", "pharmacy_id", "updated_at",
                        ]:
                            placeholders.append(f"${param_counter}")
                            value = product[field]

                            if field == "updated_at" and value and value.tzinfo is not None:
                                value = value.replace(tzinfo=None)
                            elif field in ["price", "quantity", "total_price", "wholesale_price", "retail_price"]:
                                value = float(value)

                            params.append(value)
                            param_counter += 1

                        values_placeholders.append(f"({', '.join(placeholders)})")

                    query = f"""
                        INSERT INTO products (
                            uuid, name, form, manufacturer, country, serial, price, quantity,
                            total_price, expiry_date, category, import_date, internal_code,
                            wholesale_price, retail_price, distributor, internal_id, pharmacy_id, updated_at
                        ) VALUES {', '.join(values_placeholders)}
                    """
                    await conn.execute(query, *params)
                stats["added"] = len(to_add)
                logger.info(f"Added {len(to_add)} products")

            return stats

        except Exception as e:
            await conn.close()
            logger.error(f"Error executing incremental changes: {str(e)}")
            raise
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise


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
        "АМП",
        "ТАБЛ",
        "ТАБЛ.",
        "ТАБЛ,",
        "ТАБЛ",
        "ТАБЛ.П/О",
        "ТАБЛ.РАСТВ.",
        "МАЗЬ",
        "СУПП",
        "ГЕЛЬ",
        "КАПЛИ",
        "ФЛ",
        "Р-Р",
        "ТУБА",
        "капс",
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

    form_regex = re.compile(
        r"(" + "|".join(re.escape(kw) for kw in form_keywords) + r")([\s\.,].*)?$",
        re.IGNORECASE,
    )

    match = form_regex.search(product_string)
    if match:
        form_start = match.start()
        name_part = product_string[:form_start].strip()
        form_part = product_string[form_start:].strip()
        form_part = re.sub(r"^[\s\.,]+", "", form_part)
        return (name_part if name_part else "-", form_part)

    return (product_string, "-")


@celery.task
def sync_pharmacy_orders_task():
    """Периодическая задача для синхронизации заказов"""
    # Импортируем здесь чтобы избежать циклических импортов
    from services.sync_service import SyncService

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
    from services.sync_service import SyncService

    sync_service = SyncService()

    # Запускаем в event loop для async функций
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(sync_service.retry_failed_orders())


celery.conf.beat_schedule = {
    'sync-orders-every-10-min': {
        'task': 'tasks_increment.sync_pharmacy_orders_task',
        'schedule': 600.0,
    },
    'retry-failed-orders-every-5-min': {
        'task': 'tasks_increment.retry_failed_orders_task',
        'schedule': 300.0,
    },
}
