"""Безопасное редактирование сообщений Telegram.

Telegram API бросает `TelegramBadRequest: message is not modified`, если
новый текст/клавиатура совпадают с текущими. Повторное нажатие inline-кнопки
(«Статистика», «Помощь», «Вопросы» и т.д.) не должно показывать ошибку —
контент просто остаётся как есть.
"""

import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)

_NOT_MODIFIED_MARKER = "message is not modified"


async def safe_edit_message(message: Message | None, text: str, **kwargs) -> bool:
    """Редактирует сообщение, игнорируя «message is not modified».

    Returns:
        True — сообщение отредактировано; False — контент совпал (ничего не менялось).
    """
    if message is None:
        return False
    try:
        await message.edit_text(text, **kwargs)
        return True
    except TelegramBadRequest as e:
        if _NOT_MODIFIED_MARKER in str(e):
            logger.info("safe_edit_message: content unchanged, staying on current message")
            return False
        raise


async def safe_edit_callback(
    callback: CallbackQuery,
    text: str,
    actual_text: str = "✅ Уже актуально",
    **kwargs,
) -> bool:
    """Редактирует сообщение callback'а; при отсутствии изменений отвечает коротким уведомлением.

    Returns:
        True — сообщение отредактировано; False — контент совпал.
    """
    if not callback.message:
        await callback.bot.send_message(
            chat_id=callback.from_user.id, text=text, **kwargs
        )
        return False
    edited = await safe_edit_message(callback.message, text, **kwargs)
    if not edited:
        await callback.answer(actual_text)
    return edited
