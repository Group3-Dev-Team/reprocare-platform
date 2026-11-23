-- tables for Google sign-in (only used when Google sign-in is turned on)
CREATE TABLE IF NOT EXISTS google_identities (
    subject VARCHAR(255) PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS google_authorizations (
    state_hash VARCHAR(64) PRIMARY KEY,
    challenge VARCHAR(43) NOT NULL,
    nonce VARCHAR(64) NOT NULL,
    intent VARCHAR(12) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_google_authorizations_expires_at ON google_authorizations (expires_at);

CREATE TABLE IF NOT EXISTS google_link_authorizations (
    state_hash VARCHAR(64) PRIMARY KEY REFERENCES google_authorizations(state_hash) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    binding VARCHAR(64) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_google_link_authorizations_user_id ON google_link_authorizations (user_id);