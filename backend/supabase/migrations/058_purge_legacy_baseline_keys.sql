-- 058_purge_legacy_baseline_keys.sql
--
-- One-shot cleanup of fossil price_baselines rows (2026-06-19).
--
-- The qualifier reads ONLY bucket-format keys
-- (e.g. "CDG-LIS-bucket_medium-m10-lt90p"). Two older key formats still
-- linger in the table from past schema versions:
--   - "CDG-LIS-1m" / "-3m" / "-6m"  (V3 month-only keys)
--   - bare "CDG-FCO"                 (even older, no duration)
-- The nightly recalc only ever writes bucket_* keys, so these fossils
-- are never refreshed — they sit ~70 days stale forever and inflated the
-- "baselines périmées" admin alert to a false 22% (≈235 of 4285 rows).
-- They qualify zero deals and waste the watchdog's attention.
--
-- Safe to delete: nothing reads them. Verified count on 2026-06-19:
-- 4285 flight baselines, 4050 bucket_* (kept), 235 fossils (deleted).
-- The watchdog itself was also scoped to bucket_* in the same change.

DELETE FROM price_baselines
WHERE type = 'flight'
  AND route_key NOT LIKE '%bucket_%';
