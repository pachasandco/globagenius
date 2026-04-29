"""Single source of truth for pipeline numeric thresholds.

Before V5 these were scattered across config.py, jobs.py, routes.py,
baselines.py, dedup.py and split_ticket_matcher.py. Some were even
duplicated (GLOBAL_MIN_DISCOUNT in jobs.py AND routes.py).

Each constant lives in exactly ONE place. To tune a threshold:
  1. Edit it here.
  2. Update the comment above it explaining the new value.
  3. Run the tests + grep the codebase to confirm no hard-coded
     duplicate has been re-introduced.

Future evolution: when an A/B testing need appears, swap individual
constants for a DB-backed lookup (see roadmap P3). For now, plain
Python keeps the code grep-able and stack traces readable.
"""

# ─── Discount qualification ───

# Below this discount, no flight deal becomes a Telegram alert,
# regardless of z-score, score, or user tier. Anchors the global
# noise floor of the product.
GLOBAL_MIN_DISCOUNT_PCT = 40

# Free users see deals with discount in [GLOBAL_MIN, FREE_TIER_FULL_MAX]
# unlocked. Above FREE_TIER_FULL_MAX → masked teaser only.
FREE_TIER_FULL_MAX_DISCOUNT_PCT = 50


# ─── Tier quotas ───

# Maximum number of full-info Telegram alerts a free user can receive
# in a rolling 7-day window. Beyond that, they get a "limit reached"
# teaser once per week.
FREE_TIER_WEEKLY_LIMIT = 3


# ─── Baseline robustness ───

# Minimum number of price observations required before a baseline cell
# is usable for anomaly detection. Lowered from 10 → 5 to allow young
# seasonal sub-buckets (route × month × lead-time) to qualify deals.
MIN_BASELINE_SAMPLE_COUNT = 5


# ─── Dedup (Telegram alerts) ───

# How long after sending an alert we suppress re-alerts for the same
# (user, dest, dep_date, ret_date, price_bucket). 7 days = the natural
# cadence for "hey, this deal is still around" reminders without spam.
ALERT_INHIBIT_HOURS = 168

# Price granularity for the dedup key. A genuine new deal must cross a
# 50€ bucket boundary to re-alert. 89€ → 90€ same bucket (no spam),
# 89€ → 49€ different bucket (real drop, alerts).
ALERT_PRICE_BUCKET_EUR = 50


# ─── Split-ticket combo qualification ───

# A 2x one-way combo is only qualified if both:
#   - total ≤ roundtrip_baseline * (1 - SPLIT_SAVINGS_RATIO_FLOOR)
#   - savings ≥ SPLIT_SAVINGS_EUR_FLOOR
SPLIT_SAVINGS_RATIO_FLOOR = 0.15
SPLIT_SAVINGS_EUR_FLOOR = 100.0

# Stay length window — combos shorter than 4 days or longer than 30
# days don't match the round-trip baseline cell they're compared to.
SPLIT_MIN_STAY_DAYS = 4
SPLIT_MAX_STAY_DAYS = 30


# ─── One-way qualification (V5+ option C, pre-baseline) ───

# Until we have a mature one-way baseline (~4-6 weeks of data), we
# qualify one-way deals on raw discount vs the median price for the
# same (origin, destination, direction) over the last N days.
ONEWAY_DISCOUNT_PCT_FLOOR = 60
ONEWAY_MEDIAN_LOOKBACK_DAYS = 30
ONEWAY_MIN_OBSERVATIONS = 5
