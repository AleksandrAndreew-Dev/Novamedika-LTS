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

    # Показать строки 80-200 (адрес, телефон, часы)
    print(f"\n=== СТРОКИ 80-200 ===\n")
    for i, line in enumerate(lines[80:200], 81):
        print(f"{i:3d}: {line}")

    # Показать строки содержащие "Неманская" или "адрес"
    print(f"\n=== СТРОКИ С АДРЕСОМ ===\n")
    for i, line in enumerate(lines, 1):
        if "неманск" in line.lower() or "адрес:" in line.lower() or "ул." in line:
            print(f"{i:3d}: {line}")

    # Показать meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        print(f"\n=== META DESCRIPTION ===\n{meta_desc['content']}")


if __name__ == "__main__":
    asyncio.run(main())
