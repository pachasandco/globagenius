"""Single source of truth for GlobeGenius pipeline thresholds.

Keep numeric product rules here so qualification, dispatch and API responses do
not drift. Freemium rolling-window enforcement is completed by
``app.freemium_policy`` immediately before a Telegram send.
"""

# ─── Discount qualification ────────────────────────────────────────────────
GLOBAL_MIN_DISCOUNT_PCT = 40
LONG_HAUL_MIN_DISCOUNT_PCT = 30

# Beauvais has an unusually low normal fare floor and therefore needs a
# stricter short-haul qualification threshold.
BVA_EUROPE_MIN_DISCOUNT_PCT = 50
BVA_PEPITE_PRICE_THRESHOLD_EUR = 15.0

# ─── Freemium policy ───────────────────────────────────────────────────────
# Complete free alerts are round-trip only. The scheduler splits candidates
# into two lanes; the final entitlement guard applies the rolling windows:
#   - regular [20%, 50%): 2 complete alerts per rolling 7 days
#   - exceptional >=50% : 1 complete alert per rolling 30 days
# One-way and split-ticket full alerts remain Premium-only. Exceptional Premium
# opportunities may still be shown as locked teasers.
FREE_TIER_DAILY_BAND_MIN_PCT = 20
FREE_TIER_DAILY_BAND_MAX_PCT = 50
FREE_TIER_WEEKLY_BIG_MIN_PCT = 50

# These values cap a single dispatch pass and the historical scheduler lanes.
# The independent Freemium guard extends their effective windows to 7/30 days.
FREE_TIER_DAILY_LIMIT = 2
FREE_TIER_WEEKLY_BIG_LIMIT = 1

# One explicit joker per month. The dedicated Freemium API records consumption
# with a ``funlock:`` sent_alerts key.
FREE_TIER_HOMEPAGE_UNLOCK_LIMIT = 1

# ─── Premium discount filter ───────────────────────────────────────────────
PREMIUM_MIN_DISCOUNT_CHOICES = (40, 50, 60)
PREMIUM_DEFAULT_MIN_DISCOUNT = 40

# ─── Baseline robustness ───────────────────────────────────────────────────
MIN_BASELINE_SAMPLE_COUNT = 5
PRICE_HISTORY_WINDOW_DAYS = 60

# ─── Dispatch controls ─────────────────────────────────────────────────────
MIN_STAY_NIGHTS = 4
ALERT_INHIBIT_HOURS = 168
ALERT_PRICE_BUCKET_EUR = 50

# ─── Split-ticket qualification ────────────────────────────────────────────
SPLIT_SAVINGS_RATIO_FLOOR = 0.40
SPLIT_SAVINGS_EUR_FLOOR = 100.0
SPLIT_MIN_STAY_DAYS = 4
SPLIT_MAX_STAY_DAYS = 30

# ─── Stopover chains ───────────────────────────────────────────────────────
# Kept disabled after the July 2026 economic validation showed that assembling
# three separate tickets usually costs more than a direct round trip.
STOPOVER_ENABLED = False
STOPOVER_SAVINGS_RATIO_FLOOR = 0.30
STOPOVER_SAVINGS_EUR_FLOOR = 80.0
STOPOVER_MIN_HUB_DAYS = 2
STOPOVER_MAX_HUB_DAYS = 5
STOPOVER_MIN_DEST_DAYS = 3
STOPOVER_MAX_TOTAL_DAYS = 30

# ─── One-way qualification and push gate ──────────────────────────────────
ONEWAY_DISCOUNT_PCT_FLOOR = 60
ONEWAY_MEDIAN_LOOKBACK_DAYS = 30
ONEWAY_MIN_OBSERVATIONS = 5
ONEWAY_PUSH_WOW_PRICE_EUR = 20.0
ONEWAY_PUSH_WOW_DISCOUNT_PCT = 80.0

# ─── Locked Premium teasers for free users ────────────────────────────────
LONG_HAUL_TEASER_MIN_DISCOUNT_PCT = 30
ONEWAY_TEASER_MAX_PRICE_EUR = 20.0
# 2026-08-03 : plafond quotidien par user. Sans plafond, l'ouverture du
# long-courrier (séjours 21j + 13 destinations) a fait qualifier assez de
# deals « exceptionnels » pour envoyer 11 teasers/user/jour en médiane
# (353/24h mesurés) — de la pression de conversion devenue du spam qui
# mène au mute Telegram. 1/jour = le teaser reste rare donc précieux,
# tout en gardant ~30 rappels Premium par mois.
FREE_TEASER_DAILY_LIMIT = 1
