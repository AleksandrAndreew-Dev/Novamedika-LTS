# РЕГЛАМЕНТ
## сроков хранения и удаления персональных данных

### информационной системы NovaMedika2

---

**[НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ]**

**Версия:** 1.0
**Дата утверждения:** «___» ____________ 20___ г.

---

## 1. ОБЩИЕ ПОЛОЖЕНИЯ

1.1. Настоящий регламент определяет сроки хранения и порядок удаления персональных данных в ИС NovaMedika2.

1.2. Регламент разработан в соответствии с:
- Законом Республики Беларусь №99-З «О защите персональных данных» от 07.05.2021
- Политикой обработки персональных данных NovaMedika2

---

## 2. СРОКИ ХРАНЕНИЯ ПЕРСОНАЛЬНЫХ ДАННЫХ

### 2.1. Таблица сроков

| Категория ПД | Цель обработки | Срок хранения | Критерий отсчёта | Таблицы БД |
|-------------|---------------|--------------|-----------------|-----------|
| Данные пользователей (Q&A) | Онлайн-консультации | 1 год | Дата последнего обращения | `qa_users`, `qa_questions`, `qa_answers`, `qa_dialog_messages` |
| Данные фармацевтов | Регистрация, консультации | 1 год | Дата удаления аккаунта или прекращения активности | `qa_users`, `qa_pharmacists` |
| Заказы на лекарства | Оформление заказов | 3 года | Дата оформления заказа | `booking_orders` |
| Логи событий ИБ | Информационная безопасность | 1 год | Дата создания записи | Docker logs, Loki |
| CSV-данные аптек | Синхронизация с аптеками | До следующей синхронизации + 30 дней | Дата последней синхронизации | `products`, `pharmacies`, `sync_logs` |
| JWT refresh tokens | Аутентификация | 7 дней | Дата создания | `refresh_tokens` |
| Логи аутентификации | Информационная безопасность | 1 год | Дата создания | Docker logs, Loki |

### 2.2. Правовые основания сроков

| Срок | Основание |
|------|----------|
| 1 год (пользователи) | Пункт 5 статьи 4 Закона №99-З (неизбыточность), согласие субъекта |
| 1 год (фармацевты) | Пункт 5 статьи 4 Закона №99-З, согласие субъекта |
| 3 года (заказы) | Статья 6 Закона №99-З (исполнение договора), законодательство о бухгалтерском учёте |
| 1 год (логи ИБ) | Приказ ОАЦ №66 (приложение 3, требование 1.2) |
| 30 дней (CSV) | Статья 6 Закона №99-З (исполнение договора с аптеками) |
| 7 дней (refresh tokens) | Техническая необходимость, пункт 5 статьи 4 Закона №99-З |

---

## 3. ПОРЯДОК УДАЛЕНИЯ ПЕРСОНАЛЬНЫХ ДАННЫХ

### 3.1. Автоматическое удаление

**Периодичность:** ежедневно, 03:00 (UTC+3)

**Задача Celery:** `cleanup_expired_personal_data`

```python
@celery_app.task(bind=True, name="tasks.cleanup_expired_personal_data")
def cleanup_expired_personal_data(self):
    """
    Автоматическое удаление персональных данных по истечении сроков хранения.
    Запускается ежедневно в 03:00 (UTC+3).
    """
```

### 3.2. Логика удаления по категориям

#### 3.2.1. Данные пользователей (Q&A) — 1 год

**Критерий:** `qa_questions.answered_at < NOW() - INTERVAL '1 year'`

**Действия:**
1. Анонимизировать `qa_users`: удалить ФИ, телефон, telegram_id (оставить UUID)
2. Удалить `qa_questions` старше 1 года
3. Удалить связанные `qa_answers`
4. Удалить связанные `qa_dialog_messages`
5. Зафиксировать в журнале удаления

#### 3.2.2. Данные фармацевтов — 1 год неактивности

**Критерий:** `qa_pharmacists.last_seen < NOW() - INTERVAL '1 year'` И `qa_pharmacists.is_active = false`

**Действия:**
1. Анонимизировать `qa_users`: удалить ФИ, телефон, telegram_id
2. Удалить `qa_pharmacists`
3. Зафиксировать в журнале удаления

#### 3.2.3. Заказы — 3 года

**Критерий:** `booking_orders.created_at < NOW() - INTERVAL '3 years'`

**Действия:**
1. Анонимизировать `booking_orders`: удалить customer_name, customer_phone
2. Сохранить product_id, pharmacy_id, quantity (статистика)
3. Зафиксировать в журнале удаления

#### 3.2.4. Refresh tokens — 7 дней

**Критерий:** `refresh_tokens.expires_at < NOW()` ИЛИ `refresh_tokens.revoked = true`

**Действия:**
1. Удалить все истёкшие и отозванные токены
2. Зафиксировать количество удалённых

#### 3.2.5. CSV-данные аптек — 30 дней после обновления

**Критерий:** `sync_logs.created_at < NOW() - INTERVAL '30 days'` И существует более новая синхронизация

**Действия:**
1. Удалить старые записи `sync_logs`
2. Продукты (`products`) не удаляются — они обновляются при синхронизации
3. Зафиксировать в журнале удаления

### 3.3. Удаление по запросу субъекта

**Срок исполнения:** 30 календарных дней

**Порядок:**
1. Получить запрос на email: privacy@novamedika.com
2. Верифицировать личность субъекта
3. Найти все ПД субъекта в БД
4. Удалить или анонимизировать
5. Уведомить субъекта о выполнении
6. Зафиксировать в журнале удалений

**Исключения:** Оператор вправе сохранить ПД, если обработка необходима для исполнения законодательства (например, хранение логов в течение 1 года по требованию ОАЦ).

---

## 4. ЖУРНАЛ УДАЛЕНИЯ ПЕРСОНАЛЬНЫХ ДАННЫХ

### 4.1. Форма записи

| Поле | Описание |
|------|----------|
| Дата и время | YYYY-MM-DD HH:MM:SS (UTC+3) |
| Категория ПД | Пользователи / Фармацевты / Заказы / Токены / CSV |
| Основание | Автоматическое / По запросу субъекта |
| Количество записей | Число удалённых записей |
| Таблицы | Перечень затронутых таблиц |
| Ответственный | ФИО (или "Автоматически") |
| Результат | Успешно / Ошибка |

### 4.2. Ведение журнала

- Автоматическое логирование в Loki (job: cleanup)
- Еженедельная проверка администратором
- Ежемесячный отчёт руководителю

---

## 5. ТЕХНИЧЕСКАЯ РЕАЛИЗАЦИЯ

### 5.1. Celery задача

**Файл:** `backend/src/tasks/tasks_cleanup.py`

**Расписание:** Celery beat, cron: `0 3 * * *` (ежедневно в 03:00)

**Логика:**
```python
from datetime import datetime, timedelta
from sqlalchemy import delete
from src.db.qa_models import QaUser, QaQuestion, QaAnswer, QaDialogMessage
from src.db.booking_models import BookingOrder, RefreshToken
from src.db.database import get_sync_session

def cleanup_expired_data():
    now = datetime.utcnow()

    with get_sync_session() as session:
        # 1. Refresh tokens (7 дней)
        expired_tokens = session.query(RefreshToken).filter(
            RefreshToken.expires_at < now
        ).all()
        for token in expired_tokens:
            session.delete(token)
        session.commit()

        # 2. Q&A данные (1 год)
        cutoff_date = now - timedelta(days=365)
        expired_questions = session.query(QaQuestion).filter(
            QaQuestion.answered_at < cutoff_date
        ).all()
        for question in expired_questions:
            # Удалить ответы и сообщения
            session.query(QaAnswer).filter(
                QaAnswer.question_id == question.uuid
            ).delete()
            session.query(QaDialogMessage).filter(
                QaDialogMessage.question_id == question.uuid
            ).delete()
            # Анонимизировать пользователя
            user = session.query(QaUser).filter(
                QaUser.uuid == question.user_id
            ).first()
            if user:
                user.first_name = "Анонимизирован"
                user.last_name = ""
                user.phone = ""
                user.telegram_username = ""
            session.delete(question)
        session.commit()

        # 3. Заказы (3 года)
        orders_cutoff = now - timedelta(days=365 * 3)
        expired_orders = session.query(BookingOrder).filter(
            BookingOrder.created_at < orders_cutoff
        ).all()
        for order in expired_orders:
            order.customer_name = "Анонимизирован"
            order.customer_phone = ""
        session.commit()

    return {"status": "success", "timestamp": now.isoformat()}
```

### 5.2. Celery beat расписание

**Файл:** `backend/src/tasks/celery_app.py`

```python
app.conf.beat_schedule = {
    "cleanup-expired-personal-data": {
        "task": "tasks.cleanup_expired_personal_data",
        "schedule": crontab(hour=3, minute=0),  # 03:00 UTC
    },
    # ... другие задачи
}
```

---

## 6. ОТВЕТСТВЕННЫЕ

| Роль | ФИО | Должность | Контакты |
|------|-----|-----------|----------|
| Администратор ИС | [ФИО] | [ДОЛЖНОСТЬ] | [EMAIL], [ТЕЛЕФОН] |
| Ответственный за защиту ПД | [ФИО] | [ДОЛЖНОСТЬ] | [EMAIL], [ТЕЛЕФОН] |

---

**УТВЕРЖДАЮ**

Генеральный директор
[НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ]

_______________ / [ФИО]

«___» ____________ 20___ г.

---

*Документ составлен в соответствии с:*
- *Законом Республики Беларусь №99-З «О защите персональных данных» от 07.05.2021*
- *Политикой обработки персональных данных NovaMedika2*
