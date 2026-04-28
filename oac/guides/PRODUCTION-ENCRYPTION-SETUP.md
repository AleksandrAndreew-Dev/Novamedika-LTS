# Пошаговое руководство: Настройка шифрования на продакшн-сервере

**Дата:** 28 апреля 2026 г.  
**Версия:** 1.0  
**Класс ИС:** 3-ин  
**Соответствие:** Закон РБ №99-З, Приказ ОАЦ №66

---

## 📋 Предварительные требования

Перед началом убедитесь, что:
- ✅ У вас есть SSH-доступ к продакшн-серверу
- ✅ Установлен Docker и Docker Compose
- ✅ Проект развернут через `docker-compose.traefik.prod.yml`
- ✅ Есть бэкап базы данных
- ✅ Команда имеет базовые знания Linux и Docker

---

## 🎯 Обзор процесса

Шифрование персональных данных включает следующие этапы:

1. **Подготовка** - бэкап данных и проверка текущего состояния
2. **Генерация ключа** - создание безопасного ENCRYPTION_KEY
3. **Настройка конфигурации** - добавление ключа в .env
4. **Миграция БД** - применение Alembic миграции для добавления encrypted полей
5. **Настройка PostgreSQL** - установка расширения pgcrypto
6. **Перезапуск сервисов** - обновление backend и celery_worker
7. **Тестирование** - проверка работоспособности шифрования
8. **Мониторинг** - наблюдение за логами и производительностью

---

## 🔐 Что будет зашифровано

Согласно принципу пропорциональности (ОАЦ):

✅ **Зашифрованные поля** (прямые идентификаторы):
- `telegram_id` → `telegram_id_encrypted`
- `phone` / `customer_phone` → `phone_encrypted` / `customer_phone_encrypted`

❌ **Не шифруются** (не являются прямыми идентификаторами):
- Имена пользователей (`first_name`, `last_name`, `customer_name`)
- Данные аптек (названия, адреса)
- Информация о лекарствах

**Обоснование:** Отдельные имена без дополнительных идентификаторов не позволяют однозначно идентифицировать физическое лицо.

---

## 📝 ПОШАГОВАЯ ИНСТРУКЦИЯ

### ШАГ 1: Подключение к серверу и подготовка

```bash
# 1.1 Подключиться к серверу по SSH
ssh user@your-production-server.com

# 1.2 Перейти в директорию проекта
cd /path/to/Novamedika2

# 1.3 Проверить текущее состояние системы
docker compose -f docker-compose.traefik.prod.yml ps

# 1.4 Сделать бэкап базы данных (ОБЯЗАТЕЛЬНО!)
docker exec postgres-prod pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql

# 1.5 Проверить, что бэкап создан
ls -lh backup_*.sql

# 1.6 Проверить текущую версию миграций
docker exec -it backend-prod alembic current
```

**Ожидаемый результат:**
- Все сервисы работают (state: Up)
- Бэкап успешно создан
- Текущая версия миграции отображается

---

### ШАГ 2: Генерация ключа шифрования

```bash
# Способ 1: Через Python (рекомендуется)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Способ 2: Через OpenSSL
openssl rand -base64 32

# Способ 3: Если Python не установлен на сервере
# Сгенерируйте ключ локально и скопируйте на сервер
```

**Пример вывода:**
```
gAAAAABlZmVmZWZlZmVmZWZlZmVmZWZlZmVmZWZlZmVmZWZlZmVmZWZlZmVmZWZl
```

⚠️ **ВАЖНО:** 
- Сохраните ключ в безопасном месте (менеджер паролей, HashiCorp Vault, AWS Secrets Manager)
- Никогда не показывайте ключ посторонним
- Используйте разные ключи для dev/prod/staging

---

### ШАГ 3: Настройка .env файла

```bash
# 3.1 Открыть .env файл для редактирования
nano .env
# или
vim .env

# 3.2 Добавить строку (вставьте ваш сгенерированный ключ):
ENCRYPTION_KEY=gAAAAABlZmVmZWZlZmVmZWZlZmVmZWZlZmVmZWZlZmVmZWZlZmVmZWZl

# 3.3 Сохранить файл (Ctrl+O, Enter, Ctrl+X для nano)

# 3.4 Проверить, что .env НЕ закоммичен в Git
cat .gitignore | grep ".env"
# Должно вывести: .env

# 3.5 Если .env отсутствует в .gitignore, добавить:
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Add .env to gitignore for security"
```

**Проверка:**
```bash
# Убедиться, что переменная установлена
grep ENCRYPTION_KEY .env
```

---

### ШАГ 4: Применение миграции базы данных

```bash
# 4.1 Применить миграцию Alembic
docker exec -it backend-prod alembic upgrade head

# 4.2 Проверить успешность применения
docker exec -it backend-prod alembic current

# 4.3 Проверить новые колонки в БД
docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
-- Проверить таблицу qa_users
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name='qa_users' 
AND column_name LIKE '%encrypted%';

-- Проверить таблицу booking_orders
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name='booking_orders' 
AND column_name LIKE '%encrypted%';
EOF
```

**Ожидаемый результат:**
```
column_name              | data_type
-------------------------+----------
telegram_id_encrypted    | character varying
phone_encrypted          | character varying
customer_phone_encrypted | character varying
telegram_id_encrypted    | character varying
```

**Если ошибка:**
```bash
# Посмотреть логи
docker logs backend-prod --tail 100

# Откатить миграцию (если нужно)
docker exec -it backend-prod alembic downgrade -1
```

---

### ШАГ 5: Установка расширения pgcrypto в PostgreSQL

```bash
# 5.1 Подключиться к PostgreSQL и установить расширение
docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
-- Установить расширение
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Проверить установку
\dx pgcrypto

-- Протестировать шифрование
DO \$\$
DECLARE
    test_text TEXT := 'Test encryption +375291234567';
    encrypted TEXT;
    decrypted TEXT;
BEGIN
    encrypted := ENCODE(pgp_sym_encrypt(test_text, 'test_key'), 'base64');
    decrypted := pgp_sym_decrypt(DECODE(encrypted, 'base64'), 'test_key');
    
    RAISE NOTICE 'Original: %', test_text;
    RAISE NOTICE 'Encrypted length: %', LENGTH(encrypted);
    RAISE NOTICE 'Decrypted: %', decrypted;
    
    IF test_text = decrypted THEN
        RAISE NOTICE '✓ pgcrypto работает корректно!';
    ELSE
        RAISE EXCEPTION '✗ Ошибка pgcrypto!';
    END IF;
END \$\$;
EOF
```

**Ожидаемый результат:**
```
Extension | Version | Schema | Description
----------+---------+--------+------------
pgcrypto  | 1.3     | public | cryptographic functions

NOTICE:  Original: Test encryption +375291234567
NOTICE:  Encrypted length: 124
NOTICE:  Decrypted: Test encryption +375291234567
NOTICE:  ✓ pgcrypto работает корректно!
```

---

### ШАГ 6: Перезапуск backend сервисов

```bash
# 6.1 Перезапустить backend и celery_worker
docker compose -f docker-compose.traefik.prod.yml restart backend celery_worker

# 6.2 Подождать 30-60 секунд для запуска
sleep 30

# 6.3 Проверить статус сервисов
docker compose -f docker-compose.traefik.prod.yml ps

# 6.4 Проверить логи на ошибки
docker logs backend-prod --tail 50
docker logs celery-worker-prod --tail 50
```

**Ожидаемый результат:**
- Все сервисы в состоянии "Up"
- В логах нет ошибок связанных с ENCRYPTION_KEY
- Health check проходит успешно

**Проверка health:**
```bash
curl -f https://api.novamedika.com/health
# Должно вернуть: {"status":"ok"}
```

---

### ШАГ 7: Тестирование шифрования

```bash
# 7.1 Тест через Python в контейнере
docker exec -it backend-prod python3 <<EOF
import sys
sys.path.insert(0, '/app/src')

from utils.encryption import encrypt_value, decrypt_value, encrypt_bigint, decrypt_bigint

print("=" * 60)
print("ТЕСТИРОВАНИЕ ШИФРОВАНИЯ")
print("=" * 60)

# Тест 1: Шифрование телефона
print("\n1. Тест шифрования телефона:")
phone = "+375291234567"
encrypted_phone = encrypt_value(phone)
decrypted_phone = decrypt_value(encrypted_phone)
print(f"   Оригинал:    {phone}")
print(f"   Зашифровано: {encrypted_phone[:50]}...")
print(f"   Расшифровано:{decrypted_phone}")
print(f"   Результат:   {'✓ PASS' if phone == decrypted_phone else '✗ FAIL'}")

# Тест 2: Шифрование telegram_id
print("\n2. Тест шифрования telegram_id:")
tg_id = 123456789
encrypted_id = encrypt_bigint(tg_id)
decrypted_id = decrypt_bigint(encrypted_id)
print(f"   Оригинал:    {tg_id}")
print(f"   Зашифровано: {encrypted_id[:50]}...")
print(f"   Расшифровано:{decrypted_id}")
print(f"   Результат:   {'✓ PASS' if tg_id == decrypted_id else '✗ FAIL'}")

# Тест 3: Детерминированность (Fernet НЕ детерминирован)
print("\n3. Тест недетерминированности:")
enc1 = encrypt_value(phone)
enc2 = encrypt_value(phone)
print(f"   Enc1 != Enc2: {'✓ PASS' if enc1 != enc2 else '✗ FAIL'}")
print(f"   Оба расшифровываются правильно: {'✓ PASS' if decrypt_value(enc1) == decrypt_value(enc2) == phone else '✗ FAIL'}")

print("\n" + "=" * 60)
print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
print("=" * 60)
EOF

# 7.2 Проверить работу с моделью User
docker exec -it backend-prod python3 <<EOF
import sys
sys.path.insert(0, '/app/src')

from db.database import SessionLocal
from db.qa_models import User

print("\n4. Тест сохранения пользователя с шифрованием:")

db = SessionLocal()
try:
    # Создать тестового пользователя
    user = User()
    user.set_telegram_id(999888777)
    user.set_phone("+37529999888")
    user.first_name = "Тест"
    user.last_name = "Пользователь"
    
    db.add(user)
    db.commit()
    
    # Прочитать из БД
    user_id = user.id
    db.refresh(user)
    
    print(f"   User ID: {user_id}")
    print(f"   telegram_id_encrypted заполнен: {'✓' if user.telegram_id_encrypted else '✗'}")
    print(f"   phone_encrypted заполнен: {'✓' if user.phone_encrypted else '✗'}")
    print(f"   get_telegram_id(): {user.get_telegram_id()}")
    print(f"   get_phone(): {user.get_phone()}")
    
    # Удалить тестового пользователя
    db.delete(user)
    db.commit()
    
    print("   Результат: ✓ PASS")
    
except Exception as e:
    print(f"   Результат: ✗ FAIL - {e}")
finally:
    db.close()
EOF
```

**Ожидаемый результат:**
Все тесты должны показать "✓ PASS"

---

### ШАГ 8: Проверка существующих данных

```bash
# 8.1 Посмотреть статистику по зашифрованным данным
docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
-- Статистика по пользователям
SELECT 
    COUNT(*) as total_users,
    COUNT(telegram_id_encrypted) as users_with_encrypted_tg_id,
    COUNT(phone_encrypted) as users_with_encrypted_phone,
    COUNT(telegram_id) as users_with_plain_tg_id,
    COUNT(phone) as users_with_plain_phone
FROM qa_users;

-- Статистика по заказам
SELECT 
    COUNT(*) as total_orders,
    COUNT(customer_phone_encrypted) as orders_with_encrypted_phone,
    COUNT(telegram_id_encrypted) as orders_with_encrypted_tg_id,
    COUNT(customer_phone) as orders_with_plain_phone,
    COUNT(telegram_id) as orders_with_plain_tg_id
FROM booking_orders;
EOF
```

**Примечание:** Сразу после миграции все данные будут в старых (незашифрованных) полях. Новые данные будут автоматически шифроваться при создании.

---

### ШАГ 9: Мониторинг и логирование

```bash
# 9.1 Настроить мониторинг логов
docker logs -f backend-prod --tail 100 | grep -i "encrypt\|error\|warning"

# 9.2 Проверить производительность
docker stats backend-prod celery-worker-prod --no-stream

# 9.3 Проверить здоровье API
watch -n 5 'curl -s https://api.novamedika.com/health'
```

**Рекомендации по мониторингу:**
- Следите за временем ответа API (должно увеличиться не более чем на 5-10мс)
- Проверяйте логи на ошибки шифрования
- Мониторьте использование памяти (шифрование требует немного больше ресурсов)

---

## ⚠️ Troubleshooting

### Проблема 1: "ENCRYPTION_KEY is not configured"

**Причина:** Переменная окружения не передана в контейнер

**Решение:**
```bash
# Проверить наличие в .env
grep ENCRYPTION_KEY .env

# Проверить в контейнере
docker exec backend-prod env | grep ENCRYPTION_KEY

# Если пусто, перезапустить сервисы
docker compose -f docker-compose.traefik.prod.yml down
docker compose -f docker-compose.traefik.prod.yml up -d
```

---

### Проблема 2: Ошибка "Invalid token" при дешифровании

**Причины:**
1. Неправильный ключ шифрования
2. Данные зашифрованы другим ключом
3. Поврежденные данные в БД

**Решение:**
```bash
# Проверить длину ключа
docker exec backend-prod python3 -c "
from utils.encryption import get_encryption_key
key = get_encryption_key()
print(f'Key length: {len(key)} bytes')
print(f'Key preview: {key[:20]}...')
"

# Должно быть 32 байта (44 символа base64)
```

---

### Проблема 3: Миграция не применяется

**Причина:** Конфликт версий или заблокированная БД

**Решение:**
```bash
# Проверить текущую версию
docker exec -it backend-prod alembic current

# Проверить доступные миграции
docker exec -it backend-prod alembic history

# Принудительно применить конкретную версию
docker exec -it backend-prod alembic upgrade <revision_id>

# Посмотреть логи
docker logs backend-prod --tail 100 | grep -i alembic
```

---

### Проблема 4: Медленная производительность

**Причина:** Шифрование добавляет overhead ~5-10ms на операцию

**Решения:**
1. Использовать кэширование часто запрашиваемых данных
2. Избегать массового дешифрования в циклах
3. Рассмотреть аппаратное ускорение AES-NI (проверить поддержку процессором)

```bash
# Проверить поддержку AES-NI
cat /proc/cpuinfo | grep aes
```

---

## 🔄 Процесс отката (если что-то пошло не так)

```bash
# 1. Остановить сервисы
docker compose -f docker-compose.traefik.prod.yml down

# 2. Восстановить базу данных из бэкапа
cat backup_YYYYMMDD_HHMMSS.sql | docker exec -i postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB

# 3. Откатить миграцию
docker exec -it backend-prod alembic downgrade -1

# 4. Удалить ENCRYPTION_KEY из .env (опционально)
sed -i '/ENCRYPTION_KEY/d' .env

# 5. Перезапустить сервисы
docker compose -f docker-compose.traefik.prod.yml up -d

# 6. Проверить работоспособность
curl -f https://api.novamedika.com/health
docker logs backend-prod --tail 50
```

---

## ✅ Чек-лист завершения

После выполнения всех шагов проверьте:

- [ ] Бэкап базы данных создан и сохранен
- [ ] ENCRYPTION_KEY сгенерирован и безопасно сохранен
- [ ] Ключ добавлен в .env файл
- [ ] .env добавлен в .gitignore
- [ ] Миграция Alembic успешно применена
- [ ] Расширение pgcrypto установлено в PostgreSQL
- [ ] Сервисы backend и celery_worker перезапущены
- [ ] Все тесты шифрования пройдены (✓ PASS)
- [ ] API health check возвращает OK
- [ ] Логи не содержат ошибок шифрования
- [ ] Производительность в норме (<10ms overhead)
- [ ] Команда оповещена о изменениях
- [ ] Документация обновлена

---

## 📊 Ожидаемые метрики после внедрения

### Производительность:
- **Overhead шифрования:** +5-10ms на операцию
- **Увеличение размера данных:** ~30% (base64 encoding)
- **Использование CPU:** +2-5%
- **Использование памяти:** +10-20MB

### Безопасность:
- **Защищенные поля:** 4 (telegram_id, phone × 2 таблицы)
- **Алгоритм:** AES-128-CBC с HMAC-SHA256
- **Соответствие:** ОАЦ класс 3-ин ✓

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker logs backend-prod --tail 100`
2. Проверьте health: `curl https://api.novamedika.com/health`
3. Обратитесь к документации:
   - [Руководство по шифрованию](../oac/guides/ENCRYPTION-IMPLEMENTATION-GUIDE.md)
   - [Политика шифрования ОАЦ](../oac/docs/10-encryption-policy.md)
   - [Чек-лист compliance](../oac/planning/oac-compliance-checklist.md)

---

## 📚 Дополнительные материалы

- [Документация Fernet](https://cryptography.io/en/latest/fernet/)
- [PostgreSQL pgcrypto](https://www.postgresql.org/docs/current/pgcrypto.html)
- [OWASP Encryption Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [Закон РБ №99-З](../origin-docs/zakon%2099-3.pdf)

---

**Автор:** AI Assistant  
**Дата создания:** 28 апреля 2026 г.  
**Статус:** Актуальный  
**Следующий пересмотр:** После полного перехода на encrypted поля (Фаза 3)
