# Реализация обработки персональных данных в проекте Novamedika2

**Дата создания:** 4 мая 2026 г.  
**Версия:** 1.0  
**Класс ИС:** 3-ин  
**Соответствие:** Закон РБ №99-З, Приказ ОАЦ №66  

---

## 📋 Содержание

1. [Общая архитектура системы](#общая-архитектура-системы)
2. [Категории субъектов и обрабатываемые данные](#категории-субъектов-и-обрабатываемые-данные)
3. [Техническая реализация шифрования](#техническая-реализация-шифрования)
4. [Механизмы аутентификации и сессий](#механизмы-аутентификации-и-сессий)
5. [Сбор и обработка данных через Telegram Bot](#сбор-и-обработка-данных-через-telegram-bot)
6. [Сроки хранения персональных данных](#сроки-хранения-персональных-данных)
7. [CI/CD и автоматизация миграций](#cicd-и-автоматизация-миграций)
8. [Политика конфиденциальности](#политика-конфиденциальности)
9. [Пробелы в реализации](#пробелы-в-реализации)
10. [Рекомендации по улучшению](#рекомендации-по-улучшению)

---

## Общая архитектура системы

### Технологический стек

```
┌─────────────────────────────────────────────────────────────┐
│                    ПРОДАКШН СЕРВЕР                           │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Frontend   │    │   Backend    │    │ Celery Worker│   │
│  │   (React)    │◄──►│  (FastAPI)   │◄──►│  (Tasks)     │   │
│  └──────────────┘    └──────┬───────┘    └──────────────┘   │
│                             │                                │
│                    ENCRYPTION_KEY                            │
│                    из .env файла                             │
│                             │                                │
│                      ┌──────▼───────┐                        │
│                      │ encryption.py│                        │
│                      │  (Fernet)    │                        │
│                      └──────┬───────┘                        │
│                             │                                │
│  ┌──────────────────────────▼──────────────────────────┐    │
│  │              PostgreSQL Database                     │    │
│  │                                                       │    │
│  │  ┌─────────────────────────────────────────┐        │    │
│  │  │  pgcrypto extension                     │        │    │
│  │  │  - pgp_sym_encrypt()                    │        │    │
│  │  │  - pgp_sym_decrypt()                    │        │    │
│  │  └─────────────────────────────────────────┘        │    │
│  │                                                       │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │                  Redis (Sessions)                     │    │
│  │  - БД /0: Celery Broker                              │    │
│  │  - БД /1: Session Storage (TTL 24h)                  │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Компоненты системы

**Backend:**
- FastAPI (Python 3.11+)
- SQLAlchemy ORM (асинхронный)
- Alembic (миграции БД)
- Aiogram 3.x (Telegram Bot)
- Celery + Redis (фоновые задачи)

**Frontend:**
- React 18+
- Vite
- React Router DOM (HashRouter)

**База данных:**
- PostgreSQL 15+
- Расширение pgcrypto для шифрования
- Redis 7+ для сессий и брокера задач

**Инфраструктура:**
- Docker + Docker Compose
- Traefik (reverse proxy + SSL)
- CI/CD pipeline (Git-based deployment)

---

## Категории субъектов и обрабатываемые данные

### 1. Пользователи Telegram-бота (qa_users)

| Поле | Тип | Шифрование | Описание |
|------|-----|-----------|----------|
| `uuid` | UUID | ❌ Нет | Уникальный идентификатор записи |
| `telegram_id` | BigInteger | ⚠️ Открыто* | ID пользователя Telegram |
| `telegram_id_encrypted` | String(255) | ✅ Да | Зашифрованный Telegram ID |
| `first_name` | String(100) | ❌ Нет | Имя пользователя |
| `last_name` | String(100) | ❌ Нет | Фамилия пользователя |
| `telegram_username` | String(100) | ❌ Нет | Username в Telegram |
| `phone` | String(20) | ⚠️ Открыто* | Номер телефона |
| `phone_encrypted` | String(255) | ✅ Да | Зашифрованный телефон |
| `user_type` | String(20) | ❌ Нет | Тип: customer/pharmacist |
| `created_at` | DateTime | ❌ Нет | Дата создания |

*\*Оставлены для обратной совместимости во время миграции*

### 2. Фармацевты (qa_pharmacists)

| Поле | Тип | Шифрование | Описание |
|------|-----|-----------|----------|
| `uuid` | UUID | ❌ Нет | Уникальный идентификатор |
| `user_id` | UUID | ❌ Нет | Ссылка на qa_users |
| `pharmacy_info` | JSON | ❌ Нет | Информация об аптеке |
| `is_active` | Boolean | ❌ Нет | Статус активности |
| `is_online` | Boolean | ❌ Нет | Онлайн статус |
| `last_seen` | DateTime | ❌ Нет | Время последней активности |
| `created_at` | DateTime | ❌ Нет | Дата регистрации |

**Примечание:** Данные фармацевта хранятся в связанной таблице `qa_users` с теми же полями шифрования.

### 3. Заказчики бронирования (booking_orders)

| Поле | Тип | Шифрование | Описание |
|------|-----|-----------|----------|
| `uuid` | UUID | ❌ Нет | Уникальный идентификатор заказа |
| `external_order_id` | String(255) | ❌ Нет | Внешний ID заказа |
| `pharmacy_id` | UUID | ❌ Нет | Ссылка на аптеку |
| `product_id` | UUID | ❌ Нет | Ссылка на товар |
| `product_name` | String(255) | ❌ Нет | Название товара (кэш) |
| `quantity` | Integer | ❌ Нет | Количество |
| `customer_name` | String(100) | ❌ Нет | Имя заказчика |
| `customer_phone` | String(20) | ⚠️ Открыто* | Телефон заказчика |
| `customer_phone_encrypted` | String(255) | ✅ Да | Зашифрованный телефон |
| `telegram_id` | BigInteger | ⚠️ Открыто* | Telegram ID |
| `telegram_id_encrypted` | String(255) | ✅ Да | Зашифрованный Telegram ID |
| `status` | String(50) | ❌ Нет | Статус заказа |
| `created_at` | DateTime | ❌ Нет | Дата создания |

### 4. Вопросы и ответы (qa_questions, qa_answers)

| Таблица | Поля ПД | Шифрование |
|---------|---------|-----------|
| `qa_questions` | `user_id` (UUID) | ❌ Нет (не прямой идентификатор) |
| `qa_questions` | Текст вопроса | ❌ Нет (содержит косвенные ПД) |
| `qa_answers` | `pharmacist_id` (UUID) | ❌ Нет |
| `qa_answers` | Текст ответа | ❌ Нет |

---

## Техническая реализация шифрования

### Алгоритм шифрования

Используется **гибридный подход**:

1. **Application-level шифрование (Fernet):**
   - Библиотека: `cryptography.fernet`
   - Алгоритм: AES-128-CBC с HMAC-SHA256
   - Размер ключа: 32 байта (256 бит)
   - Автоматическая ротация IV
   - Защита от tampering (подделки данных)

2. **Database-level шифрование (pgcrypto):**
   - Расширение PostgreSQL: `pgcrypto`
   - Функции: `pgp_sym_encrypt()`, `pgp_sym_decrypt()`
   - Алгоритм: AES-256
   - Используется в миграциях Alembic

### Модуль шифрования

**Файл:** `backend/src/utils/encryption.py`

```python
from utils.encryption import encrypt_value, decrypt_value, encrypt_bigint, decrypt_bigint

# Шифрование строки
encrypted = encrypt_value("+375291234567")

# Дешифрование строки
decrypted = decrypt_value(encrypted)

# Шифрование BigInt (telegram_id)
encrypted_id = encrypt_bigint(123456789)

# Дешифрование BigInt
decrypted_id = decrypt_bigint(encrypted_id)
```

**Ключевые функции:**

```python
def get_encryption_key() -> bytes:
    """Получить ключ из переменной окружения ENCRYPTION_KEY"""
    
def encrypt_value(value: str) -> str:
    """Зашифровать строковое значение (base64-encoded результат)"""
    
def decrypt_value(encrypted_value: str) -> str:
    """Расшифровать значение"""
    
def encrypt_bigint(value: int) -> str:
    """Зашифровать BigInt (конвертирует в строку)"""
    
def decrypt_bigint(encrypted_value: str) -> int:
    """Расшифровать BigInt"""
```

### Модели данных с методами шифрования

#### User модель (`backend/src/db/qa_models.py`)

```python
class User(Base):
    __tablename__ = "qa_users"

    # Зашифрованные поля
    telegram_id_encrypted = Column(String(255), unique=True, nullable=True, index=True)
    phone_encrypted = Column(String(255), nullable=True)
    
    # Старые поля (для обратной совместимости)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Методы доступа
    def set_telegram_id(self, telegram_id: int):
        """Автоматически шифрует и сохраняет telegram_id"""
        from utils.encryption import encrypt_bigint
        if telegram_id is not None:
            self.telegram_id_encrypted = encrypt_bigint(telegram_id)
            self.telegram_id = telegram_id  # Обратная совместимость
    
    def get_telegram_id(self) -> int:
        """Автоматически расшифровывает telegram_id"""
        from utils.encryption import decrypt_bigint
        if self.telegram_id_encrypted:
            return decrypt_bigint(self.telegram_id_encrypted)
        return self.telegram_id  # Fallback
    
    def set_phone(self, phone: str):
        """Автоматически шифрует и сохраняет телефон"""
        from utils.encryption import encrypt_value
        if phone is not None:
            self.phone_encrypted = encrypt_value(phone)
            self.phone = phone  # Обратная совместимость
    
    def get_phone(self) -> str:
        """Автоматически расшифровывает телефон"""
        from utils.encryption import decrypt_value
        if self.phone_encrypted:
            return decrypt_value(self.phone_encrypted)
        return self.phone  # Fallback
```

#### BookingOrder модель (`backend/src/db/booking_models.py`)

```python
class BookingOrder(Base):
    __tablename__ = "booking_orders"

    # Зашифрованные поля
    customer_phone_encrypted = Column(String(255), nullable=True)
    telegram_id_encrypted = Column(String(255), nullable=True, index=True)
    
    # Старые поля (для обратной совместимости)
    customer_phone = Column(String(20), nullable=False)
    telegram_id = Column(BigInteger, nullable=True, index=True)
    
    # Методы доступа (аналогично User)
    def set_customer_phone(self, phone: str): ...
    def get_customer_phone(self) -> str: ...
    def set_telegram_id(self, telegram_id: int): ...
    def get_telegram_id(self) -> int: ...
```

### Миграция базы данных

**Файл:** `backend/alembic/versions/3b81fefeff37_add_encrypted_fields_for_personal_data.py`

**Шаги миграции:**

1. Добавление новых зашифрованных колонок
2. Создание индексов для encrypted полей
3. Шифрование существующих данных через pgcrypto
4. Проверка наличия расширения pgcrypto перед выполнением

```sql
-- Добавление колонок
ALTER TABLE qa_users 
ADD COLUMN telegram_id_encrypted VARCHAR(255),
ADD COLUMN phone_encrypted VARCHAR(255);

CREATE INDEX idx_qa_users_telegram_id_encrypted ON qa_users (telegram_id_encrypted);

-- Шифрование существующих данных
UPDATE qa_users 
SET telegram_id_encrypted = ENCODE(
    pgp_sym_encrypt(telegram_id::text, current_setting('app.encryption_key')),
    'base64'
)
WHERE telegram_id IS NOT NULL;
```

---

## Механизмы аутентификации и сессий

### JWT Аутентификация (Pharmacist Dashboard)

**Компоненты:**
- Access Token: 30 минут
- Refresh Token: 7 дней
- Хранение refresh tokens: таблица `refresh_tokens` в PostgreSQL

**Endpoints:**
- `POST /api/pharmacist/login` - вход
- `POST /api/pharmacist/refresh` - обновление токена
- `POST /api/pharmacist/logout` - выход (аннулирование refresh token)

### Redis Session Management (Telegram Bot)

**Файл:** `backend/src/auth/session_manager.py`

```python
async def create_session_token(telegram_id: int, pharmacist_uuid: str, user_id: str) -> str:
    """Создать сессию в Redis с TTL 24 часа"""
    token = str(uuid.uuid4())
    session_data = {
        'telegram_id': telegram_id,
        'pharmacist_uuid': pharmacist_uuid,
        'user_id': user_id,
        'created_at': time.time(),
        'expires_at': time.time() + 86400  # 24 hours
    }
    
    redis_client = get_redis_client()
    await redis_client.setex(
        f"session:{token}",
        86400,  # TTL 24 hours
        json.dumps(session_data)
    )
    
    return token
```

**Конфигурация Redis:**
- URL: `redis://:<password>@redis:6379/1`
- База `/1`: сессии
- База `/0`: Celery broker
- TTL сессии: 24 часа
- Формат ключа: `session:{token}`

### Role Middleware (Telegram Bot)

**Файл:** `backend/src/bot/middleware/role_middleware.py`

Middleware автоматически инжектирует зависимости в handlers:

```python
data["user"] = user              # User объект
data["pharmacist"] = pharmacist  # Pharmacist объект (если есть)
data["is_pharmacist"] = True/False  # Флаг роли
```

---

## Сбор и обработка данных через Telegram Bot

### Процесс регистрации пользователя

**Middleware:** `RoleMiddleware`

При каждом сообщении/callback от пользователя:

1. Извлекается `from_user.id` (Telegram ID)
2. Вызывается `get_or_create_user(db, telegram_id=user_id)`
3. Создается запись в `qa_users` если пользователь новый
4. Инжектируется объект `User` в handler

**Файл:** `backend/src/services/user_service.py`

```python
async def get_or_create_user(
    db: AsyncSession,
    telegram_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    telegram_username: str | None = None,
    user_type: str = "customer",
) -> User | None:
    """Найти или создать пользователя по Telegram ID"""
    
    # Поиск существующего пользователя
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        return user

    # Создание нового пользователя
    user = User(
        uuid=uuid.uuid4(),
        telegram_id=telegram_id,
        first_name=first_name,
        last_name=last_name,
        telegram_username=telegram_username,
        user_type=user_type,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
```

**⚠️ ВАЖНО:** В текущей реализации используется прямое присваивание `telegram_id`, а не метод `set_telegram_id()`. Это означает, что новые пользователи создаются с незашифрованными данными!

### Регистрация фармацевта

**Файл:** `backend/src/bot/handlers/registration.py`

Процесс регистрации включает сбор:
- Секретное слово (проверка)
- Сеть аптек
- Номер аптеки
- Роль в аптеке
- Имя, фамилия, отчество

После регистрации создается запись в `qa_pharmacists` с ссылкой на `qa_users`.

### Обработка вопросов пользователей

Когда пользователь отправляет сообщение (не команду):

1. Trigger: `@router.message(F.text & ~F.command)`
2. Handler: `unknown_command()` в `commands.py`
3. Вызывается `try_create_question()` для создания вопроса
4. Вопрос сохраняется в `qa_questions` с `user_id` (UUID)

---

## Сроки хранения персональных данных

Согласно политике конфиденциальности (`oac/docs/04-privacy-policy.md`):

| Цель обработки | Категория | Срок хранения | Основание удаления |
|---------------|-----------|--------------|-------------------|
| Регистрация фармацевтов | Фармацевты | 1 год после прекращения сотрудничества | Дата удаления аккаунта или прекращения активности |
| Онлайн-консультации (Q&A) | Пользователи | 1 год после последнего обращения | Дата последнего вопроса или ответа |
| Оформление заказов | Заказчики | 3 года с даты оформления заказа | Дата создания заказа + 3 года |
| Синхронизация с аптеками | Представители аптек | До следующей синхронизации + 30 дней | Дата последней синхронизации |
| Информационная безопасность | Все пользователи | 1 год с даты создания записи | Дата создания лога + 1 год |

**⚠️ РЕАЛИЗАЦИЯ:** В коде отсутствует автоматическое удаление данных по истечении сроков хранения. Требуется реализовать Celery задачу для очистки устаревших данных.

---

## CI/CD и автоматизация миграций

### Deployment Pipeline

**Docker Compose файлы:**
- `docker-compose.traefik.prod.yml` - production
- `docker-compose.traefik.dev.yml` - development

**Автоматические миграции:**

Миграции выполняются автоматически при старте контейнера backend через `entrypoint.sh`:

```bash
#!/bin/bash
# backend/entrypoint.sh

# Применение миграций Alembic
alembic upgrade head

# Запуск приложения
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
```

**Преимущества:**
- ✅ Исключает человеческий фактор
- ✅ Гарантирует консистентность схем БД
- ✅ Работает при каждом рестарте контейнера
- ✅ Поддерживает rollback через Alembic

### Webhook Setup

Telegram bot webhook настраивается через скрипт:

**Файл:** `backend/src/scripts/set_webhook.py`

```python
# Настройка webhook при деплое
await bot.set_webhook(
    url=f"https://{WEBHOOK_DOMAIN}/webhook/",
    secret_token=TELEGRAM_WEBHOOK_SECRET,
    allowed_updates=["message", "callback_query"]
)
```

---

## Политика конфиденциальности

**Файл:** `oac/docs/04-privacy-policy.md`

### Ключевые разделы:

1. **Общие положения**
   - Оператор: [НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ]
   - Класс ИС: 3-ин
   - Территория обработки: Республика Беларусь

2. **Правовые основания обработки**
   - Статья 6 Закона №99-З — согласие субъекта
   - Статья 6 Закона №99-З — исполнение договора
   - Законный интерес оператора (безопасность)

3. **Меры защиты**
   - JWT аутентификация
   - Разграничение доступа по ролям
   - Шифрование чувствительных данных
   - Логирование событий безопасности

4. **Права субъектов ПД**
   - Право на доступ к своим данным
   - Право на исправление неточных данных
   - Право на удаление (право быть забытым)
   - Право на отзыв согласия

**⚠️ НЕДОСТАТКИ:**
- Отсутствует механизм реализации права на удаление (GDPR-style deletion)
- Нет endpoint для запроса копии персональных данных
- Не реализован механизм отзыва согласия

---

## Пробелы в реализации

### 🔴 КРИТИЧЕСКИЕ

1. **Шифрование не активировано полностью**
   - Код шифрования написан, но не везде используется
   - `get_or_create_user()` использует прямое присваивание `telegram_id` вместо `set_telegram_id()`
   - Новые пользователи создаются с незашифрованными данными
   
2. **Отсутствие централизованного логирования**
   - Логи хранятся только в Docker контейнерах
   - Нет retention policy (минимум 1 год по требованиям ОАЦ)
   - Нет мониторинга событий безопасности
   
3. **Нет автоматического удаления данных**
   - Сроки хранения определены в политике, но не реализованы в коде
   - Отсутствуют Celery задачи для очистки устаревших ПД

4. **Отсутствие аудита доступа к ПД**
   - Не логируется кто, когда и к каким данным обращался
   - Нет таблицы audit_logs

### 🟡 ВАЖНЫЕ

5. **Не реализованы права субъектов ПД**
   - Нет endpoint для экспорта данных (data portability)
   - Нет механизма удаления аккаунта (right to be forgotten)
   - Нет формы отзыва согласия

6. **Слабая защита API endpoints**
   - Некоторые endpoints не требуют аутентификации
   - Нет rate limiting для предотвращения brute-force
   - Отсутствует CORS validation для всех origins

7. **Backup стратегия не автоматизирована**
   - Есть скрипт `scripts/backup.sh`, но нет автоматического расписания
   - Нет тестирования восстановления из backup
   - Нет шифрования backup файлов

### 🟢 РЕКОМЕНДУЕМЫЕ

8. **Улучшение документации**
   - Отсутствует руководство администратора СЗИ
   - Нет руководства пользователя СЗИ
   - Отсутствует программа и методика испытаний (ПМИ)

9. **Тестирование безопасности**
   - Не проводился penetration test
   - Нет регулярных vulnerability scans
   - Отсутствует security audit code review

---

## Рекомендации по улучшению

### Приоритет 1: Немедленные действия (1-2 недели)

1. **Активировать шифрование для новых пользователей**
   
   Исправить `get_or_create_user()`:
   ```python
   user = User(uuid=uuid.uuid4())
   user.set_telegram_id(telegram_id)  # Вместо telegram_id=telegram_id
   if first_name:
       user.first_name = first_name
   # ... остальные поля
   ```

2. **Настроить централизованное логирование**
   
   Варианты:
   - ELK Stack (Elasticsearch, Logstash, Kibana)
   - Graylog
   - Loki + Grafana
   
   Минимальные требования:
   - Хранение логов ≥ 1 год
   - Логирование событий аутентификации
   - Логирование доступа к ПД
   - Alerting на подозрительную активность

3. **Реализовать автоматическое удаление данных**
   
   Создать Celery задачу:
   ```python
   @celery_app.task
   def cleanup_expired_personal_data():
       """Удалить ПД по истечении сроков хранения"""
       
       # Удалить вопросы старше 1 года
       one_year_ago = datetime.utcnow() - timedelta(days=365)
       await db.execute(
           delete(Question).where(Question.created_at < one_year_ago)
       )
       
       # Удалить заказы старше 3 лет
       three_years_ago = datetime.utcnow() - timedelta(days=3*365)
       await db.execute(
           delete(BookingOrder).where(BookingOrder.created_at < three_years_ago)
       )
       
       await db.commit()
   ```
   
   Расписание: ежедневно в 02:00 UTC

### Приоритет 2: Краткосрочные улучшения (1 месяц)

4. **Реализовать права субъектов ПД**
   
   Endpoints:
   - `GET /api/user/data-export` - экспорт всех ПД пользователя
   - `DELETE /api/user/account` - удаление аккаунта
   - `POST /api/user/consent/revoke` - отзыв согласия

5. **Настроить автоматический backup**
   
   Cron job для backup:
   ```bash
   # /etc/cron.d/novamedika-backup
   0 3 * * * root /path/to/scripts/backup.sh >> /var/log/backup.log 2>&1
   ```
   
   Требования:
   - Ежедневный полный backup БД
   - Хранение backup ≥ 30 дней
   - Шифрование backup файлов
   - Тестирование восстановления раз в квартал

6. **Провести penetration testing**
   
   Варианты:
   - OWASP ZAP (бесплатно, автоматизированно)
   - Внешний аудит ($1000-5000)
   
   Фокус areas:
   - SQL injection
   - XSS vulnerabilities
   - Authentication bypass
   - Data exposure

### Приоритет 3: Среднесрочные улучшения (3 месяца)

7. **Подготовить документы для аттестации ОАЦ**
   
   Необходимые документы:
   - Руководство администратора СЗИ
   - Руководство пользователя СЗИ
   - Программа и методика испытаний (ПМИ)
   - Акт классификации ИС (уже есть)
   - Модель угроз (требуется разработать)

8. **Улучшить мониторинг и alerting**
   
   Внедрить:
   - Prometheus + Grafana для метрик
   - Alertmanager для уведомлений
   - Health checks для всех сервисов
   - Uptime monitoring

9. **Реализовать двухфакторную аутентификацию (2FA)**
   
   Для фармацевтов и администраторов:
   - TOTP (Time-based One-Time Password)
   - SMS verification (опционально)
   - Email confirmation

---

## Заключение

### Текущий статус соответствия ОАЦ

| Требование | Статус | Комментарий |
|-----------|--------|-------------|
| Классификация ИС (3-ин) | ✅ Выполнено | Акт классификации создан |
| Шифрование ПД | ⚠️ Частично | Код есть, но не везде используется |
| Аутентификация | ✅ Выполнено | JWT + Redis sessions |
| Разграничение доступа | ✅ Выполнено | Role-based middleware |
| Политика конфиденциальности | ✅ Выполнено | Документ создан |
| Централизованное логирование | ❌ Не выполнено | Требуется ELK/Graylog |
| Автоматическое удаление ПД | ❌ Не выполнено | Нет Celery задач |
| Penetration testing | ❌ Не выполнено | Требуется аудит |
| Backup стратегия | ⚠️ Частично | Скрипт есть, нет автоматизации |
| Права субъектов ПД | ❌ Не выполнено | Нет endpoints |

**Общий уровень готовности:** ~50%

### Следующие шаги

1. **Немедленно:** Исправить создание пользователей с шифрованием
2. **В течение 2 недель:** Настроить логирование и автоматическое удаление
3. **В течение 1 месяца:** Реализовать права субъектов ПД и backup
4. **В течение 3 месяцев:** Провести pentest и подготовить документы для аттестации

---

**Документ создан:** 4 мая 2026 г.  
**Автор:** AI Assistant  
**Для проекта:** NovaMedika2  
**Статус:** Актуальный  
**Версия:** 1.0
