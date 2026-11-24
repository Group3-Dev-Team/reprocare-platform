-- Health library articles can be unpublished (hidden from the public) without being deleted.
-- Additive only. Every existing article, including the seeded ones, keeps being published.
-- Articles written by administrators after this change start unpublished (set by the application).
ALTER TABLE articles ADD COLUMN IF NOT EXISTS is_published BOOLEAN NOT NULL DEFAULT TRUE;
CREATE INDEX IF NOT EXISTS ix_articles_is_published ON articles (is_published);
