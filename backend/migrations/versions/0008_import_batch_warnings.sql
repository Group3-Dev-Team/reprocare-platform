-- Preserve facility import warnings in batch history.
ALTER TABLE import_batches ADD COLUMN IF NOT EXISTS warnings JSON NOT NULL DEFAULT '[]';
