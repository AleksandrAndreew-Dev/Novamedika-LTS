"""Тест парсинга страницы аптеки tabletka.by"""

import asyncio
import httpx
from bs4 import BeautifulSoup
import re

TABLETKA_URL = "https://tabletka.by/pharmacies/701/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(TABLETKA_URL, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text(separator="\n")
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]

    # Показать весь текст страницы
    print(f"\n=== ТЕКСТ СТРАНИЦЫ ({len(lines)} строк) ===\n")
    for i, line in enumerate(lines[:80], 1):
        print(f"{i:3d}: {line}")

    # Показать meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        print(f"\n=== META DESCRIPTION ===\n{meta_desc['content']}")

    # Проверить h1/h2
    title_el = soup.find("h1") or soup.find("h2")
    print(f"\n=== TITLE ===\n{title_el.get_text(strip=True) if title_el else 'N/A'}")

    # Извлечь название аптеки
    pharmacy_name = None
    # Ищем в разных местах
    for selector in [
        "h1",
        "h2",
        ".pharmacy-title",
        ".pharmacy-name",
        "[class*='pharmacy']",
    ]:
        el = soup.select_one(selector)
        if el:
            pharmacy_name = el.get_text(strip=True)
            print(f"\n=== PHARMACY NAME (selector: {selector}) ===\n{pharmacy_name}")
            break

    if not pharmacy_name:
        # Попробуем найти в meta
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            print(f"\n=== OG:TITLE ===\n{og_title['content']}")

    # Извлечь контакты (телефон, email)
    print(f"\n=== CONTACTS ===")
    phone_pattern = re.compile(r"(\+?\d[\d\s\-\(\)]{9,})")

    for tag in soup.find_all(["a", "p", "div", "span"]):
        text = tag.get_text(strip=True)
        if phone_pattern.search(text):
            print(f"PHONE: {text}")
        if "mail" in text.lower() or "@" in text:
            print(f"EMAIL: {text}")

    # Извлечь адрес
    print(f"\n=== ADDRESS ===")
    for tag in soup.find_all(["p", "div", "span", "li"]):
        text = tag.get_text(strip=True)
        if any(
            word in text.lower()
            for word in [
                "ул.",
                "проспект",
                "бульвар",
                "набережная",
                "минск",
                "беларусь",
            ]
        ):
            print(f"ADDRESS: {text}")

    # Показать все ссылки
    print(f"\n=== ALL LINKS ({len(soup.find_all('a'))}) ===")
    for a in soup.find_all("a", href=True)[:30]:
        print(f"LINK: {a['href']} - {a.get_text(strip=True)}")


if __name__ == "__main__":
    asyncio.run(main())
