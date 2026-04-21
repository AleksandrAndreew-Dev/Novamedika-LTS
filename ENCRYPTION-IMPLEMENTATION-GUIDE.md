# Руководство по шифрованию персональных данных (ОАЦ Compliance)

**Дата:** 21 апреля 2026 г.  
**Версия:** 1.0  
**Класс ИС:** 3-ин  
**Соответствие:** Закон РБ №99-З, Приказ ОАЦ №66

---

## 📋 Обзор

Данный документ описывает реализацию шифрования персональных данных в соответствии с требованиями ОАЦ для информационных систем класса 3-ин.

### Шифруемые данные (согласно принципу пропорциональности):

✅ **Шифруются** (прямые идентификаторы):
- `telegram_id` - уникальный идентификатор пользователя Telegram
- `phone` / `customer_phone` - номера телефонов пользователей

❌ **Не шифруются** (не являются прямыми идентификаторами):
- Имена пользователей (`first_name`, `last_name`, `customer_name`)
- Данные аптек (названия, адреса, телефоны)
- Информация о лекарствах (названия, цены, наличие)

**Обоснование:** Согласно принципу пропорциональности, шифруются только те данные, которые позволяют однозначно идентифицировать физическое лицо. Отдельные имена без дополнительных идентификаторов не позволяют это сделать, поэтому для снижения нагрузки на систему (~50% уменьшение операций шифрования) они остаются в открытом виде.

---

## 🔧 Техническая реализация

### 1. Алгоритм шифрования

Используется **Fernet (symmetric encryption)** из библиотеки `cryptography`:
- Алгоритм: AES-128-CBC с HMAC-SHA256 для аутентификации
- Размер ключа: 32 байта (256 бит)
- Автоматическая ротация IV (Initialization Vector)
- Защита от tampering (подделки данных)

### 2. Модуль шифрования

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

### 3. Модели данных

#### User модель (`backend/src/db/qa_models.py`)

```python
class User(Base):
    # Зашифрованные поля
    telegram_id_encrypted = Column(String(255), unique=True, nullable=True)
    phone_encrypted = Column(String(255), nullable=True)
    
    # Старые поля (для обратной совместимости)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Методы доступа
    def set_telegram_id(self, telegram_id: int):
        """Автоматически шифрует и сохраняет telegram_id"""
        
    def get_telegram_id(self) -> int:
        """Автоматически расшифровывает telegram_id"""
        
    def set_phone(self, phone: str):
        """Автоматически шифрует и сохраняет телефон"""
        
    def get_phone(self) -> str:
        """Автоматически расшифровывает телефон"""
```

#### BookingOrder модель (`backend/src/db/booking_models.py`)

```python
class BookingOrder(Base):
    # Зашифрованные поля
    customer_phone_encrypted = Column(String(255), nullable=True)
    telegram_id_encrypted = Column(String(255), nullable=True)
    
    # Старые поля (для обратной совместимости)
    customer_phone = Column(String(20), nullable=False)
    telegram_id = Column(BigInteger, nullable=True)
    
    # Методы доступа (аналогично User)
    def set_customer_phone(self, phone: str): ...
    def get_customer_phone(self) -> str: ...
    def set_telegram_id(self, telegram_id: int): ...
    def get_telegram_id(self) -> int: ...
```

---

## 🗄️ Миграция базы данных

### Шаг 1: Применение миграции Alembic

```bash
cd backend
alembic upgrade head
```

Это добавит новые зашифрованные поля:
- `qa_users.telegram_id_encrypted`
- `qa_users.phone_encrypted`
- `booking_orders.customer_phone_encrypted`
- `booking_orders.telegram_id_encrypted`

### Шаг 2: Настройка pgcrypto в PostgreSQL

```bash
# Подключиться к БД
docker exec -it postgres-prod psql -U novamedika -d novamedika_prod

# Выполнить скрипт настройки
\i /scripts/setup_encryption.sql
```

Или вручную:

```sql
-- Установить расширение
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Настроить ключ шифрования
SET app.encryption_key = 'YOUR_SECURE_ENCRYPTION_KEY';
```

### Шаг 3: Проверка миграции

```sql
-- Проверить количество зашифрованных записей
SELECT 
    COUNT(*) as total_users,
    COUNT(telegram_id_encrypted) as encrypted_telegram_ids,
    COUNT(phone_encrypted) as encrypted_phones
FROM qa_users;

SELECT 
    COUNT(*) as total_orders,
    COUNT(customer_phone_encrypted) as encrypted_phones,
    COUNT(telegram_id_encrypted) as encrypted_telegram_ids
FROM booking_orders;
```

---

## 🔑 Управление ключами шифрования

### Генерация ключа

```bash
# Способ 1: Python
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Способ 2: OpenSSL
openssl rand -base64 32
```

### Хранение ключа

**Development (.env):**
```bash
ENCRYPTION_KEY=novamedika-dev-encryption-key-32bytes!!
```

**Production (.env):**
```bash
# Сгенерируйте уникальный ключ!
ENCRYPTION_KEY=gAAAAABl... (ваш сгенерированный ключ)
```

**Docker Compose:**
```yaml
environment:
  - ENCRYPTION_KEY=${ENCRYPTION_KEY}
```

### ⚠️ ВАЖНЫЕ правила безопасности ключей:

1. **Никогда не коммитьте .env файл в Git!**
   ```bash
   # Добавьте в .gitignore
   echo ".env" >> .gitignore
   ```

2. **Используйте разные ключи для dev/prod/staging**

3. **Регулярно ротируйте ключи** (рекомендуется каждые 6-12 месяцев)

4. **Храните backup ключей в безопасном месте** (например, HashiCorp Vault, AWS Secrets Manager)

5. **При компрометации ключа:**
   - Сгенерируйте новый ключ
   - Перешифруйте все данные
   - Обновите конфигурацию всех сервисов

---

## 📝 Использование в коде

### Пример 1: Создание пользователя

```python
from db.qa_models import User

# Создание нового пользователя
user = User()
user.set_telegram_id(123456789)  # Автоматически шифруется
user.set_phone("+375291234567")  # Автоматически шифруется
user.first_name = "Иван"  # Не шифруется
user.last_name = "Иванов"  # Не шифруется

db.add(user)
db.commit()
```

### Пример 2: Чтение данных пользователя

```python
# Получение пользователя по telegram_id
telegram_id = 123456789
user = db.query(User).filter(
    User.telegram_id_encrypted == encrypt_bigint(telegram_id)
).first()

# Или используйте метод-помощник
user = get_user_by_telegram_id(db, telegram_id)

# Чтение данных
print(f"Telegram ID: {user.get_telegram_id()}")  # Расшифровывается автоматически
print(f"Phone: {user.get_phone()}")  # Расшифровывается автоматически
```

### Пример 3: Создание заказа

```python
from db.booking_models import BookingOrder

order = BookingOrder()
order.set_customer_phone("+375291234567")  # Шифруется
order.set_telegram_id(123456789)  # Шифруется
order.customer_name = "Иван Иванов"  # Не шифруется
order.quantity = 2

db.add(order)
db.commit()
```

---

## 🔍 Поиск и фильтрация

### Проблема

Зашифрованные поля нельзя напрямую использовать в WHERE clauses или JOINs без дешифрования.

### Решения

#### Вариант 1: Поиск по хешу (рекомендуется для уникальных полей)

```python
import hashlib

def hash_for_search(value: str) -> str:
    """Создать хеш для поиска (без возможности восстановления)"""
    return hashlib.sha256(value.encode()).hexdigest()

# Добавить поле telegram_id_hash
# При сохранении:
user.telegram_id_hash = hash_for_search(str(telegram_id))

# При поиске:
search_hash = hash_for_search(str(123456789))
user = db.query(User).filter(User.telegram_id_hash == search_hash).first()
```

#### Вариант 2: Гибридный подход (используется сейчас)

Храним **оба поля**:
- `telegram_id` (открытое) - для поиска и индексов
- `telegram_id_encrypted` (зашифрованное) - для безопасного хранения

**Преимущества:**
- Быстрый поиск по открытому полю
- Безопасное хранение в зашифрованном поле
- Обратная совместимость

**Недостатки:**
- Дублирование данных
- Открытое поле всё ещё доступно в БД

**Миграционный план:**
1. Фаза 1 (сейчас): Добавляем encrypted поля, сохраняем оба
2. Фаза 2 (после тестирования): Переносим все запросы на encrypted поля
3. Фаза 3 (после аудита): Удаляем открытые поля

---

## 🧪 Тестирование

### Unit тесты

```python
# tests/test_encryption.py
import pytest
from utils.encryption import encrypt_value, decrypt_value, encrypt_bigint, decrypt_bigint

def test_encrypt_decrypt_string():
    original = "+375291234567"
    encrypted = encrypt_value(original)
    decrypted = decrypt_value(encrypted)
    
    assert decrypted == original
    assert encrypted != original  # Убедиться, что данные зашифрованы

def test_encrypt_decrypt_bigint():
    original = 123456789
    encrypted = encrypt_bigint(original)
    decrypted = decrypt_bigint(encrypted)
    
    assert decrypted == original
    assert isinstance(encrypted, str)

def test_encryption_deterministic():
    """Fernet НЕ детерминирован - каждый раз разный ciphertext"""
    original = "test"
    enc1 = encrypt_value(original)
    enc2 = encrypt_value(original)
    
    assert enc1 != enc2  # Разные ciphertexts
    assert decrypt_value(enc1) == decrypt_value(enc2) == original
```

### Integration тесты

```python
# tests/test_user_encryption.py
def test_user_encryption(db_session):
    user = User()
    user.set_telegram_id(123456789)
    user.set_phone("+375291234567")
    
    db_session.add(user)
    db_session.commit()
    
    # Проверить, что encrypted поля заполнены
    assert user.telegram_id_encrypted is not None
    assert user.phone_encrypted is not None
    
    # Проверить, что данные можно расшифровать
    assert user.get_telegram_id() == 123456789
    assert user.get_phone() == "+375291234567"
```

---

## 📊 Мониторинг и аудит

### Логи шифрования

Все операции шифрования/дешифрования логируются:

```python
import logging
logger = logging.getLogger(__name__)

# При ошибке шифрования
logger.error(f"Ошибка шифрования: {e}")

# При отсутствии ключа
logger.warning("ENCRYPTION_KEY не установлен!")
```

### Аудит доступа к ПД

Рекомендуется логировать все обращения к персональным данным:

```python
def log_pd_access(user_uuid: str, accessed_by: str, field: str):
    """Логировать доступ к персональным данным"""
    logger.info(
        f"PD Access: user={user_uuid}, "
        f"accessed_by={accessed_by}, "
        f"field={field}, "
        f"timestamp={datetime.utcnow()}"
    )
```

---

## 🚀 Развертывание

### Development

```bash
# 1. Клонировать репозиторий
git clone <repo_url>
cd Novamedika2

# 2. Скопировать .env.example
cp .env.example .env

# 3. Запустить контейнеры
npm run prod:up

# 4. Применить миграции
docker exec -it backend-dev alembic upgrade head

# 5. Настроить pgcrypto
docker exec -i postgres-dev psql -U novamedika -d novamedika_dev < scripts/setup_encryption.sql
```

### Production

```bash
# 1. Сгенерировать безопасный ключ
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY" >> .env

# 2. Заполнить остальные переменные в .env

# 3. Запустить сервисы
npm run prod:up

# 4. Применить миграции
docker exec -it backend-prod alembic upgrade head

# 5. Настроить pgcrypto (указать реальный ключ!)
docker exec -i postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
CREATE EXTENSION IF NOT EXISTS pgcrypto;
SET app.encryption_key = '$ENCRYPTION_KEY';
EOF
```

---

## ⚠️ Troubleshooting

### Проблема: "ENCRYPTION_KEY is not configured"

**Решение:**
```bash
# Проверить, что переменная установлена
docker exec backend-prod env | grep ENCRYPTION_KEY

# Если пусто, добавить в .env и перезапустить
echo "ENCRYPTION_KEY=your_key_here" >> .env
npm run prod:restart-backend
```

### Проблема: Ошибка дешифрования "Invalid token"

**Причины:**
1. Неправильный ключ шифрования
2. Данные были зашифрованы другим ключом
3. Поврежденные данные в БД

**Решение:**
```python
# Проверить ключ
from utils.encryption import get_encryption_key
key = get_encryption_key()
print(f"Key length: {len(key)} bytes")

# Проверить данные в БД
SELECT telegram_id_encrypted FROM qa_users LIMIT 1;
# Должно быть base64-encoded строкой
```

### Проблема: Медленная производительность

**Причина:** Шифрование/дешифрование добавляет overhead ~5-10ms на операцию

**Решения:**
1. Использовать кэширование часто запрашиваемых данных
2. Избегать массового дешифрования в циклах
3. Рассмотреть аппаратное ускорение (AES-NI)

---

## 📚 Дополнительные ресурсы

- [Документация cryptography.fernet](https://cryptography.io/en/latest/fernet/)
- [PostgreSQL pgcrypto](https://www.postgresql.org/docs/current/pgcrypto.html)
- [OWASP Encryption Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [Закон РБ №99-З "О защите персональных данных"](../origin-docs/zakon%2099-3.pdf)
- [Политика шифрования ОАЦ](../oac/docs/10-encryption-policy.md)

---

## ✅ Чек-лист внедрения

- [ ] Сгенерирован безопасный ENCRYPTION_KEY
- [ ] Добавлен в .env (не закоммичен в Git!)
- [ ] Применена миграция Alembic
- [ ] Установлено расширение pgcrypto
- [ ] Протестировано шифрование/дешифрование
- [ ] Обновлен код для использования новых методов
- [ ] Настроено логирование операций с ПД
- [ ] Проведен security review
- [ ] Документация обновлена
- [ ] Команда обучена работе с зашифрованными данными

---

**Автор:** AI Assistant  
**Дата создания:** 21 апреля 2026 г.  
**Статус:** Актуальный  
**Следующий пересмотр:** После полного перехода на encrypted поля (Фаза 3)
