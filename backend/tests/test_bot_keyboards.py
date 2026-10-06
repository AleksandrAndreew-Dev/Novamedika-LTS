import os
import sys
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bot.handlers.common_handlers.keyboards import (
    get_pharmacist_inline_keyboard_with_token,
)


def _find_web_app_url(keyboard, text):
    for row in keyboard.inline_keyboard:
        for button in row:
            if button.text == text and button.web_app is not None:
                return button.web_app.url
    raise AssertionError(f"WebApp button {text!r} not found")


def test_pharmacist_panel_button_opens_dashboard(monkeypatch):
    monkeypatch.setenv(
        "PHARMACIST_DASHBOARD_URL",
        "https://spravka.novamedika.com/pharmacist",
    )
    keyboard = get_pharmacist_inline_keyboard_with_token(123, None)
    url = _find_web_app_url(keyboard, "💼 Панель фармацевта")

    assert url.rstrip("/") == "https://spravka.novamedika.com/pharmacist"


def test_pharmacist_search_button_opens_search(monkeypatch):
    monkeypatch.setenv(
        "FRONTEND_URL",
        "https://spravka.novamedika.com/",
    )
    keyboard = get_pharmacist_inline_keyboard_with_token(123, None)
    url = _find_web_app_url(keyboard, "🔍 Поиск лекарств")

    assert url == "https://spravka.novamedika.com/search"
