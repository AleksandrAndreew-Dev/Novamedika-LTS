# Руководство по настройке автоматического шифрования персональных данных

## 📋 Обзор

Данное руководство описывает процесс настройки **автоматического шифрования** персональных данных при создании новых записей в базе данных NovaMedika2.

**Дата внедрения:** 05 мая 2026 г.  
**Ответственный:** Администратор backend  
**Класс ИС:** 3-ин (согласно требованиям ОАЦ)

---

## 🔧 Что было реализовано

### 1. Event Listeners для SQLAlchemy

Создан модуль `backend/src/db/encryption_events.py`, который автоматически шифрует персональные данные перед сохранением в БД:

**Зашифровываемые поля:**
- `User.telegram_id` → `telegram_id_encrypted`
- `User.phone` → `phone_encrypted`
- `BookingOrder.customer_phone` → `customer_phone_encrypted`
- `BookingOrder.telegram_id` → `telegram_id_encrypted`

**Механизм работы:**
```python
@event.listens_for(User, "before_insert")
@event.listens_for(User, "before_update")
def encrypt_user_data(mapper, connection, target):
    # Автоматически вызывается при INSERT/UPDATE
    if target.telegram_id and not target.telegram_id_encrypted:
        target.set_telegram_id(target.telegram_id)
```

### 2. Интеграция с приложением

Event listeners регистрируются автоматически при импорте модуля `db`:

```python
# backend/src/db/__init__.py
from . import encryption_events  # Регистрирует event listeners
```

---

## 🚀 Процедура внедрения на production

### Шаг 1: Подготовка сервера

```bash
# Подключиться к серверу
ssh novamedika@your-server.com

# Перейти в директорию проекта
cd /opt/novamedika-prod

# Создать backup базы данных (ОБЯЗАТЕЛЬНО!)
docker exec postgres-prod pg_dump -U novamedika novamedika_prod | \
  gzip > /backups/pre-encryption-auto_$(date +%Y%m%d_%H%M%S).sql.gz

# Проверить целостность backup
gunzip -t /backups/pre-encryption-auto_*.sql.gz
echo "✅ Backup создан успешно"
```

### Шаг 2: Деплой обновленного кода

```bash
# На локальной машине (ваш компьютер)
cd /path/to/Novamedika2

# Закоммитить изменения
git add backend/src/db/encryption_events.py
git add backend/src/db/__init__.py
git commit -m "feat: automatic encryption of personal data via SQLAlchemy events"

# Отправить в репозиторий
git push origin main

# GitHub Actions автоматически выполнит деплой
# Или выполнить ручной деплой:
npm run prod:deploy
```

### Шаг 3: Перезапуск backend

```bash
# На production сервере
cd /opt/novamedika-prod

# Перезапустить backend контейнер
docker restart backend-prod

# Подождать запуска
sleep 15

# Проверить логи на ошибки
docker logs --tail 100 backend-prod | grep -i "error\|exception"

# Проверить регистрацию event listeners
docker logs --tail 100 backend-prod | grep "Encryption event listeners"
```

**Ожидаемый вывод:**
```
INFO:db.encryption_events:Encryption event listeners registered successfully
```

### Шаг 4: Тестирование автоматического шифрования

#### 4.1 Создание тестового пользователя

```bash
# Открыть Telegram и найти бота @NovaMedikaBot
# Отправить команду /start
# Пройти регистрацию (ввести имя, телефон)

# Или через API (если есть доступ):
curl -X POST https://api.novamedika.com/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 999888777,
    "phone": "+375290000000",
    "first_name": "Test User",
    "consent_privacy_policy": true
  }'
```

#### 4.2 Проверка шифрования в БД

```bash
# Подключиться к PostgreSQL
docker exec -it postgres-prod psql -U novamedika -d novamedika_prod

# Проверить последнего созданного пользователя
SELECT 
    uuid,
    telegram_id,
    telegram_id_encrypted IS NOT NULL as has_encrypted_id,
    LENGTH(telegram_id_encrypted) as encrypted_id_length,
    phone,
    phone_encrypted IS NOT NULL as has_encrypted_phone,
    LENGTH(phone_encrypted) as encrypted_phone_length,
    created_at
FROM qa_users 
ORDER BY created_at DESC 
LIMIT 1;
```

**Ожидаемый результат:**
```
 uuid | telegram_id | has_encrypted_id | encrypted_id_length | phone | has_encrypted_phone | encrypted_phone_length | created_at
------+-------------+------------------+---------------------+-------+---------------------+------------------------+------------
 ...  | 999888777   | t                | 120                 | +...  | t                   | 100                    | 2026-05-05 ...
```

Если `has_encrypted_id = t` и `has_encrypted_phone = t` — **шифрование работает!** ✅

#### 4.3 Проверка расшифровки

```sql
-- Внутри psql проверить корректность расшифровки
SELECT 
    telegram_id as original_id,
    pgp_sym_decrypt(
        DECODE(telegram_id_encrypted, 'base64'),
        current_setting('app.encryption_key')
    ) as decrypted_id,
    CASE 
        WHEN telegram_id::text = pgp_sym_decrypt(DECODE(telegram_id_encrypted, 'base64'), current_setting('app.encryption_key'))
        THEN '✅ MATCH'
        ELSE '❌ MISMATCH'
    END as status
FROM qa_users 
ORDER BY created_at DESC 
LIMIT 1;
```

**Ожидаемый результат:** `status = ✅ MATCH`

#### 4.4 Тестирование BookingOrder

```bash
# Создать тестовый заказ через бота или API
# Затем проверить в БД:

docker exec postgres-prod psql -U novamedika -d novamedika_prod -c "
SELECT 
    uuid,
    customer_phone,
    customer_phone_encrypted IS NOT NULL as has_encrypted_phone,
    telegram_id,
    telegram_id_encrypted IS NOT NULL as has_encrypted_id,
    created_at
FROM booking_orders 
ORDER BY created_at DESC 
LIMIT 1;
"
```

### Шаг 5: Мониторинг логов

```bash
# Включить debug логирование для проверки шифрования
# Добавить в .env на сервере:
LOG_LEVEL=DEBUG

# Перезапустить backend
docker restart backend-prod

# Следить за логами при создании новых пользователей
docker logs -f backend-prod | grep -i "encrypt"
```

**Ожидаемые сообщения в логах:**
```
DEBUG:db.encryption_events:Encrypting telegram_id for user <uuid>
DEBUG:db.encryption_events:Encrypting phone for user <uuid>
```

---

## ✅ Критерии успешного внедрения

Автоматическое шифрование считается настроенным правильно, если:

1. ✅ Event listeners зарегистрированы без ошибок (проверка логов)
2. ✅ Новые пользователи имеют заполненные `*_encrypted` поля
3. ✅ Расшифровка возвращает исходные значения
4. ✅ Старые записи не затронуты (обратная совместимость)
5. ✅ Производительность не ухудшилась (шифрование занимает <10ms)

---

## 🔍 Диагностика проблем

### Проблема 1: Event listeners не регистрируются

**Симптомы:** В логах нет сообщения "Encryption event listeners registered"

**Решение:**
```bash
# Проверить, что файл encryption_events.py существует
ls -la /opt/novamedika-prod/backend/src/db/encryption_events.py

# Проверить импорт в __init__.py
grep "encryption_events" /opt/novamedika-prod/backend/src/db/__init__.py

# Перезапустить backend
docker restart backend-prod
```

### Проблема 2: Данные не шифруются

**Симптомы:** Поля `*_encrypted` остаются NULL после создания записи

**Решение:**
```bash
# Проверить наличие ENCRYPTION_KEY в .env
grep ENCRYPTION_KEY /opt/novamedika-prod/.env

# Проверить ключ в PostgreSQL
docker exec postgres-prod psql -U novamedika -d novamedika_prod -c "SHOW app.encryption_key;"

# Если ключ отсутствует, настроить его (см. fix_encryption.sh)
```

### Проблема 3: Ошибка шифрования в логах

**Симптомы:** В логах появляются ошибки "Error encrypting user data"

**Решение:**
```bash
# Посмотреть полный traceback ошибки
docker logs --tail 200 backend-prod | grep -A 10 "Error encrypting"

# Проверить формат ключа
docker exec postgres-prod psql -U novamedika -d novamedika_prod -c "
SELECT LENGTH(current_setting('app.encryption_key')) as key_length;
"

# Должно быть ~44 символа (base64-encoded 32-byte key)
```

---

## 📊 Метрики для мониторинга

После внедрения рекомендуется отслеживать:

```sql
-- Процент зашифрованных пользователей
SELECT 
    COUNT(*) as total_users,
    COUNT(telegram_id_encrypted) as encrypted_users,
    ROUND(COUNT(telegram_id_encrypted)::numeric / COUNT(*)::numeric * 100, 2) as encryption_percentage
FROM qa_users;

-- Процент зашифрованных заказов
SELECT 
    COUNT(*) as total_orders,
    COUNT(customer_phone_encrypted) as encrypted_orders,
    ROUND(COUNT(customer_phone_encrypted)::numeric / COUNT(*)::numeric * 100, 2) as encryption_percentage
FROM booking_orders;
```

**Цель:** 100% новых записей должны быть зашифрованы.

---

## 🔄 Откат изменений (при необходимости)

Если возникли критические проблемы:

```bash
# 1. Вернуть предыдущую версию кода
cd /opt/novamedika-prod
git checkout HEAD~1 -- backend/src/db/

# 2. Удалить импорт encryption_events из __init__.py
# (отредактировать файл вручную)

# 3. Перезапустить backend
docker restart backend-prod

# 4. Восстановить БД из backup (если нужно)
gunzip -c /backups/pre-encryption-auto_*.sql.gz | \
  docker exec -i postgres-prod psql -U novamedika -d novamedika_prod
```

---

## 📞 Контакты

| Роль | ФИО | Контакт |
|------|-----|---------|
| Администратор backend | [ФИО] | backend@example.com |
| Ответственный за ИБ | [ФИО] | security@example.com |
| DBA | [ФИО] | dba@example.com |

---

**Документ подготовил:** AI Assistant  
**Дата:** 05 мая 2026 г.  
**Статус:** Готово к внедрению  
**Требуется тестирование:** Да

## Endpoint массового удаления заказов бронирования

### Реализация

Добавлен новый endpoint `DELETE /api/orders/bulk-delete` для массового удаления заказов с фильтрацией.

**Требования:**
- **ADMIN API Key аутентификация** (заголовок `X-API-Key`, переменная окружения `ADMIN_API_KEYS`)
- Подтверждение удаления (`confirm=true`)
- Минимум один фильтр (pharmacy_id, status или before_date)

**Параметры запроса (BulkDeleteOrdersRequest):**
```python
{
    "confirm": true,  # Обязательное подтверждение
    "pharmacy_id": "uuid",  # Опционально: фильтр по аптеке
    "status": "pending|cancelled|confirmed|failed",  # Опционально: фильтр по статусу
    "before_date": "2026-01-01T00:00:00",  # Опционально: удалить заказы до этой даты
    "reason": "Причина удаления"  # Опционально: причина для логирования
}
```

**Конфигурация ADMIN_API_KEYS:**

В файле `.env` на production сервере:
```bash
# Admin API Keys для критичных операций (удаление данных, очистка БД)
ADMIN_API_KEYS=key1,key2,key3

# Пример:
ADMIN_API_KEYS=admin-secret-key-123,another-admin-key-456
```

**Примеры использования:**

1. Удалить все отмененные заказы:
```bash
curl -X DELETE https://api.novamedika.com/api/orders/bulk-delete \
  -H "X-API-Key: YOUR_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "confirm": true,
    "status": "cancelled",
    "reason": "Очистка старых отмененных заказов"
  }'
```

2. Удалить заказы конкретной аптеки старше определенной даты:
```bash
curl -X DELETE https://api.novamedika.com/api/orders/bulk-delete \
  -H "X-API-Key: YOUR_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "confirm": true,
    "pharmacy_id": "550e8400-e29b-41d4-a716-446655440000",
    "before_date": "2025-12-31T23:59:59",
    "reason": "Удаление старых заказов аптеки"
  }'
```

3. Удалить все pending заказы:
```bash
curl -X DELETE https://api.novamedika.com/api/orders/bulk-delete \
  -H "X-API-Key: YOUR_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "confirm": true,
    "status": "pending",
    "reason": "Очистка неподтвержденных заказов"
  }'
```

**Ответ при успехе:**
```json
{
    "status": "success",
    "message": "Successfully deleted 158 orders",
    "deleted_count": 158,
    "filters": {
        "pharmacy_id": null,
        "status": "cancelled",
        "before_date": null
    },
    "reason": "Очистка старых отмененных заказов"
}
```

**Защита от случайного удаления:**
1. Требуется явное подтверждение (`confirm=true`)
2. Запрещено удаление ВСЕХ заказов без фильтров
3. Логируется количество удаленных заказов и причина
4. **Требуется ADMIN API Key** (более высокий уровень доступа чем BOOKING_API_KEYS)

**Безопасность:**
- Endpoint требует ADMIN API Key (только администраторы)
- Нельзя удалить все заказы без указания фильтров
- Все операции логируются с указанием причины
- Транзакционность: rollback при ошибке
- Используется та же функция проверки что и для `/qa/drop`, `/qa/stats` и других admin endpoints

**Файлы реализации:**
- Схема: `backend/src/db/booking_schemas.py` (BulkDeleteOrdersRequest)
- Endpoint: `backend/src/routers/booking_orders.py` (bulk_delete_orders)
- Аутентификация: `verify_admin_api_key()` использует `os.getenv("ADMIN_API_KEYS")`
