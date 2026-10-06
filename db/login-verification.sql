BEGIN;

ALTER TABLE app_user
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS verification_token_hash CHAR(64),
    ADD COLUMN IF NOT EXISTS verification_expires_at TIMESTAMPTZ;

-- Existing accounts predate email verification and remain usable.
UPDATE app_user
SET email_verified = TRUE
WHERE email_verified IS FALSE
  AND verification_token_hash IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS app_user_verification_token_hash_uq
    ON app_user (verification_token_hash)
    WHERE verification_token_hash IS NOT NULL;

COMMIT;