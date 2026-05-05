# Руководство по использованию ADMIN API Keys

## 📋 Обзор

ADMIN API Keys используются для защиты критичных административных операций в системе NovaMedika2.

**Дата создания:** 05 мая 2026 г.  
**Класс ИС:** 3-ин (согласно требованиям ОАЦ)

---

## 🔑 Конфигурация ADMIN_API_KEYS

### На production сервере

В файле `.env` добавьте переменную:

```bash
# Admin API Keys для критичных операций
# Разделяйте ключи запятыми без пробелов
ADMIN_API_KEYS=key1,key2,key3

# Пример с реальными ключами:
ADMIN_API_KEYS=admin-prod-secret-key-abc123,admin-backup-key-def456
```

### Генерация безопасных ключей

```bash
# Сгенерировать случайный ключ (32 символа)
openssl rand -base64 32

# Или через Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Рекомендации:**
- Минимальная длина ключа: 32 символа
- Используйте разные ключи для разных сред (dev/staging/prod)
- Ротируйте ключи каждые 90 дней
- Храните ключи в защищенном менеджере паролей

---

## 🛡️ Защищенные endpoint'ы

### 1. **Массовое удаление заказов**
`DELETE /api/orders/bulk-delete`

**Использование:**
```bash
curl -X DELETE https://api.novamedika.com/api/orders/bulk-delete \
  -H "X-API-Key: YOUR_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "confirm": true,
    "status": "cancelled",
    "reason": "Очистка старых заказов"
  }'
```

### 2. **Очистка базы QA**
`POST /telegram-bot/qa/drop`

**Использование:**
```bash
curl -X POST https://api.novamedika.com/telegram-bot/qa/drop \
  -H "X-API-Key: YOUR_ADMIN_API_KEY"
```

### 3. **Статистика QA**
`GET /telegram-bot/qa/stats`

**Использование:**
```bash
curl -X GET https://api.novamedika.com/telegram-bot/qa/stats \
  -H "X-API-Key: YOUR_ADMIN_API_KEY"
```

### 4. **Сброс статуса фармацевтов**
`POST /telegram-bot/qa/reset-pharmacists-status`

**Использование:**
```bash
curl -X POST https://api.novamedika.com/telegram-bot/qa/reset-pharmacists-status \
  -H "X-API-Key: YOUR_ADMIN_API_KEY"
```

### 5. **Получение pending вопросов**
`GET /telegram-bot/qa/questions/pending`

**Использование:**
```bash
curl -X GET https://api.novamedika.com/telegram-bot/qa/questions/pending \
  -H "X-API-Key: YOUR_ADMIN_API_KEY"
```

---

## 🔍 Проверка работы

### 1. Проверка конфигурации

```bash
# На production сервере
cd /opt/novamedika-prod

# Проверить наличие ADMIN_API_KEYS в .env
grep ADMIN_API_KEYS .env

# Должно вывести:
# ADMIN_API_KEYS=key1,key2,...
```

### 2. Тестирование endpoint

```bash
# Получить список ключей из БД (если есть доступ)
docker exec postgres-prod psql -U novamedika -d novamedika_prod -c "
SELECT COUNT(*) FROM pharmacy_api_configs WHERE is_active = true;
"

# Протестировать endpoint массового удаления
curl -X DELETE http://localhost:8000/api/orders/bulk-delete \
  -H "X-API-Key: test-key" \
  -H "Content-Type: application/json" \
  -d '{
    "confirm": true,
    "status": "cancelled"
  }'

# Ожидаемый ответ при неверном ключе:
# {"detail":"Invalid or missing admin API key"}
```

### 3. Проверка логов

```bash
# Следить за логами backend
docker logs -f backend-prod | grep -i "admin\|bulk delete"

# При успешном удалении должно быть:
# INFO:routers.booking_orders:Bulk deleted X orders by admin. Filters: ...
```

---

## ⚠️ Безопасность

### Требования к ADMIN_API_KEYS:

1. **Минимум один ключ должен быть настроен**
   - Если `ADMIN_API_KEYS` пустой, все admin endpoints будут заблокированы
   - В логах появится: `CRITICAL:ADMIN_API_KEYS not configured — admin endpoints blocked`

2. **Разделение уровней доступа**
   - `BOOKING_API_KEYS` — для обычных операций (создание заказов)
   - `ADMIN_API_KEYS` — для критичных операций (удаление данных)

3. **Ротация ключей**
   ```bash
   # 1. Сгенерировать новый ключ
   NEW_KEY=$(openssl rand -base64 32)
   
   # 2. Обновить .env
   sed -i "s/ADMIN_API_KEYS=.*/ADMIN_API_KEYS=$NEW_KEY/" .env
   
   # 3. Перезапустить backend
   docker restart backend-prod
   
   # 4. Уведомить всех администраторов о новом ключе
   ```

4. **Мониторинг использования**
   ```bash
   # Посмотреть количество использований admin endpoints
   docker logs backend-prod | grep "Bulk deleted" | wc -l
   
   # Проверить неудачные попытки аутентификации
   docker logs backend-prod | grep "Invalid or missing admin API key" | wc -l
   ```

---

## 🚨 Действия при компрометации ключа

Если ADMIN API Key был скомпрометирован:

### Шаг 1: Немедленная ротация

```bash
# 1. Сгенерировать новые ключи
NEW_KEYS=$(openssl rand -base64 32)

# 2. Обновить .env
echo "ADMIN_API_KEYS=$NEW_KEYS" > .env.new
mv .env.new .env
chmod 600 .env

# 3. Перезапустить backend
docker restart backend-prod
```

### Шаг 2: Аудит действий

```bash
# Проверить все действия скомпрометированного ключа
docker logs backend-prod | grep "by admin" | grep -A 5 -B 5 "COMPROMISED_KEY"

# Проверить массовые удаления
docker logs backend-prod | grep "Bulk deleted"
```

### Шаг 3: Восстановление данных (если нужно)

```bash
# Восстановить из backup
gunzip -c /backups/db/db_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i postgres-prod psql -U novamedika -d novamedika_prod
```

---

## 📊 Сравнение уровней доступа

| Уровень | Переменная | Endpoint'ы | Использование |
|---------|-----------|------------|---------------|
| **Public** | Нет | `/api/search`, `/api/orders` (POST) | Публичный доступ |
| **User** | JWT Token | `/api/users/me`, `/api/privacy/*` | Авторизованные пользователи |
| **Pharmacy** | `BOOKING_API_KEYS` | `/api/orders` (GET), `/api/orders/{id}` (PATCH) | Аптеки |
| **Admin** | `ADMIN_API_KEYS` | `/api/orders/bulk-delete`, `/qa/drop`, `/qa/stats` | Администраторы |

---

## 📞 Контакты

| Роль | Обязанности |
|------|-------------|
| Администратор системы | Управление ADMIN_API_KEYS, ротация, аудит |
| Ответственный за ИБ | Мониторинг компрометаций, расследование инцидентов |
| DBA | Восстановление данных после массовых удалений |

---

**Документ подготовил:** AI Assistant  
**Дата:** 05 мая 2026 г.  
**Статус:** Готово к использованию  
**Требуется настройка:** Да (добавить ADMIN_API_KEYS в .env)
