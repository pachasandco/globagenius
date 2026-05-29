-- 050_survey_responses.sql
-- Inline-button surveys sent over Telegram. One row per (user, survey,
-- choice). A user can change their mind (re-click another button) — we
-- upsert on (user_id, survey_key) so the latest choice wins, exactly
-- like the alert feedback flow.
--
-- survey_key namespaces a campaign (e.g. "why_no_click_202605") so we can
-- run several surveys over time without mixing results.
-- choice is the single-letter option (A..E).

CREATE TABLE IF NOT EXISTS survey_responses (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    survey_key  text NOT NULL,
    choice      text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, survey_key)
);

CREATE INDEX IF NOT EXISTS idx_survey_responses_key
    ON survey_responses (survey_key);
