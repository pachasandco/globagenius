-- 061_raw_flights_trip_type_underscore.sql
--
-- Découvert lors de la migration de projet Supabase (2026-07-30) : la
-- contrainte définie par les migrations acceptait ('roundtrip','oneway')
-- mais le code écrit depuis toujours 'round_trip' / 'one_way' (2,16M
-- lignes en prod). L'ancienne base avait été corrigée À LA MAIN sans
-- migration — le rejeu des migrations sur un projet neuf recréait donc
-- la contrainte périmée et rejetait toutes les lignes. Même classe de
-- drift que la saga sent_alerts_alert_type_check (054/055/060).

ALTER TABLE raw_flights
    DROP CONSTRAINT IF EXISTS raw_flights_trip_type_check;

ALTER TABLE raw_flights
    ADD CONSTRAINT raw_flights_trip_type_check
    CHECK (trip_type IN ('round_trip', 'one_way'));
