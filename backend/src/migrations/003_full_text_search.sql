-- migrations/001_full_text_search.sql
-- Выполнить ЭТУ МИГРАЦИЮ на сервере ПОСЛЕ деплоя

-- Включение расширений PostgreSQL
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Создание функции для нормализации текста
CREATE OR REPLACE FUNCTION unaccent_text(text)
RETURNS text AS $$
    SELECT unaccent($1);
$$ LANGUAGE SQL IMMUTABLE;

-- Обновление search_vector для существующих записей
UPDATE products
SET search_vector =
    to_tsvector(
        'russian',
        unaccent_text(coalesce(name, '')) || ' ' ||
        unaccent_text(coalesce(manufacturer, '')) || ' ' ||
        unaccent_text(coalesce(form, '')) || ' ' ||
        unaccent_text(coalesce(country, ''))
    );

-- Триггер для автоматического обновления search_vector
CREATE OR REPLACE FUNCTION product_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        to_tsvector(
            'russian',
            unaccent_text(coalesce(NEW.name, '')) || ' ' ||
            unaccent_text(coalesce(NEW.manufacturer, '')) || ' ' ||
            unaccent_text(coalesce(NEW.form, '')) || ' ' ||
            unaccent_text(coalesce(NEW.country, ''))
        );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER product_search_vector_trigger
BEFORE INSERT OR UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION product_search_vector_update();

-- СОЗДАНИЕ ОПТИМИЗИРОВАННЫХ ИНДЕКСОВ
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_name_trgm ON products USING gin (name gin_trgm_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_manufacturer_trgm ON products USING gin (manufacturer gin_trgm_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_form_trgm ON products USING gin (form gin_trgm_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pharmacy_city_trgm ON pharmacies USING gin (city gin_trgm_ops);

-- Композитные индексы для частых запросов
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_search_composite ON products (name, price, form);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_city_price ON products (pharmacy_id, price) WHERE price > 0;
