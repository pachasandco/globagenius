-- 063_email_log_freemium_types.sql
--
-- Programme d'emails freemium (2026-07-30) : trois nouveaux types
-- d'emails idempotents tracés dans onboarding_email_log, avec clé
-- périodique intégrée au type (même mécanique que beta_recap_%) :
--   freemium_digest_YYYY_WW   — récap hebdo (1/user/semaine ISO)
--   freemium_quota_YYYY_WW    — quota atteint (max 1/user/semaine ISO)
--   freemium_monthly_YYYY_MM  — bilan mensuel (1/user/mois)
--
-- NB: les 3 types beta feedback (j7/j14/j15) restent autorisés pour les
-- lignes historiques même si les flows ont été décommissionnés.

-- Deux noms possibles selon l'époque d'application (048 nommait la
-- contrainte _type_check, le nom auto-généré est _email_type_check) —
-- on droppe les deux pour ne laisser qu'une seule contrainte à jour.
ALTER TABLE onboarding_email_log
    DROP CONSTRAINT IF EXISTS onboarding_email_log_email_type_check;
ALTER TABLE onboarding_email_log
    DROP CONSTRAINT IF EXISTS onboarding_email_log_type_check;

ALTER TABLE onboarding_email_log
    ADD CONSTRAINT onboarding_email_log_email_type_check
    CHECK (
        email_type IN (
            'j1_relance',
            'j7_inactivity',
            'j7_feedback_nurture',
            'j14_feedback_relance',
            'j15_open_feedback'
        )
        OR email_type LIKE 'beta_recap_%'
        OR email_type LIKE 'freemium_%'
    );
