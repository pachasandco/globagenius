-- 059_accept_longhaul_stopover_pref.sql
--
-- Per-user preference: accept long-haul flights WITH a stopover
-- (1 correspondence) or not. 2026-07-01.
--
-- Context: a bug (fixed same day) rejected 100% of multi-stop fares
-- because haul type was read from duration_minutes (always 0 on
-- multi-stop entries) → CDG→Sydney -55% and every other long-haul
-- deal with a connection was silently dropped. Now that the pipeline
-- can qualify them, whether to PUSH them is a user choice.
--
-- Scope: LONG-HAUL ONLY. Europe/short-haul stays direct-only for
-- everyone regardless of this flag (founder rule, non-negotiable).
--
-- Default TRUE (opt-out): existing users and new signups receive
-- long-haul-with-stopover deals unless they explicitly turn it off.
-- Maximises "never miss a deal"; a Sydney at half price is worth a
-- connection for most travellers.

ALTER TABLE user_preferences
  ADD COLUMN IF NOT EXISTS accept_longhaul_stopover boolean NOT NULL DEFAULT true;
