# ИНСТРУКЦИЯ ПО ИСПРАВЛЕНИЮ ТРАНСГРАНИЧНОЙ ПЕРЕДАЧИ ЧЕРЕЗ TELEGRAM

**Версия:** 1.0
**Дата:** 20 мая 2026 г.
**Приоритет:** 🔴 КРИТИЧЕСКИЙ

---

## ЧЕК-ЛИСТ ИСПРАВЛЕНИЯ

### Этап 1: Обновление политики конфиденциальности (1-2 дня)

#### 1.1. Открыть файл для редактирования

```bash
cd oac/docs
code 04-privacy-policy.md
```

#### 1.2. Найти раздел 4

Текущий текст (строки ~280-290):
```markdown
## 4. О ТРАНСГРАНИЧНОЙ ПЕРЕДАЧЕ ПЕРСОНАЛЬНЫХ ДАННЫХ

4.1. Оператор **не осуществляет** трансграничную передачу персональных данных.

4.2. Обработка персональных данных осуществляется на территории Республики Беларусь.
```

#### 1.3. Заменить на новый текст

**ПОЛНЫЙ ТЕКСТ ДЛЯ ЗАМЕНЫ:**

```markdown
## 4. О ТРАНСГРАНИЧНОЙ ПЕРЕДАЧЕ ПЕРСОНАЛЬНЫХ ДАННЫХ

4.1. Оператор осуществляет трансграничную передачу персональных данных при использовании Telegram-бота [@Novamedika_bot](https://t.me/Novamedika_bot).

4.2. Параметры трансграничной передачи:

| Параметр | Значение |
|----------|----------|
| **Иностранное государство** | Великобритания, Объединенные Арабские Эмираты |
| **Получатель ПД** | Telegram Messenger LLP (зарегистрировано в Великобритании) |
| **Цель передачи** | Предоставление услуг через Telegram-бот (вопросы фармацевтам, бронирование лекарств) |
| **Передаваемые ПД** | Telegram ID, имя, фамилия, номер телефона (при предоставлении), тексты сообщений |
| **Правовое основание** | Статья 9 Закона №99-З — согласие субъекта персональных данных с информированием о рисках |
| **Уровень защиты** | Не обеспечивается надлежащий уровень защиты (государства не включены в перечень НЦЗПД) |

4.3. Риски трансграничной передачи:

- Персональные данные могут быть доступны иностранным государственным органам в соответствии с законодательством соответствующих стран
- Отсутствие возможности применения механизмов защиты прав субъектов ПД, предусмотренных законодательством РБ
- Возможный доступ третьих лиц к данным в случае инцидентов безопасности у получателя

4.4. Меры минимизации рисков:

- Получение явного информированного согласия пользователя перед началом использования бота
- Шифрование чувствительных данных (Telegram ID, телефон) в базе данных оператора
- Минимизация объема передаваемых данных (только необходимые для оказания услуг)
- Возможность отказа от использования Telegram-бота в пользу web-интерфейса

4.5. Альтернативные каналы связи:

Пользователи, не согласные с трансграничной передачей данных, могут использовать:
- Web-сайт: [spravka.novamedika.com](https://spravka.novamedika.com) (обработка данных на территории РБ)
- Email: [support@novamedika.com](mailto:support@novamedika.com)
- Телефон: +375 (XX) XXX-XX-XX

4.6. Порядок получения согласия:

При первом обращении к Telegram-боту пользователь получает информацию о трансграничной передаче и должен явно подтвердить согласие. Без согласия использование бота невозможно.
```

#### 1.4. Добавить новый раздел 2.5

Вставить после раздела 2.4 (перед разделом 3):

```markdown
### 2.5. Особенности обработки персональных данных через мессенджеры

2.5.1. При использовании Telegram-бота обработка персональных данных имеет следующие особенности:

**Канал передачи данных:**
- Сообщения пользователей передаются через инфраструктуру Telegram Messenger LLP
- Серверы Telegram расположены за пределами Республики Беларусь (Великобритания, ОАЭ)
- Передача данных осуществляется по защищенному каналу (HTTPS/TLS)

**Объем передаваемых данных:**
- Telegram ID (уникальный идентификатор пользователя в Telegram)
- Имя и фамилия (из профиля пользователя Telegram)
- Номер телефона (только если пользователь явно предоставил его боту)
- Тексты сообщений (вопросы фармацевтам, ответы, история диалога)
- Дата и время сообщений

**Не передаются через Telegram:**
- Паспортные данные
- Данные банковских карт
- Адреса места жительства
- Геолокационные данные
- IP-адреса пользователей

**Хранение данных:**
- После получения через Telegram API данные сохраняются в базе данных PostgreSQL на серверах в Республике Беларусь
- Чувствительные данные (Telegram ID, номер телефона) шифруются алгоритмом AES-256
- Тексты сообщений хранятся в открытом виде для обеспечения функциональности Q&A системы
- Срок хранения: 1 год после последнего обращения (дата последнего вопроса или ответа)

2.5.2. Сравнение каналов связи:

| Параметр | Telegram Bot | Web-сайт | Email |
|----------|-------------|----------|-------|
| **Трансграничная передача** | ✅ Да (UK/UAE) | ❌ Нет (только РБ) | ❌ Нет (только РБ) |
| **Удобство** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Скорость ответа** | Мгновенно | Мгновенно | 1-2 дня |
| **Шифрование в transit** | TLS (Telegram) | TLS (HTTPS) | TLS (SMTP) |
| **Шифрование at rest** | AES-256 (в БД NovaMedika2) | AES-256 (в БД NovaMedika2) | N/A |
| **Контроль оператора** | Частичный (зависит от Telegram) | Полный | Полный |

Рекомендация: Для максимальной защиты персональных данных рекомендуется использовать web-сайт или email вместо Telegram-бота.
```

#### 1.5. Сохранить и закоммитить

```bash
git add oac/docs/04-privacy-policy.md
git commit -m "fix: Update privacy policy to reflect transboundary transfer via Telegram

- Replace false statement about no transboundary transfer
- Add detailed section 4 about Telegram data transfer to UK/UAE
- Add section 2.5 about messenger-specific processing
- Inform users about risks and alternatives
- Comply with Article 9 of Law #99-З

Refs: oac/privacy-policy/transboundary-transfer-telegram-analysis-2026-05-20.md"
git push
```

---

### Этап 2: Создание миграции БД (2-3 дня)

#### 2.1. Создать файл миграции

```bash
cd backend
uv run alembic revision -m "add_transboundary_consent_fields"
```

#### 2.2. Отредактировать миграцию

Открыть созданный файл в `backend/alembic/versions/XXXX_add_transboundary_consent_fields.py`:

```python
"""add transboundary consent fields

Revision ID: XXXX
Revises: previous_revision
Create Date: 2026-05-20 XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'XXXX'
down_revision: Union[str, None] = 'previous_revision'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление полей для согласия на трансграничную передачу"""
    op.add_column('qa_users',
        sa.Column('consent_transboundary_transfer', sa.Boolean(),
                  nullable=False, server_default='false'))
    op.add_column('qa_users',
        sa.Column('consent_transboundary_transfer_date', sa.DateTime(),
                  nullable=True))
    op.add_column('qa_users',
        sa.Column('transboundary_risks_acknowledged', sa.Boolean(),
                  nullable=False, server_default='false'))


def downgrade() -> None:
    """Откат добавления полей согласия на трансграничную передачу"""
    op.drop_column('qa_users', 'transboundary_risks_acknowledged')
    op.drop_column('qa_users', 'consent_transboundary_transfer_date')
    op.drop_column('qa_users', 'consent_transboundary_transfer')
```

#### 2.3. Применить миграцию локально для теста

```bash
uv run alembic upgrade head
```

#### 2.4. Закоммитить миграцию

```bash
git add backend/alembic/versions/XXXX_add_transboundary_consent_fields.py
git commit -m "feat: Add database fields for transboundary transfer consent

- consent_transboundary_transfer (Boolean)
- consent_transboundary_transfer_date (DateTime)
- transboundary_risks_acknowledged (Boolean)

Required for compliance with Article 9 of Law #99-З"
git push
```

---

### Этап 3: Обновление Telegram Bot (1 неделя)

#### 3.1. Обновить обработчик /start

Открыть файл: `backend/src/bot/handlers/common_handlers/commands.py`

Найти функцию `cmd_start` и заменить логику проверки согласия:

**ДО:**
```python
consent_given = user.consent_privacy_policy if hasattr(user, 'consent_privacy_policy') else False

if not consent_given and not is_pharmacist:
    # Показываем текст политики конфиденциальности с кнопками
    ...
```

**ПОСЛЕ:**
```python
consent_given = user.consent_privacy_policy if hasattr(user, 'consent_privacy_policy') else False
consent_transboundary = user.consent_transboundary_transfer if hasattr(user, 'consent_transboundary_transfer') else False

if not consent_given and not is_pharmacist:
    # Показываем расширенный текст с информацией о трансграничной передаче
    privacy_text = """
🔒 <b>Защита персональных данных</b>

Для использования сервиса необходимо ваше согласие на обработку персональных данных.

<b>⚠️ Важная информация о трансграничной передаче:</b>

Этот бот работает на платформе Telegram, серверы которой расположены
за пределами Республики Беларусь (Великобритания, ОАЭ).

При использовании бота ваши данные (Telegram ID, имя, сообщения)
передаются через инфраструктуру Telegram.

<b>Передаваемые данные:</b>
• Telegram ID (идентификатор)
• Ваше имя и фамилия из профиля
• Тексты ваших вопросов и ответов фармацевтов
• Номер телефона (если вы его предоставите)

<b>Риски:</b>
• Данные могут быть доступны иностранным госорганам
• Отсутствие механизмов защиты по законодательству РБ

<b>Меры защиты:</b>
• Ваши Telegram ID и телефон шифруются в нашей базе данных
• Мы минимизируем объем передаваемых данных
• Вы можете отказаться от использования бота и использовать web-сайт

📄 Полная политика: https://spravka.novamedika.com/privacy

Выберите действие:
"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен с условиями", callback_data="consent_privacy_policy")],
        [InlineKeyboardButton(text="❌ Не согласен", callback_data="decline_privacy_policy")],
        [InlineKeyboardButton(text="🌐 Использовать web-сайт вместо бота", url="https://spravka.novamedika.com")]
    ])
    await message.answer(privacy_text, parse_mode="HTML", reply_markup=keyboard)
    return

if not consent_transboundary:
    # Дополнительное согласие именно на трансграничную передачу
    transboundary_text = """
⚠️ <b>Подтверждение трансграничной передачи данных</b>

Вы подтверждаете, что:
1. Ознакомлены с рисками передачи данных через Telegram
2. Добровольно соглашаетесь на такую передачу
3. Понимаете, что можете использовать web-сайт вместо бота

Нажмите "Подтверждаю" для продолжения использования бота.
"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтверждаю", callback_data="consent_transboundary_transfer")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data="decline_transboundary_transfer")]
    ])
    await message.answer(transboundary_text, parse_mode="HTML", reply_markup=keyboard)
    return

# Если все согласия даны - показываем меню
...
```

#### 3.2. Добавить новые callback handlers

Открыть файл: `backend/src/bot/handlers/common_handlers/callbacks.py`

Добавить после существующих handlers:

```python
@router.callback_query(F.data == "consent_transboundary_transfer")
async def consent_transboundary_callback(callback: CallbackQuery, db: AsyncSession, user: User):
    """Обработка согласия на трансграничную передачу ПД"""
    user.consent_transboundary_transfer = True
    user.transboundary_risks_acknowledged = True
    user.consent_transboundary_transfer_date = get_utc_now_naive()
    await db.commit()

    logger.info(f"User {user.telegram_id} gave consent for transboundary transfer")
    await callback.answer("✅ Спасибо за подтверждение!")
    await callback.message.answer(
        "✅ <b>Согласие получено!</b>\n\n"
        "Теперь вы можете использовать все функции бота.\n\n"
        "Если у вас есть вопросы, напишите /help"
    )
    # Показать главное меню
    await show_main_menu(callback.message, user)


@router.callback_query(F.data == "decline_transboundary_transfer")
async def decline_transboundary_callback(callback: CallbackQuery):
    """Обработка отказа от трансграничной передачи"""
    await callback.message.answer(
        "❌ <b>Согласие не получено</b>\n\n"
        "Без согласия на трансграничную передачу данных использование Telegram-бота невозможно.\n\n"
        "Вы можете использовать альтернативные каналы связи:\n"
        "🌐 Web-сайт: https://spravka.novamedika.com\n"
        "📧 Email: support@novamedika.com\n"
        "📱 Телефон: +375 (XX) XXX-XX-XX\n\n"
        "Если вы передумаете, нажмите /start повторно."
    )
```

#### 3.3. Добавить функцию show_main_menu (если нет)

```python
async def show_main_menu(message: Message, user: User):
    """Показать главное меню пользователя"""
    # Импортировать клавиатуру
    from bot.keyboards.user_keyboards import get_user_inline_keyboard

    keyboard = get_user_inline_keyboard()
    await message.answer(
        f"👋 Добро пожаловать, {user.first_name}!\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )
```

#### 3.4. Закоммитить изменения

```bash
git add backend/src/bot/handlers/common_handlers/commands.py
git add backend/src/bot/handlers/common_handlers/callbacks.py
git commit -m "feat: Add transboundary transfer consent flow in Telegram bot

- Update /start command to inform about transboundary transfer
- Add separate consent for transboundary transfer (UK/UAE)
- Add callback handlers for consent/decline
- Provide alternative channels (web-site)
- Comply with Article 9 of Law #99-З

Refs: oac/privacy-policy/transboundary-transfer-telegram-analysis-2026-05-20.md"
git push
```

---

### Этап 4: Тестирование (2-3 дня)

#### 4.1. Локальное тестирование

```bash
# Запустить backend локально
cd backend
uv run uvicorn src.main:app --reload

# Запустить бота
uv run python -m bot.core
```

#### 4.2. Checklist для тестирования

- [ ] Новый пользователь видит запрос согласия при `/start`
- [ ] Текст содержит информацию о трансграничной передаче
- [ ] Есть ссылка на web-сайт как альтернативу
- [ ] Нажатие "✅ Согласен" запрашивает дополнительное согласие на трансграничную передачу
- [ ] Нажатие "✅ Подтверждаю" сохраняет согласие в БД
- [ ] Поля `consent_transboundary_transfer` и `transboundary_risks_acknowledged` установлены в `True`
- [ ] Поле `consent_transboundary_transfer_date` заполнено текущей датой
- [ ] Повторный `/start` после согласия показывает главное меню
- [ ] Нажатие "❌ Отказаться" показывает контакты поддержки и web-сайт

#### 4.3. Проверка в БД

```sql
-- Проверить, что поля созданы
\d qa_users

-- Проверить данные пользователя
SELECT telegram_id, consent_privacy_policy, consent_transboundary_transfer,
       transboundary_risks_acknowledged, consent_transboundary_transfer_date
FROM qa_users
WHERE telegram_id = [TEST_USER_ID];
```

---

### Этап 5: Деплой на production (1 день)

#### 5.1. Применить миграцию на production

```bash
# Подключиться к production серверу
ssh user@server

# Перейти в директорию проекта
cd /opt/novamedika-prod

# Применить миграцию
docker-compose exec backend alembic upgrade head

# Проверить успешность
docker-compose logs backend | grep "upgrade"
```

#### 5.2. Перезапустить backend

```bash
docker-compose restart backend
```

#### 5.3. Проверить работу бота

- Отправить `/start` новому пользователю
- Убедиться, что появляется запрос согласия
- Протестировать весь flow

---

## ПРОВЕРКА ГОТОВНОСТИ

### Checklist перед сдачей:

- [ ] Политика конфиденциальности обновлена (раздел 4 и 2.5)
- [ ] Миграция БД создана и применена
- [ ] Telegram Bot обновлен с новым consent flow
- [ ] Тестирование пройдено успешно
- [ ] Деплой на production выполнен
- [ ] Документация обновлена

---

## КОНТАКТЫ ДЛЯ ВОПРОСОВ

- **Юридические вопросы:** [EMAIL юриста]
- **Технические вопросы:** [EMAIL tech lead]
- **Тестирование:** [EMAIL QA engineer]

---

**Статус инструкции:** ✅ Готова к использованию
**Автор:** AI-ассистент
**Дата создания:** 20 мая 2026 г.
