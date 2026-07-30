-- 062_users_marketing_consent.sql
--
-- Programme d'emails freemium (2026-07-30). La prospection commerciale
-- par email exige un consentement préalable explicite (CNIL) : la simple
-- création de compte ne suffit pas, et la case doit être décochée par
-- défaut. Ce consentement est collecté au signup (nouveaux inscrits
-- uniquement — décision fondateur) et modifiable depuis le profil.
-- Les users existants restent à false : ils ne recevront aucun email
-- marketing sauf opt-in volontaire via leur profil.
--
-- marketing_consent_at trace le moment du consentement (preuve CNIL).

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS marketing_consent boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS marketing_consent_at timestamptz;

-- Requêtes du programme : "tous les free consentants" — index partiel
-- (la colonne est false pour l'immense majorité).
CREATE INDEX IF NOT EXISTS idx_users_marketing_consent
    ON users (id) WHERE marketing_consent;
