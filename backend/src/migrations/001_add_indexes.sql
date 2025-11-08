-- app/migrations/001_add_indexes.sql (добавляем индексы для производительности)
CREATE INDEX IF NOT EXISTS idx_products_pharmacy_id ON products(pharmacy_id);
CREATE INDEX IF NOT EXISTS idx_products_serial ON products(serial);
CREATE INDEX IF NOT EXISTS idx_products_expiry_date ON products(expiry_date);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);

-- Составной индекс для быстрого поиска дубликатов
CREATE INDEX IF NOT EXISTS idx_products_unique_identity
ON products(name, serial, expiry_date, pharmacy_id);


ALTER TABLE products ALTER COLUMN expiry_date DROP NOT NULL;
