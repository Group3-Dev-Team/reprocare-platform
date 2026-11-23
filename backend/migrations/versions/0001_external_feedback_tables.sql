-- 0001: external public feedback tables (SYSTEM 2), separate from ReproCare `reviews` (SYSTEM 1).
-- The tables themselves are created from the SQLAlchemy models by `python -m app.database.migrate`
-- (create_all only adds missing tables). This file records the version and adds supporting indexes.
CREATE INDEX IF NOT EXISTS ix_external_posts_facility_platform ON external_posts (facility_id, platform);
CREATE INDEX IF NOT EXISTS ix_external_comments_post_status ON external_comments (post_id, status);
