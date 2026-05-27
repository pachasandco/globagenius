-- Migration 048: allow feedback-nurturing types in onboarding_email_log
--
-- Migration 042 created the type CHECK with only ('j1_relance',
-- 'j7_inactivity'). The feedback-nurturing emails added 2026-05-21
-- (j7_feedback_nurture, j14_feedback_relance, j15_open_feedback) were
-- never added to the constraint, so their _mark_sent inserts were
-- silently rejected by the CHECK — the user was never logged as mailed
-- and the daily cron re-sent those emails on every run. Extend the
-- constraint to cover all current onboarding email types.

ALTER TABLE onboarding_email_log
  DROP CONSTRAINT IF EXISTS onboarding_email_log_type_check;

ALTER TABLE onboarding_email_log
  ADD CONSTRAINT onboarding_email_log_type_check
  CHECK (email_type IN (
    'j1_relance',
    'j7_inactivity',
    'j7_feedback_nurture',
    'j14_feedback_relance',
    'j15_open_feedback'
  ));
