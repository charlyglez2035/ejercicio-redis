BEGIN;

CREATE TABLE IF NOT EXISTS jwt_revocation (
    jti TEXT PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS jwt_revocation_expires_at_idx
    ON jwt_revocation (expires_at);

COMMIT;