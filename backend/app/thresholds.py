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

# Anchors the global noise floor for *premium* alerts. Anything below
# this is never an alert for a premium user, regardless of which
# min_discount they picked in their profile.
# (V9: free users now have their own narrower band — see below — so
# this constant only governs the premium pipeline.)
GLOBAL_MIN_DISCOUNT_PCT = 40

# ─── V9 Free tier policy ───
#
# Free users always get one A/R per day in the [20%, 40%) band — the
# product's "regular value" proof. They additionally get one A/R at
# >=40% per week — the "wow" proof.
# No one-way, no split-ticket combos, no teasers, no quota beyond these.
FREE_TIER_DAILY_BAND_MIN_PCT = 20      # inclusive
FREE_TIER_DAILY_BAND_MAX_PCT = 40      # exclusive
FREE_TIER_WEEKLY_BIG_MIN_PCT = 40      # inclusive — the "≥40% once a week" lane

# Daily and weekly caps for the free tier. Strict — we never exceed.
FREE_TIER_DAILY_LIMIT = 1              # one regular deal per UTC day
FREE_TIER_WEEKLY_BIG_LIMIT = 1         # one big deal per rolling 7d

# How many deals a free user may unlock (full price + booking link) on the
# homepage per rolling 7d. Independent from the Telegram cadence so the
# homepage doesn't have to wait for a Telegram alert to surface a deal.
# Kept at the legacy value (3) — generous enough to give the user a feel
# for the product without giving away the whole catalogue.
FREE_TIER_HOMEPAGE_UNLOCK_LIMIT = 3

# ─── V9 Premium discount filter ───
#
# Premium users pick their own discount floor in profile. Stored in
# user_preferences.min_discount; only these three values are valid.
# Default for new premium signups is the lowest (40%).
PREMIUM_MIN_DISCOUNT_CHOICES = (40, 50, 60)
PREMIUM_DEFAULT_MIN_DISCOUNT = 40


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
# Aligned with the global 40% promise — anything weaker is sub-product.
SPLIT_SAVINGS_RATIO_FLOOR = 0.40
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
