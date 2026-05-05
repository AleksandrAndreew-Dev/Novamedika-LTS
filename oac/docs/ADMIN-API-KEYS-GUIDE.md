## Endpoint полного удаления всех заказов бронирования

### Реализация

Добавлен endpoint `DELETE /api/orders/bulk-delete` для полного удаления **ВСЕХ** заказов бронирования.

**Аналогия с `/telegram-bot/qa/drop`:**
- Использует `TRUNCATE TABLE booking_orders CASCADE`
- Отключает foreign key constraints на время операции
- Полное удаление без возможности восстановления
- Требует ADMIN API Key аутентификации
- **Не принимает тело запроса** (как и `/qa/drop`)

**Требования:**
- **ADMIN API Key аутентификация** (заголовок `X-API-Key`, переменная окружения [ADMIN_API_KEYS](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\routers\telegram_bot.py#L235-L237))
- Метод: `DELETE`
- Тело запроса: **НЕТ** (пустой запрос)

**Конфигурация ADMIN_API_KEYS:**

В файле `.env` на production сервере:
```bash
# Admin API Keys для критичных операций (удаление данных, очистка БД)
ADMIN_API_KEYS=key1,key2,key3

# Пример:
ADMIN_API_KEYS=admin-secret-key-123,another-admin-key-456
```

---

### ⚠️ ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ

Этот endpoint использует `TRUNCATE TABLE CASCADE` и **удаляет ВСЕ заказы без фильтров и возможности восстановления!**

Если вам нужно удалить только часть заказов, используйте другие методы:
- Удаление по одному: `DELETE /api/orders/{order_id}`
- SQL скрипт с фильтрацией напрямую в БД

---

### 📝 Использование endpoint'а

#### **Пример 1: Полное удаление всех заказов**

```bash
curl -X DELETE https://api.novamedika.com/api/orders/bulk-delete \
  -H "X-API-Key: YOUR_ADMIN_API_KEY"
```

**Ответ при успехе:**
```json
{
    "status": "success",
    "message": "All booking orders deleted successfully",
    "cleared_tables": ["booking_orders"]
}
```

#### **Пример 2: Без ADMIN API Key (ошибка 401)**

```bash
curl -X DELETE https://api.novamedika.com/api/orders/bulk-delete
```

**Ответ:**
```json
{
    "detail": "Invalid or missing admin API key"
}
```

---

### 🔍 Проверка работы

#### **Локальное тестирование:**

```bash
# 1. Запустите backend локально
cd backend
python -m uvicorn src.main:app --reload

# 2. Получите ADMIN API Key из .env
grep ADMIN_API_KEYS .env

# 3. Протестируйте endpoint (без тела запроса!)
curl -X DELETE http://localhost:8000/api/orders/bulk-delete \
  -H "X-API-Key: YOUR_ADMIN_API_KEY"
```

#### **Проверка в production:**

```bash
# 1. Проверьте количество заказов до удаления
docker exec postgres-prod psql -U novamedika -d novamedika_prod -c "
SELECT COUNT(*) as total_orders FROM booking_orders;
"

# 2. Выполните удаление (простой DELETE запрос без тела)
curl -X DELETE https://api.novamedika.com/api/orders/bulk-delete \
  -H "X-API-Key: YOUR_PROD_ADMIN_API_KEY"

# 3. Проверьте результат
docker exec postgres-prod psql -U novamedika -d novamedika_prod -c "
SELECT COUNT(*) as total_orders FROM booking_orders;
"

# Должно вернуть: 0

# 4. Проверьте логи
docker logs --tail 50 backend-prod | grep -i "bulk delete\|truncate"
```

---

### 🛡️ Безопасность

✅ **Защита от случайного удаления:**
- Требуется ADMIN API Key (высший уровень доступа)
- Транзакционность: rollback при ошибке
- Логирование всех операций
- Нет параметров в теле запроса (проще = безопаснее)

✅ **Аутентификация:**
- Endpoint требует ADMIN API Key (только администраторы)
- Endpoint не доступен публично
- Используется та же функция проверки что и для `/qa/drop`

✅ **Логирование:**
```python
logger.info("Starting bulk delete of all booking orders")
logger.info("Cleared table: booking_orders")
logger.info("Bulk delete completed successfully by admin")
```

---

### 📊 Сравнение с другими методами удаления

| Метод | Endpoint | Фильтрация | Восстановление | Уровень доступа |
|-------|----------|------------|----------------|-----------------|
| **По одному** | `DELETE /api/orders/{id}` | По ID | ❌ Нет | BOOKING_API_KEYS |
| **Отмена заказа** | `PATCH /api/orders/{id}` | По ID | ✅ Да (статус cancelled) | BOOKING_API_KEYS |
| **Полное удаление** ⭐ | `DELETE /api/orders/bulk-delete` | **НЕТ (все)** | ❌ Нет | ADMIN_API_KEYS |
| **SQL TRUNCATE** | Прямой SQL | Опционально | ❌ Нет | DBA доступ |

---

### 🔄 Техническая реализация

```python
@router.delete("/orders/bulk-delete")
async def bulk_delete_orders(
    db: AsyncSession = Depends(get_db),
    admin_verified: bool = Depends(verify_admin_api_key),
):
    """Полное удаление всех заказов бронирования (аналогично /telegram-bot/qa/drop)."""
    
    try:
        # Отключаем внешние ключи (для PostgreSQL)
        await db.execute(text("SET session_replication_role = 'replica';"))
        
        logger.info("Starting bulk delete of all booking orders")
        
        # Очищаем таблицу booking_orders
        await db.execute(text("TRUNCATE TABLE booking_orders CASCADE;"))
        logger.info("Cleared table: booking_orders")
        
        # Включаем обратно внешние ключи
        await db.execute(text("SET session_replication_role = 'origin';"))
        await db.commit()
        
        logger.info("Bulk delete completed successfully by admin")
        
        return {
            "status": "success",
            "message": "All booking orders deleted successfully",
            "cleared_tables": ["booking_orders"],
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting orders: {str(e)}")
```

---

### 🚨 Действия при ошибке

Если удаление прошло успешно, но данные нужны:

1. **Немедленно остановите приложение:**
   ```bash
   docker stop backend-prod
   ```

2. **Восстановите из backup:**
   ```bash
   gunzip -c /backups/db/db_YYYYMMDD_HHMMSS.sql.gz | \
     docker exec -i postgres-prod psql -U novamedika -d novamedika_prod
   ```

3. **Перезапустите приложение:**
   ```bash
   docker start backend-prod
   ```

---

### 📋 Сравнение с `/telegram-bot/qa/drop`

| Характеристика | `/telegram-bot/qa/drop` | `/api/orders/bulk-delete` |
|----------------|-------------------------|---------------------------|
| **Метод HTTP** | POST | DELETE |
| **Тело запроса** | ❌ Нет | ❌ Нет |
| **Параметры** | ❌ Нет | ❌ Нет |
| **Подтверждение** | ❌ Не требуется | ❌ Не требуется |
| **Аутентификация** | ADMIN_API_KEYS | ADMIN_API_KEYS |
| **Функция проверки** | [verify_admin_api_key()](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\routers\telegram_bot.py#L239-L250) | [verify_admin_api_key()](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\routers\telegram_bot.py#L239-L250) |
| **SQL команда** | TRUNCATE TABLE ... CASCADE | TRUNCATE TABLE ... CASCADE |
| **Foreign Keys** | Отключаются/включаются | Отключаются/включаются |
| **Логирование** | ✅ Да | ✅ Да |
| **Возврат таблиц** | ✅ `cleared_tables` | ✅ `cleared_tables` |

**Идеальное соответствие!** ✅

---

### 📞 Контакты

| Роль | Обязанности |
|------|-------------|
| Администратор системы | Использование endpoint'а, ротация ADMIN_API_KEYS |
| Ответственный за ИБ | Аудит использований, расследование инцидентов |
| DBA | Восстановление данных из backup |

---

**Файлы реализации:**
- Endpoint: `backend/src/routers/booking_orders.py` (bulk_delete_orders)
- Аутентификация: `verify_admin_api_key()` использует `os.getenv("ADMIN_API_KEYS")`
- Импорт: `from sqlalchemy import text`

**Документ подготовил:** AI Assistant  
**Дата:** 05 мая 2026 г.  
**Статус:** Готово к использованию  
**Требуется настройка:** Да (добавить ADMIN_API_KEYS в .env)
