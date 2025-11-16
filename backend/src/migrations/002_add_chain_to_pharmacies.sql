ALTER TABLE pharmacies ADD COLUMN chain VARCHAR(50);

UPDATE pharmacies SET chain = 'Новамедика' WHERE name = 'Новамедика';
UPDATE pharmacies SET chain = 'Эклиния' WHERE name = 'ЭКЛИНИЯ';
