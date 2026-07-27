# Шпаргалка: Быстрая настройка шифрования на продакшене

**Версия:** 1.0 | **Дата:** 28 апреля 2026 г.

---

## 🚀 Быстрый старт (5 минут)

```bash
# 1. Подключиться к серверу
ssh user@your-server.com
cd /path/to/Novamedika2

# 2. Сделать бэкап БД
docker exec postgres-prod pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql

# 3. Сгенерировать ключ
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "Ключ: $ENCRYPTION_KEY"
echo "СОХРАНИТЕ ЭТОТ КЛЮЧ В БЕЗОПАСНОМ МЕСТЕ!"

# 4. Добавить ключ в .env
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY" >> .env

# 5. Применить миграцию
docker exec -it backend-prod alembic upgrade head

# 6. Установить pgcrypto
docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"

# 7. Перезапустить сервисы
docker compose -f docker-compose.traefik.prod.yml restart backend celery_worker

# 8. Подождать и проверить
sleep 30
curl -f https://api.novamedika.com/health
docker logs backend-prod --tail 20 | grep -i encrypt
```

---

## ✅ Проверка работоспособности

```bash
# Тест шифрования
docker exec -it backend-prod python3 -c "
import sys; sys.path.insert(0, '/app/src')
from utils.encryption import encrypt_value, decrypt_value
test = '+375291234567'
enc = encrypt_value(test)
dec = decrypt_value(enc)
print('✓ OK' if test == dec else '✗ FAIL')
"

# Проверить колонки в БД
docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
SELECT column_name FROM information_schema.columns 
WHERE table_name='qa_users' AND column_name LIKE '%encrypted%';
"
```

---

## 🔄 Откат (если что-то пошло не так)

```bash
# Восстановить БД из бэкапа
cat backup_YYYYMMDD_HHMMSS.sql | docker exec -i postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB

# Откатить миграцию
docker exec -it backend-prod alembic downgrade -1

# Перезапустить
docker compose -f docker-compose.traefik.prod.yml up -d
```

---

## ⚠️ Важные предупреждения

1. **Никогда не коммитьте .env в Git!**
   ```bash
   echo ".env" >> .gitignore
   git add .gitignore
   git commit -m "Secure .env file"
   ```

2. **Сохраните ключ шифрования!** Без него данные нельзя будет расшифровать

3. **Используйте разные ключи** для dev/prod/staging

4. **При компрометации ключа** нужно перешифровать все данные новым ключом

---

## 📊 Что проверяем после настройки

- [ ] `curl -f https://api.novamedika.com/health` возвращает OK
- [ ] В логах нет ошибок: `docker logs backend-prod | grep -i error`
- [ ] Тест шифрования проходит: ✓ OK
- [ ] Новые пользователи создаются с зашифрованными данными
- [ ] Производительность в норме (<10ms overhead)

---

## 🆘 Быстрые команды для диагностики

```bash
# Проверить статус сервисов
docker compose -f docker-compose.traefik.prod.yml ps

# Посмотреть логи backend
docker logs backend-prod --tail 50

# Посмотреть логи celery
docker logs celery-worker-prod --tail 50

# Проверить переменные окружения
docker exec backend-prod env | grep ENCRYPTION

# Проверить версию миграции
docker exec -it backend-prod alembic current

# Проверить расширение pgcrypto
docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\dx pgcrypto"

# Статистика по зашифрованным данным
docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
SELECT COUNT(*) as total, 
       COUNT(telegram_id_encrypted) as encrypted_tg 
FROM qa_users;
"
```

---

## 📞 Экстренная помощь

Если сервисы не запускаются:

```bash
# 1. Посмотреть детальные логи
docker logs backend-prod --tail 200

# 2. Проверить конфигурацию
docker compose -f docker-compose.traefik.prod.yml config

# 3. Пересоздать контейнеры
docker compose -f docker-compose.traefik.prod.yml down
docker compose -f docker-compose.traefik.prod.yml up -d

# 4. Проверить здоровье БД
docker exec postgres-prod pg_isready -U $POSTGRES_USER

# 5. Проверить здоровье Redis
docker exec redis-prod redis-cli -a $REDIS_PASSWORD ping
```

---

**Полная документация:** [PRODUCTION-ENCRYPTION-SETUP.md](./PRODUCTION-ENCRYPTION-SETUP.md)  
**Техническое руководство:** [ENCRYPTION-IMPLEMENTATION-GUIDE.md](./ENCRYPTION-IMPLEMENTATION-GUIDE.md)
