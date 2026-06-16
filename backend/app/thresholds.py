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

# Long-haul push floor (2026-06-13). Long-haul fares move on tight
# yield management, so genuine −40% errors are rare (≈ a handful/month).
# But the EUR saving dwarfs short-haul: −30% on a 427€ CDG→New York is
# ~180€ off, far more actionable than −40% on a 50€ BVA→Lisbonne. So
# long-haul (is_long_haul(destination)) pushes at a lower bar. Applied
# at DISPATCH only and as a FLOOR override: a premium user who
# explicitly picked a higher min_discount keeps it (we never push them
# something below THEIR chosen bar) — this only lowers the default 40.
# Founder decision: 30%.
LONG_HAUL_MIN_DISCOUNT_PCT = 30

# ─── BVA Europe floor (2026-06-09; validated by the 48h audit of
# 2026-06-12: no user exceeded 6 messages/day over 5 days, so no
# further tightening is needed) ───────────────────────────────────────
# Beauvais is a Ryanair hub: 25-40€ A/R on BVA→Med (LIS/BCN/AGP/NAP)
# is the NORMAL price there, not a deal, and BVA produces the densest
# (and noisiest) qualified-deal flow of all origins. Short-haul alerts
# from BVA therefore need a higher bar than the global 40% floor.
# Applied at DISPATCH time only (Telegram push) — the deal stays in
# qualified_items and visible on /home, consistent with how L1/L2/L3
# treat blocked deals. Other origins (LYS, MRS, BOD, NTE, TLS, CDG,
# ORY) keep GLOBAL_MIN_DISCOUNT_PCT — their deal flow is thinner.
# Long-haul from BVA (rare) is NOT tightened.
BVA_EUROPE_MIN_DISCOUNT_PCT = 50

# Pépite price bar for BVA short-haul. The generic pépite override
# (≤30€ A/R) would bypass the floor above on virtually every Ryanair
# sale fare — 25-30€ is Beauvais's everyday price floor, not a "wow".
# A true BVA pépite must be ≤15€ A/R (or clear the generic ≥75%
# discount bar, which still applies unchanged).
BVA_PEPITE_PRICE_THRESHOLD_EUR = 15.0

# ─── V9 Free tier policy ───
#
# Free users always get one A/R per day in the [20%, 40%) band — the
# product's "regular value" proof. They additionally get one A/R at
# >=40% per week — the "wow" proof.
# No FULL one-way / split-ticket combos, no quota beyond these.
# (Additive since the locked-teaser feature: free users ALSO get a
#  blurred, non-actionable teaser of EXCEPTIONAL premium deals — see
#  LONG_HAUL_TEASER_MIN_DISCOUNT_PCT / ONEWAY_TEASER_MAX_PRICE_EUR below.
#  That lane is teaser-only and never gives away destination/dates/link,
#  so it does not change the bands above.)
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


# ─── Dispatch stay-length floor ───

# Minimum nights for a round-trip to be PUSHED (Telegram).
# PRODUCT RULE (founder, 2026-06-12, non-negotiable): trips under 4
# nights must NOT alert — short-stay fares are so frequent that pushing
# them would flood users. Deals under the floor still qualify and stay
# visible on /home; only the push is suppressed, and the drop is
# counted as `min_stay` in the dispatch summary line so the volume
# discarded by this rule stays measurable.
# History: this was a hardcoded `4` buried in the dispatcher since
# 2026-04-20 with no log/counter — the 2026-06-12 "ghost deal" audit
# spent hours rediscovering it. Centralised + counted that day; the
# threshold itself was briefly lowered to 2 and immediately reverted
# to 4 on founder decision.
MIN_STAY_NIGHTS = 4

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


# ─── Stopover chain qualification (phase 1, 2026-06-09) ───

# A stopover chain is 3 one-way tickets: origin → hub (a few days),
# hub → final destination, destination → origin. Compared against the
# round-trip baseline for origin → destination DIRECT. The bar is lower
# than the split-ticket 40%/100€ on purpose: the chain includes a bonus
# second destination, so "cheaper than the direct A/R at all" is already
# a strong story — 30% under the direct baseline is a clear win.
STOPOVER_SAVINGS_RATIO_FLOOR = 0.30
STOPOVER_SAVINGS_EUR_FLOOR = 80.0

# Stay-shape constraints. The hub visit must be a real city stop
# (2-5 days, not an airport transfer) and the whole trip must stay
# comparable to the round-trip baseline cell it's measured against.
STOPOVER_MIN_HUB_DAYS = 2
STOPOVER_MAX_HUB_DAYS = 5
STOPOVER_MIN_DEST_DAYS = 3
STOPOVER_MAX_TOTAL_DAYS = 30


# ─── One-way qualification (V5+ option C, pre-baseline) ───

# Until we have a mature one-way baseline (~4-6 weeks of data), we
# qualify one-way deals on raw discount vs the median price for the
# same (origin, destination, direction) over the last N days.
ONEWAY_DISCOUNT_PCT_FLOOR = 60
ONEWAY_MEDIAN_LOOKBACK_DAYS = 30
ONEWAY_MIN_OBSERVATIONS = 5

# ─── One-way Telegram push gate (2026-06-07) ───
#
# A one-way fare only solves a problem when the user already needs to
# be in city X on date Y. For a generic user without that constraint,
# a one-way alert is noise — they can't act on it. Product call: we
# qualify every one-way deal (so it appears on /home and feeds
# analytics), but we ONLY push a Telegram notification when it's
# striking enough to function as an impulse-buy "wow" — a true price
# anomaly someone might book just because it exists.
#
# A one-way Telegram push fires iff:
#   - absolute price ≤ ONEWAY_PUSH_WOW_PRICE_EUR (20€), OR
#   - discount ≥ ONEWAY_PUSH_WOW_DISCOUNT_PCT (80%)
#
# Note: these are stricter than the L1/L2/L3 pépite thresholds
# (≤30€ OR ≥75%) on purpose — round-trip pépites still ride the
# qualifier-default rules, one-way pépites need to clear a higher bar
# because the user-action friction is much higher.
ONEWAY_PUSH_WOW_PRICE_EUR = 20.0
ONEWAY_PUSH_WOW_DISCOUNT_PCT = 80.0

# ── Locked teaser (FREE-tier blurred teaser of EXCEPTIONAL premium deals) ──
# A free user gets a blurred teaser (type + % + coarse price, no
# destination/dates/link) only for deals rare enough that the rarity itself
# is the frequency throttle:
#   - long-haul round-trip with discount ≥ LONG_HAUL_TEASER_MIN_DISCOUNT_PCT
#   - one-way with price ≤ ONEWAY_TEASER_MAX_PRICE_EUR
#   - any qualified split-ticket combo (already exceptional by construction)
LONG_HAUL_TEASER_MIN_DISCOUNT_PCT = 30
ONEWAY_TEASER_MAX_PRICE_EUR = 20.0
