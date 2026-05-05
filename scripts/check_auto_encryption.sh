#!/bin/bash
# Script: check_auto_encryption.sh
# Быстрая проверка работы автоматического шифрования

set -e

echo "=== Проверка автоматического шифрования NovaMedika2 ==="
echo ""

# 1. Проверка наличия файлов
echo "1. Проверка файлов реализации..."
if [ -f "/opt/novamedika-prod/backend/src/db/encryption_events.py" ]; then
    echo "   ✅ encryption_events.py найден"
else
    echo "   ❌ encryption_events.py НЕ найден!"
    exit 1
fi

if grep -q "encryption_events" /opt/novamedika-prod/backend/src/db/__init__.py; then
    echo "   ✅ Импорт в __init__.py настроен"
else
    echo "   ❌ Импорт в __init__.py отсутствует!"
    exit 1
fi

# 2. Проверка логов backend
echo ""
echo "2. Проверка регистрации event listeners..."
if docker logs --tail 200 backend-prod 2>&1 | grep -q "Encryption event listeners registered"; then
    echo "   ✅ Event listeners зарегистрированы"
else
    echo "   ⚠️ Сообщение о регистрации не найдено (возможно, логи старые)"
fi

# 3. Проверка ключа шифрования
echo ""
echo "3. Проверка ключа шифрования..."
ENCRYPTION_KEY=$(docker exec postgres-prod psql -U novamedika -d novamedika_prod -t -A -c \
    "SELECT current_setting('app.encryption_key');" 2>/dev/null || echo "")

if [ -n "$ENCRYPTION_KEY" ] && [ ${#ENCRYPTION_KEY} -gt 30 ]; then
    echo "   ✅ Ключ шифрования настроен (длина: ${#ENCRYPTION_KEY})"
else
    echo "   ❌ Ключ шифрования НЕ настроен!"
    echo "   Выполните fix_encryption.sh сначала"
    exit 1
fi

# 4. Статистика зашифрованных данных
echo ""
echo "4. Статистика зашифрованных данных..."
docker exec postgres-prod psql -U novamedika -d novamedika_prod <<'EOSQL'
-- Пользователи
SELECT 
    'qa_users' as table_name,
    COUNT(*) as total,
    COUNT(telegram_id_encrypted) as encrypted_telegram_ids,
    COUNT(phone_encrypted) as encrypted_phones,
    CASE 
        WHEN COUNT(*) > 0 THEN 
            ROUND(COUNT(telegram_id_encrypted)::numeric / COUNT(*)::numeric * 100, 2)
        ELSE 0 
    END as telegram_encryption_pct
FROM qa_users

UNION ALL

-- Заказы
SELECT 
    'booking_orders' as table_name,
    COUNT(*) as total,
    COUNT(telegram_id_encrypted) as encrypted_telegram_ids,
    COUNT(customer_phone_encrypted) as encrypted_customer_phones,
    CASE 
        WHEN COUNT(*) > 0 THEN 
            ROUND(COUNT(telegram_id_encrypted)::numeric / COUNT(*)::numeric * 100, 2)
        ELSE 0 
    END as telegram_encryption_pct
FROM booking_orders;
EOSQL

# 5. Проверка последнего созданного пользователя
echo ""
echo "5. Последний созданный пользователь:"
docker exec postgres-prod psql -U novamedika -d novamedika_prod -c "
SELECT 
    uuid,
    created_at,
    telegram_id IS NOT NULL as has_plain_id,
    telegram_id_encrypted IS NOT NULL as has_encrypted_id,
    phone IS NOT NULL as has_plain_phone,
    phone_encrypted IS NOT NULL as has_encrypted_phone
FROM qa_users 
ORDER BY created_at DESC 
LIMIT 1;
"

# 6. Тест шифрования нового пользователя
echo ""
echo "6. Тест создания пользователя с шифрованием..."
echo "   Создайте нового пользователя через Telegram бота (/start)"
echo "   Затем повторно запустите этот скрипт для проверки"

echo ""
echo "=== Проверка завершена ==="
echo ""
echo "📊 Интерпретация результатов:"
echo "   ✅ Если у новых пользователей has_encrypted_id = t и has_encrypted_phone = t"
echo "      → Автоматическое шифрование РАБОТАЕТ!"
echo ""
echo "   ❌ Если has_encrypted_id = f или has_encrypted_phone = f"
echo "      → Требуется диагностика (см. AUTO-ENCRYPTION-DEPLOYMENT-GUIDE.md)"
echo ""
