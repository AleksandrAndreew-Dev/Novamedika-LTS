# РЕГЛАМЕНТ
## управления ключами шифрования

### информационной системы NovaMedika2

---

**[НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ]**

**Версия:** 1.1
**Дата обновления:** 05 мая 2026 г.
**Дата утверждения:** «___» ____________ 20___ г.

---

## 1. ОБЩИЕ ПОЛОЖЕНИЯ

1.1. Настоящий регламент определяет порядок генерации, хранения, использования и ротации криптографических ключей в ИС NovaMedika2.

1.2. Регламент разработан в соответствии с требованиями:
- Приказа ОАЦ № 66 (приложение 3, пункты 5.1–5.5)
- **Приказа ОАЦ № 195 от 12 ноября 2021 г.** (изменения в требованиях к криптографической защите персональных данных)
- Закона РБ № 99-З "О защите персональных данных" (статья 16)

1.3. **Особенности применения согласно Приказу № 195:**
- Для класса 3-ин шифрование при передаче (пункт 5.1) является **обязательным** (+)
- Шифрование при хранении (пункт 5.2) имеет **условное выполнение** (+/–)
- Согласно пункту 19¹ Положения: если ПД получены без криптозащиты, их возврат субъекту может осуществляться также без криптозащиты

1.4. **Текущее состояние реализации (на 05.05.2026):**
- ✅ Реализовано шифрование персональных данных в БД (pgcrypto AES-256)
- ✅ Реализовано шифрование API-токенов аптек (Fernet)
- ✅ HTTPS/TLS для всех внешних соединений (Traefik + Let's Encrypt)
- ✅ Ключи хранятся в .env файле с правами доступа chmod 600
- ⚠️ Требуется настройка автоматической ротации ключей

---

## 2. КРИПТОГРАФИЧЕСКИЕ КЛЮЧИ

### 2.1. Перечень ключей

| Ключ | Алгоритм | Длина | Назначение | Где хранится | Статус |
|------|----------|-------|-----------|-------------|--------|
| ENCRYPTION_KEY | AES-256 (pgcrypto) | 32 байта | Шифрование ПД в БД (telegram_id, phone) | PostgreSQL GUC + .env | ✅ Активен |
| FERNET_KEY | Fernet (AES-128-CBC) | 32 байта Base64 | Шифрование API-токенов аптек | .env | ✅ Активен |
| SECRET_KEY | HMAC-SHA256 | 32+ байта | JWT подписи | .env | ✅ Активен |
| REDIS_PASSWORD | — | 16+ символов | Аутентификация Redis | .env | ✅ Активен |
| POSTGRES_PASSWORD | — | 16+ символов | Аутентификация PostgreSQL | .env | ✅ Активен |
| SSL_EMAIL | — | — | TLS-сертификаты Let's Encrypt | .env + Traefik ACME | ✅ Активен |

### 2.2. Требования к ключам

| Ключ | Генерация | Сложность | Ротация | Последняя ротация |
|------|----------|-----------|---------|------------------|
| ENCRYPTION_KEY | `openssl rand -base64 32` | 256 бит | 1 год | При развертывании (апрель 2026) |
| FERNET_KEY | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | 128 бит | 1 год | При развертывании (апрель 2026) |
| SECRET_KEY | `openssl rand -base64 64` | 512 бит | 6 месяцев | При развертывании (апрель 2026) |
| REDIS_PASSWORD | Генератор паролей | 16+ символов, [A-Za-z0-9!@#$%] | 6 месяцев | При развертывании (апрель 2026) |
| POSTGRES_PASSWORD | Генератор паролей | 16+ символов, [A-Za-z0-9!@#$%] | 6 месяцев | При развертывании (апрель 2026) |

---

## 3. ПОРЯДОК ХРАНЕНИЯ КЛЮЧЕЙ

### 3.1. Production

| Хранилище | Какие ключи | Доступ | Защита |
|-----------|------------|--------|--------|
| .env на сервере (/opt/novamedika-prod/.env) | Все ключи | root, novamedika (владелец), chmod 600 | Файловая система Linux, права доступа |
| PostgreSQL GUC (app.encryption_key) | ENCRYPTION_KEY | Только DBA, SUPERUSER | Внутреннее хранилище PostgreSQL |
| GitHub Secrets (CI/CD) | Все ключи (для деплоя) | Только администраторы репозитория | Шифрование GitHub |
| Docker secrets (runtime) | Ключи передаются через environment | Только внутри контейнеров | Изоляция контейнеров Docker |

### 3.2. Требования к защите

- ✅ Файл .env: `chmod 600`, владелец — `novamedika:novamedika`
- ✅ Ключи НЕ коммитятся в git (.gitignore включает .env)
- ✅ Ключи НЕ передаются по незащищённым каналам (только HTTPS/SSH)
- ⚠️ При компрометации — немедленная ротация (процедура описана в разделе 4)
- ✅ CI/CD pipeline использует GitHub Secrets для безопасной передачи ключей

---

## 4. ПОРЯДОК РОТАЦИИ КЛЮЧЕЙ

### 4.1. Плановая ротация

| Ключ | Периодичность | Ответственный | Следующая ротация |
|------|--------------|--------------|------------------|
| ENCRYPTION_KEY | 1 год | Администратор БД | Апрель 2027 |
| FERNET_KEY | 1 год | Администратор backend | Апрель 2027 |
| SECRET_KEY | 6 месяцев | Администратор backend | Октябрь 2026 |
| REDIS_PASSWORD | 6 месяцев | Администратор инфраструктуры | Октябрь 2026 |
| POSTGRES_PASSWORD | 6 месяцев | Администратор БД | Октябрь 2026 |

### 4.2. Внеплановая ротация

Внеплановая ротация выполняется в следующих случаях:
1. Подозрение на компрометацию ключа
2. Увольнение сотрудника, имевшего доступ к ключам
3. Изменение архитектуры системы
4. По требованию аудитора безопасности

### 4.3. Процедура ротации ENCRYPTION_KEY

**Важно:** Ротация ENCRYPTION_KEY требует перешифрования всех существующих данных.

```bash
# === ЭТАП 1: Подготовка ===

# 1. Создать backup базы данных
docker exec postgres-prod pg_dump -U novamedika novamedika_prod > /backups/pre_rotation_$(date +%Y%m%d).sql

# 2. Проверить целостность backup
gzip /backups/pre_rotation_$(date +%Y%m%d).sql
gunzip -t /backups/pre_rotation_$(date +%Y%m%d).sql.gz

# === ЭТАП 2: Генерация нового ключа ===

# 3. Генерируем новый ключ
NEW_KEY=$(openssl rand -base64 32)
echo "Новый ключ: $NEW_KEY"

# 4. Сохраняем старый ключ для перешифрования
OLD_KEY=$(grep ENCRYPTION_KEY /opt/novamedika-prod/.env | cut -d'=' -f2)

# === ЭТАП 3: Обновление конфигурации ===

# 5. В production: обновляем .env
sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=${NEW_KEY}/" /opt/novamedika-prod/.env

# 6. Обновляем GUC в PostgreSQL
docker exec postgres-prod psql -U postgres -c \
  "ALTER DATABASE novamedika_prod SET app.encryption_key = '${NEW_KEY}';"

# === ЭТАП 4: Перешифрование данных ===

# 7. Запускаем скрипт перешифрования
docker exec postgres-prod psql -U novamedika -d novamedika_prod <<EOF
-- Перешифровать telegram_id в qa_users
UPDATE qa_users 
SET telegram_id_encrypted = ENCODE(
    pgp_sym_encrypt(telegram_id::text, current_setting('app.encryption_key')),
    'base64'
)
WHERE telegram_id IS NOT NULL;

-- Перешифровать phone в qa_users
UPDATE qa_users 
SET phone_encrypted = ENCODE(
    pgp_sym_encrypt(phone, current_setting('app.encryption_key')),
    'base64'
)
WHERE phone IS NOT NULL;

-- Перешифровать customer_phone в booking_orders
UPDATE booking_orders 
SET customer_phone_encrypted = ENCODE(
    pgp_sym_encrypt(customer_phone, current_setting('app.encryption_key')),
    'base64'
)
WHERE customer_phone IS NOT NULL;

-- Перешифровать telegram_id в booking_orders
UPDATE booking_orders 
SET telegram_id_encrypted = ENCODE(
    pgp_sym_encrypt(telegram_id::text, current_setting('app.encryption_key')),
    'base64'
)
WHERE telegram_id IS NOT NULL;
EOF

# === ЭТАП 5: Перезапуск сервисов ===

# 8. Перезапускаем PostgreSQL для применения нового GUC
docker restart postgres-prod

# 9. Перезапускаем backend для обновления FERNET_KEY (если менялся)
docker restart backend-prod

# 10. Проверяем работоспособность
sleep 10
curl -f https://spravka.novamedika.com/api/health || echo "ERROR: Backend не отвечает!"

# === ЭТАП 6: Верификация ===

# 11. Проверяем расшифровку данных
docker exec postgres-prod psql -U novamedika -d novamedika_prod -c \
  "SELECT COUNT(*) FROM qa_users WHERE telegram_id_encrypted IS NOT NULL;"

# 12. Тестируем Telegram бота
# Отправить тестовое сообщение боту и проверить обработку

# === ЭТАП 7: Очистка ===

# 13. Удаляем старый ключ из истории bash
history -c

# 14. Архивируем старый ключ в защищенное хранилище
echo "$OLD_KEY" > /secure/old_keys/encryption_key_$(date +%Y%m%d).txt
chmod 600 /secure/old_keys/encryption_key_$(date +%Y%m%d).txt
```

### 4.4. Процедура ротации FERNET_KEY

```bash
# 1. Генерируем новый Fernet ключ
NEW_FERNET=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 2. Обновляем .env
sed -i "s/FERNET_KEY=.*/FERNET_KEY=${NEW_FERNET}/" /opt/novamedika-prod/.env

# 3. Перезапускаем backend
docker restart backend-prod

# 4. Проверяем API аптеки
curl -f https://spravka.novamedika.com/api/pharmacies/health
```

### 4.5. Процедура ротации SECRET_KEY (JWT)

**Внимание:** Ротация SECRET_KEY инвалидирует все активные JWT токены. Пользователи будут вынуждены повторно войти в систему.

```bash
# 1. Генерируем новый SECRET_KEY
NEW_SECRET=$(openssl rand -base64 64)

# 2. Обновляем .env
sed -i "s/SECRET_KEY=.*/SECRET_KEY=${NEW_SECRET}/" /opt/novamedika-prod/.env

# 3. Перезапускаем backend
docker restart backend-prod

# 4. Очищаем Redis сессии (опционально)
docker exec redis-prod redis-cli -a "$REDIS_PASSWORD" FLUSHDB

# 5. Уведомляем пользователей о необходимости повторного входа
```

---

## 5. МОНИТОРИНГ И АУДИТ

### 5.1. Контрольные точки

| Проверка | Периодичность | Метод |
|----------|--------------|-------|
| Проверка прав доступа к .env | Ежемесячно | `ls -la /opt/novamedika-prod/.env` |
| Проверка наличия ключей в git | При каждом комите | pre-commit hook |
| Проверка сроков действия ключей | Ежеквартально | Сверка с таблицей 4.1 |
| Тестирование процедуры ротации | Раз в год | Учебная ротация в staging |

### 5.2. Логирование операций с ключами

Все операции с криптографическими ключами должны логироваться:

```bash
# Пример записи в журнал
echo "[$(date)] ROTATION: ENCRYPTION_KEY rotated by admin@example.com" >> /var/log/crypto-operations.log
echo "[$(date)] ACCESS: .env accessed by user novamedika" >> /var/log/crypto-operations.log
```

### 5.3. Аудит соответствия

Ежегодный аудит включает:
1. Проверку соблюдения сроков ротации
2. Анализ инцидентов компрометации
3. Тестирование процедур восстановления
4. Проверку актуальности документации

---

## 6. ОТВЕТСТВЕННОСТЬ

### 6.1. Распределение ответственности

| Роль | Ответственность |
|------|----------------|
| Администратор БД | Ротация ENCRYPTION_KEY, POSTGRES_PASSWORD |
| Администратор backend | Ротация FERNET_KEY, SECRET_KEY |
| Администратор инфраструктуры | Ротация REDIS_PASSWORD, мониторинг |
| Ответственный за ИБ | Аудит, контроль сроков, расследование инцидентов |

### 6.2. Действия при компрометации

1. **Немедленно:** Изолировать затронутые системы
2. **В течение 1 часа:** Выполнить ротацию скомпрометированного ключа
3. **В течение 24 часов:** Провести анализ масштаба инцидента
4. **В течение 72 часов:** Предоставить отчет руководству
5. **В течение 7 дней:** Обновить процедуры безопасности

---

## 7. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ

7.1. Настоящий регламент вступает в силу с момента утверждения.

7.2. Изменения в регламент вносятся приказом руководителя организации.

7.3. С регламентом должны быть ознакомлены все сотрудники, имеющие доступ к криптографическим ключам.

---

**СОГЛАСОВАНО:**

Руководитель организации: _________________ / _________________ /

Ответственный за ИБ: _________________ / _________________ /

Администратор БД: _________________ / _________________ /

Дата: «___» ____________ 20___ г.
