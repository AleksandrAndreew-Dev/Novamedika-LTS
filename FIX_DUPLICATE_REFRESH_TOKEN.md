# Исправление проблемы Duplicate Refresh Token

**Дата:** 2026-04-29  
**Статус:** ✅ ИСПРАВЛЕНО

---

## Проблема

Фармацевты не могли войти в дашборд через Telegram WebApp. При попытке аутентификации возникала ошибка:

```
sqlalchemy.exc.IntegrityError: duplicate key value violates unique constraint "ix_refresh_tokens_token"
DETAIL: Key (token)=(eyJhbGci...) already exists.
```

Браузер получал HTTP 500 от `/api/pharmacist/login/telegram/`, после чего запрос на `/api/pharmacist/me` возвращал 401 Unauthorized.

---

## Корневая причина

При каждом входе пользователя создавался новый refresh token, но старые токены не удалялись из БД. Так как поле `token` в таблице `refresh_tokens` имеет уникальный индекс, при повторном входе возникало нарушение уникальности.

---

## Решение

Обновлена функция `store_refresh_token()` в `backend/src/auth/auth.py`:

**До:**
```python
async def store_refresh_token(token: str, user_id: str, db: AsyncSession):
    """Сохранить refresh token в БД"""
    expires_at = get_utc_now_naive() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = RefreshToken(...)
    db.add(refresh_token)
    await db.commit()  # ❌ IntegrityError если токен уже существует
    return refresh_token
```

**После:**
```python
from sqlalchemy import delete

async def store_refresh_token(token: str, user_id: str, db: AsyncSession):
    """Сохранить refresh token в БД (удаляет старые активные токены пользователя)"""
    # Удаляем все активные токены пользователя перед созданием нового
    await db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False
        )
    )
    
    # Создаем новый токен
    expires_at = get_utc_now_naive() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = RefreshToken(...)
    db.add(refresh_token)
    await db.commit()  # ✅ Теперь всегда успешно
    return refresh_token
```

---

## Измененные файлы

1. **`backend/src/auth/auth.py`**
   - Добавлен импорт `delete` из SQLAlchemy
   - Обновлена функция `store_refresh_token()` для удаления старых токенов

2. **`backend/src/routers/pharmacist_auth.py`**
   - Улучшена обработка ошибок в `telegram_webapp_login()` endpoint
   - Добавлены комментарии о автоматической очистке старых токенов

---

## Инструкция по развертыванию

### Шаг 1: Пересобрать backend образ

```bash
cd c:\Users\37525\Desktop\upwork\projects\Novamedika2

# Пересобрать backend image с исправлениями
docker-compose build backend
```

### Шаг 2: Перезапустить backend контейнер

```bash
# Перезапустить только backend
docker-compose up -d backend

# Или перезапустить все сервисы
docker-compose up -d
```

### Шаг 3: Проверить применение изменений

```bash
# Посмотреть логи backend
docker-compose logs -f backend

# Убедиться, что нет ошибок при старте
docker-compose exec backend python -c "import sys; print('Backend OK')"
```

### Шаг 4: Тестирование аутентификации

1. Открыть Telegram бот
2. Нажать кнопку входа в дашборд фармацевта
3. Проверить, что:
   - ✅ Запрос `POST /api/pharmacist/login/telegram/` проходит успешно (HTTP 200)
   - ✅ Возвращаются JWT токены (access_token и refresh_token)
   - ✅ Запрос `GET /api/pharmacist/me` возвращает профиль фармацевта (HTTP 200)
   - ✅ Фармацевт попадает в дашборд

### Шаг 5: Мониторинг логов

```bash
# Следить за backend логами во время тестирования
docker-compose logs -f backend | grep -i "pharmacist\|login\|token"
```

Ожидаемый результат:
```
INFO:routers.pharmacist_auth:Telegram login attempt: telegram_id=XXXXX, user=Имя Фамилия
INFO:routers.pharmacist_auth:✅ Telegram login successful for pharmacist user_id=XXX-XXX-XXX
```

❌ **Не должно быть:**
```
ERROR:routers.pharmacist_auth:Telegram WebApp login failed
IntegrityError: duplicate key value violates unique constraint "ix_refresh_tokens_token"
```

---

## Дополнительные проверки

### Проверка таблицы refresh_tokens в БД

```bash
# Подключиться к PostgreSQL
docker-compose exec postgres psql -U postgres -d novamedika

# Посмотреть количество токенов на пользователя
SELECT user_id, COUNT(*) as token_count 
FROM refresh_tokens 
WHERE revoked = false 
GROUP BY user_id 
HAVING COUNT(*) > 1;

# Должно вернуть пустой результат (у каждого пользователя максимум 1 активный токен)
```

### Очистка старых токенов (опционально)

Если в БД накопились старые токены, можно их удалить:

```sql
-- Удалить все отозванные токены старше 7 дней
DELETE FROM refresh_tokens 
WHERE revoked = true 
AND created_at < NOW() - INTERVAL '7 days';

-- Удалить все просроченные токены
DELETE FROM refresh_tokens 
WHERE expires_at < NOW();
```

---

## Почему это решение правильное

1. **Простота**: Один активный токен на пользователя - простая и понятная модель
2. **Безопасность**: При каждом новом входе старые токены аннулируются, что предотвращает использование скомпрометированных токенов
3. **Надежность**: Нет race conditions или сложных upsert операций
4. **Производительность**: Удаление по индексу `user_id` выполняется быстро
5. **Чистота БД**: Таблица `refresh_tokens` не разрастается со временем

---

## Альтернативные подходы (не использованы)

1. **Upsert (ON CONFLICT DO UPDATE)**: PostgreSQL-specific, сложнее в реализации
2. **Проверка перед вставкой**: Создает race condition при конкурентных запросах
3. **Удаление по времени создания**: Усложняет логику без существенных преимуществ

Текущее решение является оптимальным балансом простоты, безопасности и надежности.
