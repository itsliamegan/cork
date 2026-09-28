-- Pins may be saved without a URL.
ALTER TABLE pins ALTER COLUMN url DROP NOT NULL;
