-- Script: enable_encryption.sql
-- Description: Включение шифрования чувствительных данных в NovaMedika2
-- Usage: docker exec -i postgres-prod psql -U <user> -d <db> < scripts/enable_encryption.sql
-- WARNING: Сделайте backup перед выполнением!

-- ==================== 1. Установка расширения pgcrypto ====================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Проверка установки
SELECT extname, extversion FROM pg_extension WHERE extname = 'pgcrypto';

-- ==================== 2. Создание функций шифрования ====================

-- Функция шифрования текста
CREATE OR REPLACE FUNCTION encrypt_text(data text, encryption_key text)
RETURNS bytea AS $$
BEGIN
    IF data IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN pgp_sym_encrypt(data, encryption_key);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Функция расшифровки текста
CREATE OR REPLACE FUNCTION decrypt_text(encrypted_data bytea, encryption_key text)
RETURNS text AS $$
BEGIN
    IF encrypted_data IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN pgp_sym_decrypt(encrypted_data, encryption_key);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==================== 3. Добавление зашифрованных колонок ====================

-- Таблица users (пользователи)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS phone_encrypted bytea,
ADD COLUMN IF NOT EXISTS telegram_id_encrypted bytea,
ADD COLUMN IF NOT EXISTS first_name_encrypted bytea,
ADD COLUMN IF NOT EXISTS last_name_encrypted bytea;

-- Таблица pharmacists (фармацевты)
ALTER TABLE pharmacists 
ADD COLUMN IF NOT EXISTS phone_encrypted bytea,
ADD COLUMN IF NOT EXISTS telegram_id_encrypted bytea,
ADD COLUMN IF NOT EXISTS first_name_encrypted bytea,
ADD COLUMN IF NOT EXISTS last_name_encrypted bytea,
ADD COLUMN IF NOT EXISTS patronymic_encrypted bytea;

-- Таблица orders (заказы)
ALTER TABLE booking_orders 
ADD COLUMN IF NOT EXISTS customer_phone_encrypted bytea,
ADD COLUMN IF NOT EXISTS customer_name_encrypted bytea;

-- ==================== 4. Миграция существующих данных ====================
-- WARNING: Замените 'YOUR_ENCRYPTION_KEY' на реальный ключ из .env файла!
-- Ключ должен быть минимум 16 символов и храниться в безопасном месте

DO $$
DECLARE
    encryption_key text := 'YOUR_ENCRYPTION_KEY'; -- ЗАМЕНИТЕ ЭТО!
BEGIN
    -- Шифрование данных в таблице users
    UPDATE users 
    SET 
        phone_encrypted = encrypt_text(phone, encryption_key),
        telegram_id_encrypted = encrypt_text(telegram_id::text, encryption_key),
        first_name_encrypted = encrypt_text(first_name, encryption_key),
        last_name_encrypted = encrypt_text(last_name, encryption_key)
    WHERE phone_encrypted IS NULL AND phone IS NOT NULL;

    -- Шифрование данных в таблице pharmacists
    UPDATE pharmacists 
    SET 
        phone_encrypted = encrypt_text(phone, encryption_key),
        telegram_id_encrypted = encrypt_text(telegram_id::text, encryption_key),
        first_name_encrypted = encrypt_text(first_name, encryption_key),
        last_name_encrypted = encrypt_text(last_name, encryption_key),
        patronymic_encrypted = encrypt_text(patronymic, encryption_key)
    WHERE phone_encrypted IS NULL AND phone IS NOT NULL;

    -- Шифрование данных в таблице booking_orders
    UPDATE booking_orders 
    SET 
        customer_phone_encrypted = encrypt_text(customer_phone, encryption_key),
        customer_name_encrypted = encrypt_text(customer_name, encryption_key)
    WHERE customer_phone_encrypted IS NULL AND customer_phone IS NOT NULL;

END $$;

-- ==================== 5. Создание индексов для производительности ====================
-- Индексы не нужны для зашифрованных данных (они бинарные)
-- Но можно создать индекс на ID для быстрого поиска

-- ==================== 6. Удаление открытых данных (ОПЦИОНАЛЬНО) ====================
-- WARNING: Выполняйте ТОЛЬКО после проверки, что все данные зашифрованы!
-- Раскомментируйте следующие строки для удаления открытых данных:

-- ALTER TABLE users DROP COLUMN IF EXISTS phone, DROP COLUMN IF EXISTS telegram_id;
-- ALTER TABLE pharmacists DROP COLUMN IF EXISTS phone, DROP COLUMN IF EXISTS telegram_id;
-- ALTER TABLE booking_orders DROP COLUMN IF EXISTS customer_phone;

-- ==================== 7. Проверка результатов ====================

-- Подсчет зашифрованных записей
SELECT 
    'users' as table_name,
    COUNT(*) as total_records,
    COUNT(phone_encrypted) as encrypted_records
FROM users

UNION ALL

SELECT 
    'pharmacists' as table_name,
    COUNT(*) as total_records,
    COUNT(phone_encrypted) as encrypted_records
FROM pharmacists

UNION ALL

SELECT 
    'booking_orders' as table_name,
    COUNT(*) as total_records,
    COUNT(customer_phone_encrypted) as encrypted_records
FROM booking_orders;

-- Проверка качества шифрования (должны быть разные значения для одинаковых данных)
SELECT 
    phone,
    phone_encrypted,
    LENGTH(phone_encrypted) as encrypted_length
FROM users 
WHERE phone IS NOT NULL 
LIMIT 5;

-- Тест расшифровки
SELECT 
    phone,
    decrypt_text(phone_encrypted, 'YOUR_ENCRYPTION_KEY') as decrypted_phone
FROM users 
WHERE phone_encrypted IS NOT NULL 
LIMIT 5;

-- ==================== 8. Создание представлений для удобного доступа ====================

-- Представление для пользователей с автоматической расшифровкой
CREATE OR REPLACE VIEW users_decrypted AS
SELECT 
    id,
    decrypt_text(first_name_encrypted, 'YOUR_ENCRYPTION_KEY') as first_name,
    decrypt_text(last_name_encrypted, 'YOUR_ENCRYPTION_KEY') as last_name,
    decrypt_text(phone_encrypted, 'YOUR_ENCRYPTION_KEY') as phone,
    decrypt_text(telegram_id_encrypted, 'YOUR_ENCRYPTION_KEY')::bigint as telegram_id,
    created_at,
    updated_at
FROM users;

-- Представление для фармацевтов с автоматической расшифровкой
CREATE OR REPLACE VIEW pharmacists_decrypted AS
SELECT 
    id,
    decrypt_text(first_name_encrypted, 'YOUR_ENCRYPTION_KEY') as first_name,
    decrypt_text(last_name_encrypted, 'YOUR_ENCRYPTION_KEY') as last_name,
    decrypt_text(patronymic_encrypted, 'YOUR_ENCRYPTION_KEY') as patronymic,
    decrypt_text(phone_encrypted, 'YOUR_ENCRYPTION_KEY') as phone,
    decrypt_text(telegram_id_encrypted, 'YOUR_ENCRYPTION_KEY')::bigint as telegram_id,
    status,
    created_at,
    updated_at
FROM pharmacists;

-- ==================== 9. Настройка прав доступа ====================

-- Предоставление прав на функции шифрования только авторизованным ролям
REVOKE ALL ON FUNCTION encrypt_text(text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION decrypt_text(bytea, text) FROM PUBLIC;

-- Grant to application role (если используется)
-- GRANT EXECUTE ON FUNCTION encrypt_text(text, text) TO app_user;
-- GRANT EXECUTE ON FUNCTION decrypt_text(bytea, text) TO app_user;

-- ==================== ЗАВЕРШЕНИЕ ====================

COMMENT ON EXTENSION pgcrypto IS 'Cryptographic functions for data encryption (OAC compliance)';
COMMENT ON FUNCTION encrypt_text(text, text) IS 'Encrypts text data using pgp_sym_encrypt';
COMMENT ON FUNCTION decrypt_text(bytea, text) IS 'Decrypts text data using pgp_sym_decrypt';

-- Сообщение об успешном выполнении
DO $$
BEGIN
    RAISE NOTICE '✅ Шифрование успешно настроено!';
    RAISE NOTICE '⚠️  ВАЖНО:';
    RAISE NOTICE '   1. Замените YOUR_ENCRYPTION_KEY на реальный ключ в коде приложения';
    RAISE NOTICE '   2. Сохраните ключ в безопасном месте (.env файл)';
    RAISE NOTICE '   3. Обновите application code для использования зашифрованных полей';
    RAISE NOTICE '   4. Протестируйте расшифровку перед удалением открытых данных';
END $$;
