# Инструкция по развертыванию шифрования ПД на Production

**Дата:** 21 апреля 2026 г.  
**Версия:** 1.0  
**Класс ИС:** 3-ин  
**Соответствие:** Закон РБ №99-З, Приказ ОАЦ №66

---

## 📋 Обзор

Данная инструкция описывает пошаговый процесс развертывания шифрования персональных данных (telegram_id, phone) на production сервере NovaMedika2 для соответствия требованиям ОАЦ класса 3-ин.

**Что шифруется:**
- ✅ `telegram_id` - идентификатор пользователя Telegram
- ✅ `phone` / `customer_phone` - номера телефонов

**Что НЕ шифруется:**
- ❌ Имена пользователей
- ❌ Данные аптек и лекарств

---

## ⚠️ ПРЕДУПРЕЖДЕНИЕ: Сделайте Backup!

**ПЕРЕД началом выполнения обязательно создайте резервные копии!**

```bash
# 1. Backup базы данных
docker exec postgres-prod pg_dump -U $POSTGRES_USER $POSTGRES_DB | \
  gzip > /backup/db_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# 2. Backup .env файла
cp .env .env.backup_$(date +%Y%m%d_%H%M%S)

# 3. Проверьте, что backup создан
ls -lh /backup/db_backup_*.sql.gz
ls -lh .env.backup_*
```

---

## 🚀 Пошаговая инструкция

### Шаг 1: Подключение к серверу

```bash
# Подключитесь к серверу по SSH
ssh ваш_пользователь@ваш_сервер

# Перейдите в директорию проекта
cd /путь/к/Novamedika2

# Убедитесь, что вы в правильном каталоге
ls -la docker-compose.traefik.prod.yml
```

---

### Шаг 2: Обновление кода из Git

```bash
# Заберите последние изменения
git pull origin main

# Или если используете другую ветку
git pull origin <ваша_ветка>

# Проверьте, что код обновлен
git log --oneline -5
```

**Ожидаемый результат:** Вы должны увидеть коммит с сообщением "Implement personal data encryption for OAC compliance"

---

### Шаг 3: Генерация ключа шифрования

```bash
# Сгенерируйте криптографически стойкий ключ
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Пример вывода:**
```
gAAAAABlZxK3j8vN2mP4qR5sT6uW7xY8zA9bC0dE1fG2hI3jK4lM5nO6pQ7rS8tU9vW0xY1zA2bC3dE4fG5hI6jK7lM8nO9pQ0rS1tU2vW3xY4zA5bC6dE7fG8hI9jK0lM1nO2pQ3rS4tU5vW6xY7zA8bC9dE0fG1hI2jK3lM4nO5pQ6rS7tU8vW9xY0zA1bC2dE3fG4hI5jK6lM7nO8pQ9rS0tU1vW2xY3zA4bC5dE6fG7hI8jK9lM0nO1pQ2rS3tU4vW5xY6zA7bC8dE9fG0hI1jK2lM3nO4pQ5rS6tU7vW8xY9zA0bC1dE2fG3hI4jK5lM6nO7pQ8rS9tU0vW1xY2zA3bC4dE5fG6hI7jK8lM9nO0pQ1rS2tU3vW4xY5zA6bC7dE8fG9hI0jK1lM2nO3pQ4rS5tU6vW7xY8zA9bC0dE1fG2hI3jK4lM5nO6pQ7rS8tU9vW0xY1zA2bC3dE4fG5hI6jK7lM8nO9pQ0rS1tU2vW3xY4zA5bC6dE7fG8hI9jK0lM1nO2pQ3rS4tU5vW6xY7zA8bC9dE0fG1hI2jK3lM4nO5pQ6rS7tU8vW9xY0zA1bC2dE3fG4hI5jK6lM7nO8pQ9rS0tU1vW2xY3zA4bC5dE6fG7hI8jK9lM0nO1pQ2rS3tU4vW5xY6zA7bC8dE9fG0hI1jK2lM3nO4pQ5rS6tU7vW8xY9zA0bC1dE2fG3hI4jK5lM6nO7pQ8rS9tU0vW1xY2zA3bC4dE5fG6hI7jK8lM9nO0pQ1rS2tU3vW4xY5zA6bC7dE8fG9hI0jK1lM2nO3pQ4rS5tU6vW7xY8zA9bC0dE1fG2hI3jK4lM5nO6pQ7rS8tU9vW0xY1zA2bC3dE4fG5hI6jK7lM8nO9pQ0rS1tU2vW3xY4zA5bC6dE7fG8hI9jK0lM1nO2pQ3rS4tU5vW6xY7zA8bC9dE0fG1hI2jK3lM4nO5pQ6rS7tU8vW9xY0zA1bC2dE3fG4hI5jK6lM7nO8pQ9rS0tU1vW2xY3zA4bC5dE6fG7hI8jK9lM0nO1pQ2rS3tU4vW5xY6zA7bC8dE9fG0hI1jK2lM3nO4pQ5rS6tU7vW8xY9zA0bC1dE2fG3hI4jK5lM6nO7pQ8rS9tU0vW1xY2zA3bC4dE5fG6hI7jK8lM9nO0pQ1rS2tU3vW4xY5zA6bC7dE8fG9hI0jK1lM2nO3pQ4rS5tU6vW7xY8zA9bC0d......
```

**⚠️ ВАЖНО:** Скопируйте этот ключ! Он понадобится на следующем шаге.

---

### Шаг 4: Настройка .env файла

```bash
# Откройте .env файл для редактирования
nano .env
# или
vim .env
```

Добавьте сгенерированный ключ в конец файла:

```bash
# Добавьте эту строку (замените YOUR_GENERATED_KEY на реальный ключ)
ENCRYPTION_KEY=ваш_сгенерированный_ключ_из_шага_3
```

**Пример содержимого .env:**
```bash
# ... существующие переменные ...
POSTGRES_USER=novamedika
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=novamedika_prod
DATABASE_URL=postgresql+asyncpg://novamedika:your_secure_password@postgres:5432/novamedika_prod
SECRET_KEY=your_secret_key
TELEGRAM_BOT_TOKEN=your_bot_token
REDIS_PASSWORD=your_redis_password

# Ключ шифрования для персональных данных (ОАЦ compliance)
ENCRYPTION_KEY=gAAAAABlZxK3j8vN2mP4qR5sT6uW7xY8zA9bC0dE1fG2hI3jK4lM5nO6pQ7rS8tU9vW0xY1zA2bC3dE4fG5hI6jK7lM8nO9pQ0rS1tU2vW3xY4zA5bC6dE7fG8hI9jK0lM1nO2pQ3rS4tU5vW6xY7zA8bC9dE0fG1hI2jK3lM4nO5pQ6rS7tU8vW9xY0zA1bC2dE3fG4hI5jK6lM7nO8pQ9rS0tU1vW2xY3zA4bC5dE6fG7hI8jK9lM0nO1pQ2rS3tU4vW5xY6zA7bC8dE9fG0hI1jK2lM3nO4pQ5rS6tU7vW8xY9zA0bC1dE2fG3hI4jK5lM6nO7pQ8rS9tU0vW1xY2zA3bC4dE5fG6hI7jK8lM9nO0pQ1rS2tU3vW4xY5zA6bC7dE8fG9hI0jK1lM2nO3pQ4rS5tU6vW7xY8zA9bC0dE1fG2hI3jK4lM5nO6pQ7rS8tU9vW0xY1zA2bC3dE4fG5hI6jK7lM8nO9pQ0rS1tU2vW3xY4zA5bC6dE7fG8hI9jK0lM1nO2pQ3rS4tU5vW6xY7zA8bC9dE0fG1hI2jK3lM4nO5pQ6rS7tU8vW9xY0zA1bC2dE3fG4hI5jK6lM7nO8pQ9rS0tU1vW2xY3zA4bC5dE6fG7hI8jK9lM0nO1pQ2rS3tU4vW5xY6zA7bC8dE9fG0hI1jK2lM3nO4pQ5rS6tU7vW8xY9zA0bC1dE2fG3hI4jK5lM6nO7pQ8rS9tU0vW1xY2zA3bC4dE5fG6hI7jK8lM9nO0pQ1rS2tU3vW4xY5zA6bC7dE8fG9hI0jK1lM2nO3pQ4rS5tU6vW7xY8zA9bC0dE1fG2hI3jK4lM5nO6pQ7rS8tU9vW0xY1zA2bC3dE4fG5hI6jK7lM8nO9pQ0rS1tU2vW3xY4zA5bC6dE7fG8hI9jK0lM1nO2pQ3rS4tU5vW6xY7zA8bC9dE0fG1hI2jK3lM4nO5pQ6rS7tU8vW9xY0zA1bC2dE3fG4hI5jK6lM7nO8pQ9rS0tU1vW2xY3zA4bC5dE6fG7hI8jK9lM0nO1pQ2rS3tU4vW5xY6zA7bC8dE9fG0hI1jK2lM3nO4pQ5rS6tU7vW8xY9zA0bC1dE2fG3hI4jK5lM6nO7pQ8rS9tU0vW1xY2zA3bC4dE5fG6hI7jK8lM9nO0pQ1rS2tU3vW4xY5zA6bC7dE8fG9hI0jK1lM2nO3pQ4rS5tU6vW7xY8zA9bC0d......

# Domain
DOMAIN=spravka.novamedika.com
VITE_API_URL=https://api.spravka.novamedika.com
CORS_ORIGINS=https://spravka.novamedika.com,https://www.spravka.novamedika.com
```

Сохраните файл:
- **nano:** Ctrl+X, затем Y, затем Enter
- **vim:** Esc, затем `:wq`, затем Enter

---

### Шаг 5: Пересборка и перезапуск контейнеров

#### Вариант A: Полная пересборка (рекомендуется)

```bash
# Остановите текущие контейнеры
npm run prod:down

# Пересоберите образы без кэша
docker-compose -f docker-compose.traefik.prod.yml build --no-cache

# Запустите сервисы
npm run prod:up
```

#### Вариант B: Быстрый перезапуск (если код уже обновлен)

```bash
# Просто перезапустите backend
npm run prod:restart-backend
```

**Проверьте статус контейнеров:**
```bash
docker ps

# Должны быть запущены:
# - backend-prod
# - frontend-prod
# - postgres-prod
# - redis-prod
# - traefik
```

---

### Шаг 6: Применение миграции базы данных

```bash
# Примените миграцию Alembic
docker exec -it backend-prod alembic upgrade head
```

**Ожидаемый вывод:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade m3n4o5p6q7r8 -> 3b81fefeff37, add_encrypted_fields_for_personal_data
```

**Проверьте текущую версию миграций:**
```bash
docker exec -it backend-prod alembic current
```

**Ожидаемый вывод:**
```
3b81fefeff37 (head)
```

---

### Шаг 7: Настройка pgcrypto в PostgreSQL

```bash
# Загрузите переменные окружения
source .env

# Выполните SQL скрипт настройки
docker exec -i postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
-- Установить расширение pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Настроить ключ шифрования
ALTER SYSTEM SET app.encryption_key = '$ENCRYPTION_KEY';

-- Проверить установку расширения
SELECT extname, extversion FROM pg_extension WHERE extname = 'pgcrypto';
EOF
```

**Ожидаемый вывод:**
```
CREATE EXTENSION
ALTER SYSTEM
   extname   | extversion 
-------------+------------
 pgcrypto    | 1.3
(1 row)
```

**Перезапустите PostgreSQL для применения настроек:**
```bash
docker restart postgres-prod

# Подождите 10-15 секунд пока PostgreSQL перезагрузится
sleep 15

# Проверьте, что PostgreSQL запустился
docker ps | grep postgres-prod
```

---

### Шаг 8: Проверка работоспособности

#### 8.1. Проверка health endpoint

```bash
curl https://api.spravka.novamedika.com/health
```

**Ожидаемый ответ:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-21T..."
}
```

#### 8.2. Проверка логов backend

```bash
# Просмотр последних 100 строк логов
docker logs --tail=100 backend-prod

# Поиск ошибок
docker logs backend-prod 2>&1 | grep -i "error\|exception\|traceback"
```

**Не должно быть ошибок, связанных с ENCRYPTION_KEY!**

#### 8.3. Проверка环境变量

```bash
# Убедитесь, что ключ передан в контейнер
docker exec backend-prod env | grep ENCRYPTION_KEY
```

**Ожидаемый вывод:**
```
ENCRYPTION_KEY=gAAAAABlZxK3j8v...
```

---

### Шаг 9: Тестирование шифрования

#### 9.1. Проверка зашифрованных данных в БД

```bash
# Подключитесь к БД
docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB

-- Проверьте количество зашифрованных записей
SELECT 
    COUNT(*) as total_users,
    COUNT(telegram_id_encrypted) as encrypted_telegram_ids,
    COUNT(phone_encrypted) as encrypted_phones
FROM qa_users;

-- Проверьте заказы
SELECT 
    COUNT(*) as total_orders,
    COUNT(customer_phone_encrypted) as encrypted_phones,
    COUNT(telegram_id_encrypted) as encrypted_telegram_ids
FROM booking_orders;

-- Выйдите из psql
\q
```

**Ожидаемый результат:** Количество зашифрованных записей должно совпадать с общим количеством (или быть 0, если нет данных).

#### 9.2. Функциональное тестирование

1. **Откройте Telegram бота** @Novamedika_bot
2. **Отправьте команду** `/start`
3. **Зарегистрируйтесь** или войдите в систему
4. **Создайте тестовый заказ**
5. **Проверьте**, что заказ создался успешно

**Проверьте логи на ошибки:**
```bash
docker logs -f backend-prod 2>&1 | grep -i "error\|exception"
```

---

### Шаг 10: Мониторинг после развертывания

В течение первых 24 часов после обновления внимательно следите за системой:

```bash
# Логи в реальном времени
docker logs -f --tail=50 backend-prod

# Использование ресурсов
docker stats backend-prod postgres-prod

# Статус всех контейнеров
watch -n 5 'docker ps'
```

**На что обращать внимание:**
- ❌ Ошибки шифрования/дешифрования
- ❌ Проблемы с подключением к БД
- ❌ Высокая нагрузка на CPU (>80%)
- ❌ Увеличение времени ответа API

---

## 🔧 Troubleshooting

### Проблема 1: "ENCRYPTION_KEY is not configured"

**Симптомы:**
```
RuntimeError: ENCRYPTION_KEY is not configured
```

**Решение:**
```bash
# 1. Проверьте, что ключ есть в .env
grep ENCRYPTION_KEY .env

# 2. Если отсутствует, добавьте ключ
echo "ENCRYPTION_KEY=ваш_ключ" >> .env

# 3. Перезапустите backend
docker restart backend-prod

# 4. Проверьте
docker exec backend-prod env | grep ENCRYPTION_KEY
```

---

### Проблема 2: Ошибка миграции Alembic

**Симптомы:**
```
alembic.util.exc.CommandError: Can't locate revision identified by '...'
```

**Решение:**
```bash
# 1. Проверьте текущую версию
docker exec -it backend-prod alembic current

# 2. Если версия неверная, откатите и примените заново
docker exec -it backend-prod alembic downgrade base
docker exec -it backend-prod alembic upgrade head

# 3. Проверьте статус
docker exec -it backend-prod alembic current
```

---

### Проблема 3: Ошибка дешифрования "Invalid token"

**Симптомы:**
```
cryptography.fernet.InvalidToken: Invalid token
```

**Причины:**
1. Неправильный ENCRYPTION_KEY
2. Данные были зашифрованы другим ключом
3. Поврежденные данные в БД

**Решение:**
```bash
# 1. Проверьте ключ в .env и в PostgreSQL
source .env
docker exec -i postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SHOW app.encryption_key;"

# 2. Убедитесь, что ключи совпадают
echo "ENV key: $ENCRYPTION_KEY"

# 3. Если не совпадают, обновите в PostgreSQL
docker exec -i postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
ALTER SYSTEM SET app.encryption_key = '$ENCRYPTION_KEY';
EOF

# 4. Перезапустите PostgreSQL
docker restart postgres-prod
sleep 15
```

---

### Проблема 4: PostgreSQL не запускается после ALTER SYSTEM

**Симптомы:**
```
postgres-prod exited with code 1
```

**Решение:**
```bash
# 1. Проверьте логи PostgreSQL
docker logs postgres-prod

# 2. Если ошибка в конфигурации, сбросьте настройки
docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
ALTER SYSTEM RESET app.encryption_key;
EOF

# 3. Перезапустите
docker restart postgres-prod
sleep 15

# 4. Настройте ключ заново через .env и docker-compose
```

---

### Проблема 5: Медленная производительность после шифрования

**Симптомы:**
- Время ответа API увеличилось на >50%
- Высокая нагрузка на CPU

**Решение:**
```bash
# 1. Проверьте нагрузку
docker stats backend-prod

# 2. Оптимизируйте запросы (добавьте индексы)
docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
-- Проверьте наличие индексов
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename IN ('qa_users', 'booking_orders')
AND indexname LIKE '%encrypted%';
EOF

# 3. Если индексы отсутствуют, создайте их
docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
CREATE INDEX IF NOT EXISTS idx_qa_users_telegram_id_encrypted ON qa_users(telegram_id_encrypted);
CREATE INDEX IF NOT EXISTS idx_booking_orders_telegram_id_encrypted ON booking_orders(telegram_id_encrypted);
EOF
```

---

## 🔄 Откат изменений (Emergency Rollback)

Если что-то пошло не так и нужно срочно откатить изменения:

### Шаг 1: Откат миграции

```bash
docker exec -it backend-prod alembic downgrade -1
```

### Шаг 2: Восстановление БД из backup

```bash
# Найдите последний backup
ls -lt /backup/db_backup_*.sql.gz | head -1

# Восстановите (замените filename на реальный файл)
gunzip < /backup/db_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB
```

### Шаг 3: Восстановление .env

```bash
# Найдите backup .env
ls -lt .env.backup_* | head -1

# Восстановите (замените filename на реальный файл)
cp .env.backup_YYYYMMDD_HHMMSS .env
```

### Шаг 4: Перезапуск сервисов

```bash
npm run prod:restart
```

---

## ✅ Чек-лист успешного развертывания

Пройдитесь по чек-листу после завершения всех шагов:

- [ ] **Backup создан** (БД + .env)
- [ ] **Код обновлен** через git pull
- [ ] **ENCRYPTION_KEY сгенерирован** и добавлен в .env
- [ ] **Контейнеры пересобраны** и запущены
- [ ] **Миграция Alembic применена** успешно
- [ ] **Расширение pgcrypto установлено** в PostgreSQL
- [ ] **Ключ настроен** через ALTER SYSTEM
- [ ] **PostgreSQL перезапущен** и работает
- [ ] **Health check проходит** (HTTP 200)
- [ ] **Нет ошибок в логах** backend
- [ ] **Переменная ENCRYPTION_KEY доступна** в контейнере
- [ ] **Данные шифруются** корректно (проверено в БД)
- [ ] **Bot работает** нормально (тестовый заказ создан)
- [ ] **Мониторинг настроен** (логи, ресурсы)

---

## 📊 Метрики успеха

После успешного развертывания вы должны наблюдать:

1. **Время ответа API:** < 500ms (увеличение не более 10-20%)
2. **CPU usage backend:** < 60%
3. **Memory usage backend:** < 800MB
4. **Ошибка шифрования:** 0 в логах
5. **Успешных заказов:** 100% (нет потерь данных)

---

## 📞 Поддержка

Если возникли проблемы, которые не удалось решить через troubleshooting:

1. **Проверьте документацию:**
   - [ENCRYPTION-IMPLEMENTATION-GUIDE.md](../ENCRYPTION-IMPLEMENTATION-GUIDE.md)
   - [oac/docs/10-encryption-policy.md](../oac/docs/10-encryption-policy.md)

2. **Соберите информацию для диагностики:**
   ```bash
   # Версия миграций
   docker exec -it backend-prod alembic current
   
   # Логи backend (последние 200 строк)
   docker logs --tail=200 backend-prod > backend_logs.txt
   
   # Логи PostgreSQL
   docker logs --tail=100 postgres-prod > postgres_logs.txt
   
   # Статус контейнеров
   docker ps -a > containers_status.txt
   
   # Переменные окружения backend
   docker exec backend-prod env > backend_env.txt
   ```

3. **Предоставьте логи** для анализа

---

## 📚 Дополнительные ресурсы

- [Полное руководство по шифрованию](../ENCRYPTION-IMPLEMENTATION-GUIDE.md)
- [Политика шифрования ОАЦ](../oac/docs/10-encryption-policy.md)
- [Статус compliance](../OAC-COMPLIANCE-STATUS-REPORT.md)
- [Документация Fernet](https://cryptography.io/en/latest/fernet/)
- [PostgreSQL pgcrypto](https://www.postgresql.org/docs/current/pgcrypto.html)

---

## 🎯 Следующие шаги после успешного развертывания

1. **Обновите код приложения** для использования новых методов шифрования:
   - Замените прямое присваивание `user.telegram_id = ...` на `user.set_telegram_id(...)`
   - Замените чтение `user.telegram_id` на `user.get_telegram_id()`

2. **Настройте централизованное логирование** (следующий критический пункт ОАЦ)

3. **Проведите pentest** (тестирование на проникновение)

4. **Подготовьте документы для аттестации:**
   - Руководство администратора СЗИ
   - Руководство пользователя СЗИ
   - Программа и методика испытаний (ПМИ)

---

**Инструкция создана:** 21 апреля 2026 г.  
**Версия:** 1.0  
**Статус:** Актуальная  
**Автор:** AI Assistant  
**Для проекта:** NovaMedika2 (класс 3-ин)
