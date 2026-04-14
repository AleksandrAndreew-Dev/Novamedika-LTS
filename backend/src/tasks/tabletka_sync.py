"""
Сервис синхронизации данных аптек с tabletka.by

Парсит https://tabletka.by/pharmacies/ и обновляет информацию в БД:
- name, city, district, address, phone, opening_hours
- Матчинг по адресу + телефону + названию
"""

import re
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TABLETKA_BASE = "https://tabletka.by"
TABLETKA_SEARCH_URL = (
    f"{TABLETKA_BASE}/pharmacies/?&page={{page}}&str={{query}}&sort=name&sorttype=asc"
)

# Поисковые запросы для наших сетей
SEARCH_QUERIES = ["новамедика", "эклиния"]

# User-Agent для запросов
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class TabletkaPharmacy:
    """Данные аптеки с tabletka.by"""

    tabletka_id: str
    name: str
    url: str
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    opening_hours: Optional[str] = None
    manager_name: Optional[str] = None  # Заведующий


# Маппинг улиц Минска к районам (для извлечения когда район не указан явно)
MINSK_STREET_TO_DISTRICT = {
    "Платонова": "Первомайский",
    "Богдановича": "Первомайский",
    "Независимости": "Первомайский",  # часть
    "Лесная": "Первомайский",
    "Калиновского": "Первомайский",
    "Хоружей": "Советский",
    "Верная": "Советский",
    "Волгоградская": "Советский",
    "Тухачевского": "Фрунзенский",
    "Пушкина": "Фрунзенский",
    "Мельникайте": "Фрунзенский",
    "Каменногорская": "Фрунзенский",
    "Сухая": "Фрунзенский",
    "Петра Глебки": "Фрунзенский",
    "Янки Купалы": "Центральный",
    "Советская": "Центральный",
    "Революционная": "Центральный",
    "Интернациональная": "Центральный",
    "Кирова": "Центральный",
    "Тимошенко": "Заводской",
    "Долгобродская": "Заводской",
    "Смоленская": "Заводской",
    "Геологическая": "Заводской",
    "Холмогорская": "Московский",
    "Ленинский проспект": "Ленинский",
    "Бобруйская": "Ленинский",
    "Козлова": "Октябрьский",
    "Кижеватова": "Октябрьский",
    "Уручская": "Первомайский",
    "Белорусская": "Первомайский",
}


def extract_district_from_address(address: str) -> Optional[str]:
    """Извлекает район из строки адреса."""
    if not address:
        return None

    # Формат: Минск-Фрунзенский
    match = re.match(r"^([А-Яа-яЁё]+)\s*[-–—]\s*([А-Яа-яЁё]+)\b", address)
    if match:
        return f"{match.group(2).strip()} р-н"

    # Формат: Минск, Фрунзенский р-н
    match = re.search(r",\s*([А-Яа-яЁё]+\s+(?:р-н|район))\b", address)
    if match:
        return match.group(1).strip().replace("район", "р-н")

    # Формат: ул. Платонова → извлекаем улицу и ищем в маппинге
    if "Минск" in address:
        street_match = re.search(r"ул\.\s*([А-Яа-яЁё]+)", address)
        if street_match:
            street = street_match.group(1).strip()
            for known_street, district in MINSK_STREET_TO_DISTRICT.items():
                if street.lower().startswith(known_street[:4].lower()):
                    return f"{district} р-н"

    return None


async def fetch_pharmacy_page(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """Загружает HTML страницы аптеки."""
    try:
        resp = await client.get(
            url, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        )
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPError as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def parse_pharmacy_from_html(html: str, tabletka_id: str) -> Optional[TabletkaPharmacy]:
    """Парсит страницу аптеки и извлекает информацию."""
    soup = BeautifulSoup(html, "html.parser")

    # Заголовок — обычно название аптеки
    title_el = soup.find("h1") or soup.find("h2")
    name = title_el.get_text(strip=True) if title_el else ""

    # Ищем адрес — обычно в блоке с контактами
    full_text = soup.get_text(separator="\n")
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]

    city = None
    district = None
    address = None
    phone = None
    opening_hours = None
    manager_name = None

    # Паттерны для поиска
    address_patterns = [
        r"(Минск[-–—][А-Яа-яЁё]+,\s*ул\.[^\n,]+)",
        r"(Минск[-–—][А-Яа-яЁё]+[^\n,]*)",
        r"(Гомель[-–—][А-Яа-яЁё]+[^\n,]*)",
        r"(Брест[-–—][А-Яа-яЁё]+[^\n,]*)",
        r"(Гродно[-–—][А-Яа-яЁё]+[^\n,]*)",
        r"(Могилёв[-–—][А-Яа-яЁё]+[^\n,]*)",
        r"(Витебск[-–—][А-Яа-яЁё]+[^\n,]*)",
    ]

    phone_pattern = r"(\+375[\d\s\-]+)"
    hours_pattern = r"(\d{1,2}[.:]\d{2}\s*[–-]\s*\d{1,2}[.:]\d{2})"
    manager_pattern = r"(?:Заведующий|Зав\.?)\s*[:.\s]*([А-Яа-яЁё][А-Яа-яЁё\s]+?(?:[А-Яа-яЁё]\.)?\s*[А-Яа-яЁё]+)"

    # Ищем адрес
    for line in lines:
        for pattern in address_patterns:
            match = re.search(pattern, line)
            if match:
                full_address = match.group(1).strip()
                # Разбираем город/район/адрес
                city_match = re.match(r"^([А-Яа-яЁё]+)\s*[-–—]", full_address)
                if city_match:
                    city = city_match.group(1)
                    district = extract_district_from_address(full_address)
                    # Извлекаем улицу после города-района
                    addr_part = re.sub(
                        r"^[А-Яа-яЁё]+\s*[-–—][А-Яа-яЁё]+\s*,\s*", "", full_address
                    )
                    if addr_part and "ул." in addr_part:
                        address = addr_part.strip()
                    else:
                        address = full_address
                break

    # Если адрес не найден — ищем просто адрес с улицей
    if not address:
        for line in lines:
            if "ул." in line or "пр." in line or "бул." in line:
                address = line.strip()
                city_match = re.match(r"^([А-Яа-яЁё]+)\s*[-–—]", address)
                if city_match:
                    city = city_match.group(1)
                    district = extract_district_from_address(address)
                break

    # Ищем телефон
    for line in lines:
        match = re.search(phone_pattern, line)
        if match:
            phone = match.group(1).strip()
            break

    # Ищем часы работы — парсим весь блок расписания по дням
    in_hours_block = False
    hours_lines = []
    day_pattern = re.compile(
        r"^(Понедельник|Вторник|Среда|Четверг|Пятница|Суббота|Воскресенье)",
        re.IGNORECASE,
    )
    time_pattern = re.compile(r"\d{1,2}[.:]\d{2}\s*[–-—]\s*\d{1,2}[.:]\d{2}")

    for idx in range(len(lines) - 1):
        line = lines[idx]

        # Проверяем начало блока часов (первый день недели)
        if not in_hours_block and day_pattern.match(line):
            # Проверяем что следующая строка содержит время
            if time_pattern.search(lines[idx + 1]):
                in_hours_block = True
                hours_lines = [line]
                continue

        # Если внутри блока — добавляем строки пока это дни или время
        if in_hours_block:
            if (
                day_pattern.match(line)
                or time_pattern.search(line)
                or "Санитарный" in line
            ):
                hours_lines.append(line)
            else:
                # Блок закончился
                in_hours_block = False

    # Собираем часы работы в одну строку
    if hours_lines:
        opening_hours = " | ".join(hours_lines)

    # Ищем заведующего
    for line in lines:
        if "Заведующий" in line or "Зав." in line:
            manager_match = re.search(manager_pattern, line)
            if manager_match:
                manager_name = manager_match.group(1).strip()

    # Если ничего не нашли — пытаемся извлечь из полного текста
    if not city and not address:
        # Попробуем найти адрес через meta description или structured data
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            content = meta_desc["content"]
            city_match = re.match(r"^([А-Яа-яЁё]+)\s*[-–—]", content)
            if city_match:
                city = city_match.group(1)
                district = extract_district_from_address(content)

    return TabletkaPharmacy(
        tabletka_id=tabletka_id,
        name=name or "",
        url=f"{TABLETKA_BASE}/pharmacies/{tabletka_id}/",
        city=city,
        district=district,
        address=address,
        phone=phone,
        opening_hours=opening_hours,
        manager_name=manager_name,
    )


async def fetch_all_pharmacies_from_tabletka() -> list[TabletkaPharmacy]:
    """
    Ищет аптеки наших сетей ("новамедика", "эклиния") на tabletka.by
    через поиск и загружает детальную информацию по каждой.
    """
    logger.info("Starting tabletka.by pharmacy sync for our networks")

    all_pharmacy_ids = set()

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        # 1. Для каждого поискового запроса парсим все страницы результатов
        for query in SEARCH_QUERIES:
            logger.info(f"Searching tabletka.by for: '{query}'")
            page = 1
            while True:
                url = TABLETKA_SEARCH_URL.format(page=page, query=query)
                logger.info(f"  Page {page}: {url}")

                resp = await client.get(url, headers={"User-Agent": USER_AGENT})
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # Ищем ссылки на аптеки: /pharmacies/{id}/
                links = soup.select('a[href^="/pharmacies/"]')
                page_ids = []
                for link in links:
                    href = link.get("href", "")
                    match = re.search(r"/pharmacies/(\d+)/", href)
                    if match:
                        ph_id = match.group(1)
                        if ph_id not in all_pharmacy_ids:
                            all_pharmacy_ids.add(ph_id)
                            page_ids.append(ph_id)

                logger.info(
                    f"  Page {page}: found {len(page_ids)} new pharmacies "
                    f"(total: {len(all_pharmacy_ids)})"
                )

                # Проверяем есть ли кнопка "следующая страница"
                has_next = False
                pagination = soup.select('a[href*="page="]')
                for link in pagination:
                    href = link.get("href", "")
                    try:
                        p = int(re.search(r"page=(\d+)", href).group(1))
                        if p > page:
                            has_next = True
                            break
                    except (AttributeError, ValueError):
                        pass

                if not has_next:
                    break
                page += 1
                await asyncio.sleep(1)

        logger.info(f"Total unique pharmacies found: {len(all_pharmacy_ids)}")

        # 2. Загружаем каждую страницу аптеки
        results = []
        for i, ph_id in enumerate(sorted(all_pharmacy_ids, key=int), 1):
            url = f"{TABLETKA_BASE}/pharmacies/{ph_id}/"
            logger.info(f"[{i}/{len(all_pharmacy_ids)}] Fetching: {url}")

            html = await fetch_pharmacy_page(client, url)
            if html:
                pharmacy = parse_pharmacy_from_html(html, ph_id)
                if pharmacy:
                    results.append(pharmacy)
                    logger.info(
                        f"  Parsed: {pharmacy.name} | "
                        f"city={pharmacy.city}, district={pharmacy.district}, "
                        f"address={pharmacy.address}, phone={pharmacy.phone}"
                    )

            await asyncio.sleep(1.5)

        logger.info(f"Sync complete: {len(results)} pharmacies parsed from tabletka.by")
        return results
