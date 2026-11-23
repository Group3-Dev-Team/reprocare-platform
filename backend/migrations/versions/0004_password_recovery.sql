-- table for password reset links (only the hash of the token is saved)
CREATE TABLE IF NOT EXISTS password_resets (
    token_hash VARCHAR(64) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    password_fingerprint VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_password_resets_user_id ON password_resets (user_id);
CREATE INDEX IF NOT EXISTS ix_password_resets_expires_at ON password_resets (expires_at);