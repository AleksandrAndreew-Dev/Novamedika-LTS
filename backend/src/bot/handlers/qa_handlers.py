
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from db.qa_models import User, Pharmacist
from db.qa_models import Question
from db.qa_models import Answer
from bot.handlers.qa_states import QAStates
from bot.keyboards.qa_keyboard import make_question_keyboard

from bot.handlers.common_handlers import get_pharmacist_keyboard
import logging
from datetime import datetime, timedelta
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("online"))
async def set_online(
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: Pharmacist
):
    """Установка статуса онлайн для фармацевта с проверкой ожидающих вопросов"""
    logger.info(
        f"Command /online from user {message.from_user.id}, is_pharmacist: {is_pharmacist}"
    )

    if not is_pharmacist or not pharmacist:
        logger.warning(
            f"User {message.from_user.id} is not pharmacist but tried to use /online"
        )
        await message.answer(
            "❌ Эта команда доступна только для зарегистрированных фармацевтов"
        )
        return

    try:
        pharmacist.is_online = True
        pharmacist.last_seen = get_utc_now_naive()
        await db.commit()
        logger.info(
            f"Pharmacist {message.from_user.id} successfully set online status"
        )

        # Проверяем есть ли ожидающие вопросы
        from sqlalchemy import select, func
        result = await db.execute(
            select(func.count(Question.uuid))
            .where(Question.status == "pending")
        )
        pending_count = result.scalar() or 0

        if pending_count > 0:
            await message.answer(
                f"✅ Вы теперь онлайн и готовы принимать вопросы!\n\n"
                f"📝 <b>Ожидающих вопросов:</b> {pending_count}\n"
                f"Используйте /questions чтобы просмотреть вопросы.",
                parse_mode="HTML",
                reply_markup=get_pharmacist_keyboard()  # Добавляем клавиатуру
            )

            # Показываем первые 3 вопроса
            result = await db.execute(
                select(Question)
                .where(Question.status == "pending")
                .order_by(Question.created_at.asc())
                .limit(3)
            )
            questions = result.scalars().all()

            for i, question in enumerate(questions, 1):
                question_preview = question.text[:100] + "..." if len(question.text) > 100 else question.text
                await message.answer(
                    f"❓ Вопрос #{i}:\n{question_preview}\n",
                    reply_markup=make_question_keyboard(question.uuid)
                )
        else:
            await message.answer(
                "✅ Вы теперь онлайн и готовы принимать вопросы!\n\n"
                "На данный момент новых вопросов нет. "
                "Вы получите уведомление, когда появится новый вопрос.",
                reply_markup=get_pharmacist_keyboard()
            )

    except Exception as e:
        logger.error(
            f"Error setting online status for user {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("❌ Ошибка при изменении статуса")


@router.message(Command("offline"))
async def set_offline(
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: Pharmacist
):
    """Установка статуса офлайн для фармацевта"""
    logger.info(
        f"Command /offline from user {message.from_user.id}, is_pharmacist: {is_pharmacist}"
    )

    if not is_pharmacist or not pharmacist:
        logger.warning(
            f"User {message.from_user.id} is not pharmacist but tried to use /offline"
        )
        await message.answer(
            "❌ Эта команда доступна только для зарегистрированных фармацевтов"
        )
        return

    try:
        pharmacist.is_online = False
        pharmacist.last_seen = get_utc_now_naive()
        await db.commit()
        logger.info(
        f"Pharmacist {message.from_user.id} successfully set offline status"  # вместо pharmacist.telegram_id
    )

        await message.answer("✅ Вы теперь офлайн.")

    except Exception as e:
        logger.error(
            f"Error setting offline status for user {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("❌ Ошибка при изменении статуса")


@router.message(Command("status"))
async def cmd_status(
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: Pharmacist
):
    """Показать статус фармацевта"""
    logger.info(
        f"Command /status from user {message.from_user.id}, is_pharmacist: {is_pharmacist}"
    )

    if not is_pharmacist or not pharmacist:
        await message.answer(
            "❌ Эта команда доступна только для зарегистрированных фармацевтов"
        )
        return

    status = "онлайн" if pharmacist.is_online else "офлайн"
    last_seen = (
        pharmacist.last_seen.strftime("%d.%m.%Y %H:%M")
        if pharmacist.last_seen
        else "никогда"
    )

    await message.answer(
        f"📊 Ваш статус:\n\n"
        f"• Статус: {status}\n"
        f"• Последняя активность: {last_seen}\n"
        f"• Зарегистрирован: {pharmacist.created_at.strftime('%d.%m.%Y')}"
    )


@router.message(Command("questions"))
async def cmd_questions(
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: Pharmacist
):
    """Показать вопросы с пагинацией"""
    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта команда доступна только фармацевтам")
        return

    try:
        result = await db.execute(
            select(Question)
            .where(Question.status == "pending")
            .order_by(Question.created_at.asc())  # Сначала старые вопросы
            .limit(5)  # Ограничиваем количество
        )
        questions = result.scalars().all()

        if not questions:
            await message.answer(
                "📝 На данный момент нет новых вопросов.\n\n"
                "Пользователи задают вопросы через команду /ask"
            )
            return

        for i, question in enumerate(questions, 1):
            question_text = (
                f"❓ Вопрос #{i}:\n{question.text}\n\n"
                f"🕒 Создан: {question.created_at.strftime('%d.%m.%Y %H:%M')}"
            )

            # Получаем пользователя
            user_result = await db.execute(
                select(User).where(User.uuid == question.user_id)
            )
            user = user_result.scalar_one_or_none()

            if user:
                # ИСПРАВЛЕНИЕ: используем правильные поля
                user_info = user.first_name or user.telegram_username or "Аноним"
                if user.last_name:
                    user_info = f"{user.first_name} {user.last_name}"
                question_text += f"\n👤 Пользователь: {user_info}"

            await message.answer(
                question_text,
                reply_markup=make_question_keyboard(question.uuid)
            )

        if len(questions) == 5:
            await message.answer("💡 Показаны первые 5 вопросов. Ответьте на них чтобы увидеть следующие.")

    except Exception as e:
        logger.error(f"Error in cmd_questions: {e}")
        await message.answer("❌ Ошибка при получении вопросов")



@router.message(Command("debug_status"))
async def debug_status(
    message: Message, db: AsyncSession, is_pharmacist: bool
):
    """Команда для отладки статуса системы"""
    try:
        from sqlalchemy import select, func
        from bot.services.notification_service import get_online_pharmacists

        # Статистика по вопросам
        total_questions = await db.execute(select(func.count(Question.uuid)))
        pending_questions = await db.execute(
            select(func.count(Question.uuid)).where(Question.status == "pending")
        )

        # Онлайн фармацевты
        online_pharmacists = await get_online_pharmacists(db)

        # Все активные фармацевты
        all_pharmacists_result = await db.execute(
            select(Pharmacist).where(Pharmacist.is_active == True)
        )
        all_pharmacists = all_pharmacists_result.scalars().all()

        status_text = (
            f"🔧 <b>Отладочная информация системы</b>\n\n"
            f"📊 <b>Вопросы:</b>\n"
            f"• Всего: {total_questions.scalar()}\n"
            f"• Ожидают ответа: {pending_questions.scalar()}\n\n"
            f"👨‍⚕️ <b>Фармацевты:</b>\n"
            f"• Всего активных: {len(all_pharmacists)}\n"
            f"• Сейчас онлайн: {len(online_pharmacists)}\n\n"
            f"🕒 <b>Время сервера:</b>\n"
            f"{get_utc_now_naive().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Детальная информация об онлайн фармацевтах
        if online_pharmacists:
            status_text += f"\n\n<b>Онлайн фармацевты:</b>"
            for i, pharm in enumerate(online_pharmacists, 1):
                last_seen = pharm.last_seen.strftime('%H:%M:%S') if pharm.last_seen else "никогда"
                status_text += f"\n{i}. ID: {pharm.user.telegram_id}, Последняя активность: {last_seen}"

        await message.answer(status_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in debug_status: {e}")
        await message.answer("❌ Ошибка при получении статуса системы")


@router.callback_query(F.data.startswith("answer_"))
async def answer_question_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка нажатия на кнопку ответа на вопрос"""
    question_uuid = callback.data.replace("answer_", "")

    logger.info(
        f"Answer callback for question {question_uuid} from user {callback.from_user.id}"
    )

    if not is_pharmacist or not pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
        return

    try:
        # Получаем вопрос
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Сохраняем ID вопроса в состоянии
        await state.update_data(question_uuid=question_uuid)
        await state.set_state(QAStates.waiting_for_answer)

        question_preview = (
            question.text[:100] + "..." if len(question.text) > 100 else question.text
        )

        await callback.message.answer(
            f"💬 Вы отвечаете на вопрос:\n\n"
            f"«{question_preview}»\n\n"
            f"Напишите ваш ответ ниже:\n"
            f"(или /cancel для отмены)"
        )

        await callback.answer()

    except Exception as e:
        logger.error(
            f"Error in answer_question_callback for user {callback.from_user.id}: {e}",
            exc_info=True,
        )
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


@router.message(QAStates.waiting_for_answer)
async def process_answer_text(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка текста ответа на вопрос - ОБНОВЛЕННАЯ ВЕРСИЯ С ФИО"""
    logger.info(f"Processing answer from pharmacist {message.from_user.id}")

    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта функция доступна только фармацевтам")
        await state.clear()
        return

    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("question_uuid")

        if not question_uuid:
            await message.answer("❌ Не удалось найти вопрос для ответа")
            await state.clear()
            return

        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await message.answer("❌ Вопрос не найден")
            await state.clear()
            return

        # Создаем ответ
        answer = Answer(
            text=message.text,
            question_id=question.uuid,
            pharmacist_id=pharmacist.uuid,
            created_at=get_utc_now_naive(),
        )

        db.add(answer)
        question.status = "answered"
        question.answered_at = get_utc_now_naive()
        await db.commit()

        # Уведомляем пользователя с информацией о фармацевте (ВКЛЮЧАЯ ФИО)
        user_result = await db.execute(
            select(User).where(User.uuid == question.user_id)
        )
        user = user_result.scalar_one_or_none()

        if user and user.telegram_id:
            try:
                # Формируем информацию о фармацевте с ФИО
                pharmacy_info = pharmacist.pharmacy_info or {}
                chain = pharmacy_info.get("chain", "Не указана")
                number = pharmacy_info.get("number", "Не указан")
                role = pharmacy_info.get("role", "Фармацевт")

                # Получаем ФИО фармацевта
                first_name = pharmacy_info.get("first_name", "")
                last_name = pharmacy_info.get("last_name", "")
                patronymic = pharmacy_info.get("patronymic", "")

                # Формируем строку с ФИО
                pharmacist_name_parts = []
                if last_name:
                    pharmacist_name_parts.append(last_name)
                if first_name:
                    pharmacist_name_parts.append(first_name)
                if patronymic:
                    pharmacist_name_parts.append(patronymic)

                pharmacist_name = " ".join(pharmacist_name_parts) if pharmacist_name_parts else "Фармацевт"

                pharmacist_info = f"{pharmacist_name}"
                if chain and number:
                    pharmacist_info += f", {chain}, аптека №{number}"
                if role and role != "Фармацевт":
                    pharmacist_info += f" ({role})"

                answer_preview = (
                    message.text[:100] + "..."
                    if len(message.text) > 100
                    else message.text
                )

                await message.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"💊 На ваш вопрос получен ответ!\n\n"
                         f"❓ Ваш вопрос: {question.text}\n\n"
                         f"💬 Ответ: {answer_preview}\n\n"
                         f"👨‍⚕️ Ответ предоставил: {pharmacist_info}\n\n"
                         f"💡 Если ответ неполный или у вас есть уточняющий вопрос, "
                         "используйте команду /clarify",
                )
                logger.info(
                    f"Notification sent to user {user.telegram_id} about answer"
                )

            except Exception as e:
                logger.error(
                    f"Failed to send notification to user {user.telegram_id}: {e}"
                )

        await message.answer(
            "✅ Ответ успешно отправлен пользователю!\n\n"
            "Используйте /questions для просмотра других вопросов."
        )

        await state.clear()

    except Exception as e:
        logger.error(
            f"Error in process_answer_text for pharmacist {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("❌ Ошибка при отправке ответа")
        await state.clear()
