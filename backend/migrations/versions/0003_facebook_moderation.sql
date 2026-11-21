ALTER TABLE external_posts
    ADD COLUMN IF NOT EXISTS facebook_scope VARCHAR(20)
        CONSTRAINT ck_external_posts_facebook_scope
        CHECK (facebook_scope IS NULL OR (platform = 'facebook' AND facebook_scope IN ('facility', 'organization'))),
    ADD COLUMN IF NOT EXISTS facebook_reviewed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS facebook_reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS facebook_review_note TEXT;
