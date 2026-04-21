-- Скрипт для настройки шифрования персональных данных в PostgreSQL
-- Запускать после применения миграции Alembic

-- Шаг 1: Установить расширение pgcrypto (если еще не установлено)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Шаг 2: Настроить ключ шифрования
-- ВАЖНО: Замените 'YOUR-SECRET-ENCRYPTION-KEY-HERE' на реальный ключ!
-- Ключ должен быть минимум 8 символов, рекомендуется 32+ символа

-- Установить ключ шифрования для текущей сессии
SET app.encryption_key = 'YOUR-SECRET-ENCRYPTION-KEY-HERE';

-- Для постоянного хранения ключа, добавьте в postgresql.conf:
-- shared_preload_libraries = 'pgcrypto'
-- custom_variable_classes = 'app'
-- app.encryption_key = 'YOUR-SECRET-ENCRYPTION-KEY-HERE'

-- ИЛИ используйте ALTER SYSTEM (требует перезагрузки):
-- ALTER SYSTEM SET app.encryption_key = 'YOUR-SECRET-ENCRYPTION-KEY-HERE';

-- Шаг 3: Проверить, что расширение установлено
SELECT extname, extversion FROM pg_extension WHERE extname = 'pgcrypto';

-- Шаг 4: Протестировать шифрование/дешифрование
DO $$
DECLARE
    test_text TEXT := 'Test encryption';
    encrypted TEXT;
    decrypted TEXT;
BEGIN
    -- Тест шифрования текста
    encrypted := ENCODE(pgp_sym_encrypt(test_text, current_setting('app.encryption_key')), 'base64');
    decrypted := pgp_sym_decrypt(DECODE(encrypted, 'base64'), current_setting('app.encryption_key'));
    
    RAISE NOTICE 'Original: %', test_text;
    RAISE NOTICE 'Encrypted: %', encrypted;
    RAISE NOTICE 'Decrypted: %', decrypted;
    
    IF test_text = decrypted THEN
        RAISE NOTICE '✓ Шифрование работает корректно!';
    ELSE
        RAISE EXCEPTION '✗ Ошибка шифрования!';
    END IF;
END $$;

-- Шаг 5: Проверить количество записей для шифрования
SELECT 
    'qa_users' as table_name,
    COUNT(*) as total_records,
    COUNT(telegram_id) as telegram_ids_to_encrypt,
    COUNT(phone) as phones_to_encrypt
FROM qa_users
UNION ALL
SELECT 
    'booking_orders' as table_name,
    COUNT(*) as total_records,
    COUNT(telegram_id) as telegram_ids_to_encrypt,
    COUNT(customer_phone) as phones_to_encrypt
FROM booking_orders;

-- Шаг 6: После успешного выполнения миграции и проверки данных,
-- можно удалить старые незашифрованные поля (ОПЦИОНАЛЬНО, не рекомендуется сразу!)

-- ВНИМАНИЕ: Выполняйте эти команды ТОЛЬКО после полной проверки работоспособности!
-- ALTER TABLE qa_users DROP COLUMN telegram_id;
-- ALTER TABLE qa_users DROP COLUMN phone;
-- ALTER TABLE booking_orders DROP COLUMN telegram_id;
-- ALTER TABLE booking_orders DROP COLUMN customer_phone;
