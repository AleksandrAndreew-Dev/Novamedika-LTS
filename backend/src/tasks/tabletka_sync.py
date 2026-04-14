"""
Сервис синхронизации данных аптек с tabletka.by

Парсит https://tabletka.by/pharmacies/ и обновляет информацию в БД:
- name, city, district, address, phone, opening_hours
"""

import re
import logging
import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

TABLETKA_BASE = "https://tabletka.by"
TABLETKA_SEARCH_URL = (
    f"{TABLETKA_BASE}/pharmacies/?&page={{page}}&str={{query}}&sort=name&sorttype=asc"
)

SEARCH_QUERIES = ["новамедика", "эклиния"]

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
    manager_name: Optional[str] = None


MINSK_STREET_TO_DISTRICT = {
    "Платонова": "Первомайский",
    "Богдановича": "Первомайский",
    "Независимости": "Первомайский",
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

    match = re.match(r"^([А-Яа-яЁё]+)\s*[-–—]\s*([А-Яа-яЁё]+)\b", address)
    if match:
        return f"{match.group(2).strip()} р-н"

    match = re.search(r",\s*([А-Яа-яЁё]+\s+(?:р-н|район))\b", address)
    if match:
        return match.group(1).strip().replace("район", "р-н")

    if "Минск" in address:
        street_match = re.search(
            r"(ул\.|пр\.|бул\.|пер\.|наб\.)\s*([А-Яа-яЁё]+)", address
        )
        if street_match:
            street = street_match.group(2).strip()
            for known_street, district in MINSK_STREET_TO_DISTRICT.items():
                if street.lower().startswith(known_street[:4].lower()):
                    return f"{district} р-н"

    return None


def extract_city_district_address(full_address: str):
    """
    Из полного адреса вида "Минск-Фрунзенский, пер. 2-й Тимошенко, 3-235"
    возвращает (city, district, clean_address).
    """
    city = None
    district = None
    clean_address = None

    # Ищем город и район в начале: "Город-Район" или "Город, Район"
    match = re.match(r"^([А-Яа-яЁё]+)\s*[-–—]\s*([А-Яа-яЁё]+)", full_address)
    if match:
        city = match.group(1).strip()
        district = f"{match.group(2).strip()} р-н"
        # Удаляем "Город-Район, " из начала
        clean_address = re.sub(
            r"^[А-Яа-яЁё]+\s*[-–—][А-Яа-яЁё]+\s*,\s*", "", full_address
        ).strip()
    else:
        # Возможно, запись через запятую: "Минск, Фрунзенский р-н, ..."
        match_comma = re.match(
            r"^([А-Яа-яЁё]+),\s*([А-Яа-яЁё]+(?:\s+р-н)?)", full_address
        )
        if match_comma:
            city = match_comma.group(1).strip()
            district_raw = match_comma.group(2).strip()
            if not district_raw.endswith("р-н"):
                district_raw += " р-н"
            district = district_raw
            clean_address = re.sub(
                r"^[А-Яа-яЁё]+,\s*[А-Яа-яЁё]+(?:\s+р-н)?,\s*", "", full_address
            ).strip()
        else:
            # Не удалось выделить город и район — берём весь адрес как есть
            clean_address = full_address

    if not clean_address:
        clean_address = full_address

    return city, district, clean_address


def _format_hours_compact(hours_lines: list[str]) -> str:
    """Форматирует расписание: 'Пн-Пт 9:00-20:00, Сб-Вс 10:00-18:00'."""
    DAY_SHORT = {
        "понедельник": "Пн",
        "вторник": "Вт",
        "среда": "Ср",
        "четверг": "Чт",
        "пятница": "Пт",
        "суббота": "Сб",
        "воскресенье": "Вс",
    }
    DAY_ORDER = list(DAY_SHORT.keys())

    schedule: list[tuple[str, str]] = []
    current_day = None
    for line in hours_lines:
        line_lower = line.lower().strip()
        matched_day = None
        for full_day in DAY_ORDER:
            if line_lower.startswith(full_day):
                matched_day = full_day
                break
        if matched_day:
            current_day = matched_day
        elif current_day:
            val = line.strip()
            if val.startswith("|"):
                val = val[1:].strip()
            schedule.append((current_day, val))
            current_day = None

    if not schedule:
        return " | ".join(hours_lines)

    groups: list[tuple[str, str, str]] = []
    for day, time_val in schedule:
        if groups and groups[-1][2] == time_val:
            groups[-1] = (groups[-1][0], day, time_val)
        else:
            groups.append((day, day, time_val))

    parts: list[str] = []
    for start_day, end_day, time_val in groups:
        s = DAY_SHORT.get(start_day, start_day[:2])
        e = DAY_SHORT.get(end_day, end_day[:2])
        if s == e:
            parts.append(f"{s} {time_val}")
        else:
            parts.append(f"{s}-{e} {time_val}")

    return ", ".join(parts)


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

    title_el = soup.find("h1") or soup.find("h2")
    name = title_el.get_text(strip=True) if title_el else ""

    full_text = soup.get_text(separator="\n")
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]

    city = None
    district = None
    address = None
    phone = None
    opening_hours = None
    manager_name = None

    # ---------- 1. Поиск адреса через блок "Адрес" (самый надёжный) ----------
    # Ищем элемент, который содержит текст "Адрес" (часто это <div> или <p>)
    address_label = None
    for elem in soup.find_all(["div", "p", "span", "td", "th"]):
        if elem.get_text(strip=True) == "Адрес":
            address_label = elem
            break

    if address_label:
        # Берём следующий элемент (sibling) или родителя
        addr_elem = address_label.find_next_sibling()
        if addr_elem and isinstance(addr_elem, Tag):
            full_address = addr_elem.get_text(strip=True)
            if full_address and len(full_address) > 5:
                city, district, address = extract_city_district_address(full_address)
                logger.debug(
                    f"Address from block: full='{full_address}', city={city}, district={district}, address={address}"
                )

    # ---------- 2. Если не нашли, ищем через регулярные выражения ----------
    if not address:
        # Паттерны для полного адреса (включая город и район)
        full_address_patterns = [
            r"(Минск[-–—][А-Яа-яЁё]+,\s*(?:ул\.|пр\.|бул\.|пер\.|наб\.|площадь)[^,\n]+(?:,\s*[^,\n]+)*)",
            r"(Минск[-–—][А-Яа-яЁё]+[^\n,]*)",
            r"(Гомель[-–—][А-Яа-яЁё]+,\s*(?:ул\.|пр\.|бул\.|пер\.|наб\.|площадь)[^,\n]+(?:,\s*[^,\n]+)*)",
            r"(Гомель[-–—][А-Яа-яЁё]+[^\n,]*)",
            r"(Брест[-–—][А-Яа-яЁё]+,\s*(?:ул\.|пр\.|бул\.|пер\.|наб\.|площадь)[^,\n]+(?:,\s*[^,\n]+)*)",
            r"(Брест[-–—][А-Яа-яЁё]+[^\n,]*)",
            r"(Гродно[-–—][А-Яа-яЁё]+,\s*(?:ул\.|пр\.|бул\.|пер\.|наб\.|площадь)[^,\n]+(?:,\s*[^,\n]+)*)",
            r"(Гродно[-–—][А-Яа-яЁё]+[^\n,]*)",
            r"(Могилёв[-–—][А-Яа-яЁё]+,\s*(?:ул\.|пр\.|бул\.|пер\.|наб\.|площадь)[^,\n]+(?:,\s*[^,\n]+)*)",
            r"(Могилёв[-–—][А-Яа-яЁё]+[^\n,]*)",
            r"(Витебск[-–—][А-Яа-яЁё]+,\s*(?:ул\.|пр\.|бул\.|пер\.|наб\.|площадь)[^,\n]+(?:,\s*[^,\n]+)*)",
            r"(Витебск[-–—][А-Яа-яЁё]+[^\n,]*)",
        ]

        for line in lines:
            for pattern in full_address_patterns:
                match = re.search(pattern, line)
                if match:
                    full_address = match.group(1).strip()
                    city, district, address = extract_city_district_address(
                        full_address
                    )
                    if address:
                        break
            if address:
                break

    # ---------- 3. Fallback: meta description ----------
    if not address:
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            content = meta_desc["content"]
            addr_match = re.search(
                r"(?:адрес:\s*)?([А-Яа-яЁё]+[-–—][А-Яа-яЁёё]+,\s*(?:ул\.|пр\.|бул\.|пер\.|наб\.|площадь)[^,\n]+(?:,\s*[^,\n]+)*)",
                content,
            )
            if addr_match:
                full_address = addr_match.group(1).strip()
                city, district, address = extract_city_district_address(full_address)
                logger.debug(f"Address from meta description: {address}")

    # ---------- Поиск телефона ----------
    phone_pattern = r"(\+375[\d\s\-]+)"
    for line in lines:
        match = re.search(phone_pattern, line)
        if match:
            phone = match.group(1).strip()
            break

    # ---------- Поиск часов работы ----------
    in_hours_block = False
    hours_lines = []
    day_pattern = re.compile(
        r"^(Понедельник|Вторник|Среда|Четверг|Пятница|Суббота|Воскресенье)",
        re.IGNORECASE,
    )
    time_pattern = re.compile(r"\d{1,2}[.:]\d{2}\s*[–-—]\s*\d{1,2}[.:]\d{2}")

    def _is_hours_value(text: str) -> bool:
        return (
            time_pattern.search(text)
            or "выходной" in text.lower()
            or "Санитарн" in text
        )

    for idx in range(len(lines) - 1):
        line = lines[idx]

        if not in_hours_block and day_pattern.match(line):
            if _is_hours_value(lines[idx + 1]):
                in_hours_block = True
                hours_lines = [line]
                continue

        if in_hours_block:
            if day_pattern.match(line) or _is_hours_value(line):
                hours_lines.append(line)
            else:
                in_hours_block = False

    if hours_lines:
        opening_hours = _format_hours_compact(hours_lines)

    # ---------- Поиск заведующего ----------
    manager_pattern = r"(?:Заведующий|Зав\.?)\s*[:.\s]*([А-Яа-яЁё][А-Яа-яЁё\s]+?(?:[А-Яа-яЁё]\.)?\s*[А-Яа-яЁё]+)"
    for line in lines:
        if "Заведующий" in line or "Зав." in line:
            manager_match = re.search(manager_pattern, line)
            if manager_match:
                manager_name = manager_match.group(1).strip()

    # ---------- Fallback для города и района, если ещё не определены ----------
    if not city and not address:
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
    """Ищет аптеки наших сетей на tabletka.by."""
    logger.info("Starting tabletka.by pharmacy sync for our networks")

    all_pharmacy_ids = set()

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for query in SEARCH_QUERIES:
            logger.info(f"Searching tabletka.by for: '{query}'")
            page = 1
            while True:
                url = TABLETKA_SEARCH_URL.format(page=page, query=query)
                logger.info(f"  Page {page}: {url}")

                resp = await client.get(url, headers={"User-Agent": USER_AGENT})
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

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
