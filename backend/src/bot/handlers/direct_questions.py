from db.qa_models import User, Question
from utils.time_utils import get_utc_now_naive


from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import logging


from bot.services.notification_service import notify_pharmacists_about_new_question


logger = logging.getLogger(__name__)
router = Router()


def should_create_question(text: str) -> bool:
    """Определяет, стоит ли создавать вопрос из текста"""
    text_lower = text.lower().strip()

    # 0. Проверяем, является ли это командой (начинается с /)
    if text.startswith("/"):
        return False

    # 2. Проверяем длину (минимально 5 символов)
    if len(text_lower) < 5:
        return False

    # 3. Проверяем, что это не просто набор символов или цифр
    if (
        text_lower.replace("?", "")
        .replace("!", "")
        .replace(".", "")
        .replace(",", "")
        .strip()
        .isdigit()
    ):
        return False

    # 4. Проверяем на явные команды (даже без /)
    if text_lower.startswith(("список", "помощь", "команды", "меню", "старт")):
        return False

    return True


@router.message(F.text & ~F.command)
async def handle_direct_text(
    message: Message,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
    state: FSMContext,
):
    """Обработка прямых текстовых сообщений как вопросов"""


    if is_pharmacist:
        return


    current_state = await state.get_state()
    if current_state is not None:
       
        if current_state != UserQAStates.waiting_for_prescription_photo:
            return

    if not should_create_question(message.text):
        return

    try:
        # Создаем вопрос
        question = Question(
            text=message.text,
            user_id=user.uuid,
            status="pending",
            created_at=get_utc_now_naive(),
        )

        db.add(question)
        await db.commit()
        await db.refresh(question)

        logger.info(f"Direct question from {user.telegram_id}: {message.text[:50]}...")

        # Уведомляем фармацевтов
        await notify_pharmacists_about_new_question(question, db)

        # Подтверждение пользователю
        await message.answer(
        "✅ <b>Вопрос отправлен!</b>\n\n"
        "Фармацевты получили уведомление и скоро ответят.\n\n"
        "💡 <i>Используйте /my_questions чтобы отслеживать статус</i>",
        parse_mode="HTML",
    )

    except Exception as e:
        logger.error(f"Error in direct question: {e}")
