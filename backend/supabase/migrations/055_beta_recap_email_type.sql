-- Migration 055: beta recap email types (2026-06-10)
--
-- The "Lettre de la beta" is the first RECURRING email: one send per
-- user per calendar month, idempotence-keyed as beta_recap_YYYY_MM in
-- onboarding_email_log. The CHECK from migration 048 only allows a
-- fixed list of lifetime-one-shot types and would silently reject the
-- monthly keys (the exact failure mode 048 itself was fixing) — extend
-- it with a prefix match for the recurring family.

ALTER TABLE onboarding_email_log
  DROP CONSTRAINT IF EXISTS onboarding_email_log_type_check;

ALTER TABLE onboarding_email_log
  ADD CONSTRAINT onboarding_email_log_type_check
  CHECK (
    email_type IN (
      'j1_relance',
      'j7_inactivity',
      'j7_feedback_nurture',
      'j14_feedback_relance',
      'j15_open_feedback'
    )
    OR email_type LIKE 'beta_recap_%'
  );
