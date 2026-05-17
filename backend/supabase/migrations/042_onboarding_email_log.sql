-- Migration 042: onboarding_email_log — chantier 10 (2026-05-17)
--
-- Tracks which onboarding follow-up emails have been sent to which
-- user. Prevents the daily cron from re-sending the same J+1
-- reminder or J+7 nudge if it runs twice (e.g. a scheduler restart
-- mid-day).
--
-- We don't track the welcome email (J0) here — that one is fired
-- inline by /api/signup as part of BackgroundTasks and isn't part
-- of the cron-driven cohort.

CREATE TABLE IF NOT EXISTS onboarding_email_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email_type varchar(32) NOT NULL,
    sent_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_onboarding_email_log_user_type
  ON onboarding_email_log(user_id, email_type);

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'onboarding_email_log_type_check'
  ) THEN
    ALTER TABLE onboarding_email_log
      ADD CONSTRAINT onboarding_email_log_type_check
      CHECK (email_type IN ('j1_relance', 'j7_inactivity'));
  END IF;
END $$;
