-- 065_users_auth_columns_drift.sql
--
-- Découvert 2026-07-31, en prod : PERSONNE ne pouvait plus se connecter
-- après la migration de projet Supabase. Cause : users.password_hash et
-- user_preferences.telegram_connect_token avaient été ajoutées À LA MAIN
-- dans l'ancienne base, sans migration. Le rejeu des migrations sur le
-- nouveau projet a donc créé les tables SANS ces colonnes, et l'import a
-- silencieusement ignoré les valeurs (l'importeur filtre sur les
-- colonnes du schéma cible).
--
-- 5e occurrence de la classe « schéma modifié hors migration » (cf.
-- sent_alerts 054/060, raw_flights 061, onboarding_email_log 063) — et
-- la plus grave : elle a cassé l'authentification de tous les comptes.
--
-- Le backfill des valeurs se fait hors migration (depuis l'export de la
-- migration de projet) ; ce fichier ne codifie que le schéma.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_hash varchar;

ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS telegram_connect_token text;
