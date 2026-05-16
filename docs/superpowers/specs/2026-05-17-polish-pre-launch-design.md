# Polish pre-launch — design

**Branch:** `polish-pre-launch`
**Date:** 2026-05-17
**Status:** Design approved, awaiting implementation plan

## Why

Three technical debts identified during the 2026-05-16 audit bias every
downstream decision we make on the product:

1. **No temporal smoothing of alerts** — the pooled 5/24h cap lets a user
   wake up to 4 notifications between 00h and 04h (observed: user
   889be488 on 2026-05-16). The cap is respected but perception is spam.
2. **Duplicate rows for a single Telegram message** — a grouped alert
   with N offers writes N rows to `sent_alerts` with different
   `alert_key`s but the same `created_at`. This pollutes CTR, baseline
   maturity scoring, and the L2 cap logic, which all rely on a 5-minute
   bucket workaround.
3. **Baseline maturity ETA is conceptually wrong** — the 82-day ETA
   assumes uniform sample distribution across all baselines. Reality:
   72% of samples concentrate on 5 Spain destinations. Long-haul
   baselines (Tokyo, Bangkok) acquire ~0 samples/day. The global score
   never improves on cold-tail routes.

These three fixes precede everything else in the backlog (admin health
endpoint, feedback buttons, article auto-regen) because they condition
the *quality* of what those future features would measure.

## Scope

Three independent chantiers. The chantier numbers below match the
section headings further down (chantiers 1, 2, 3 below correspond
literally to "Chantier 1", "Chantier 2", "Chantier 3" in the rest of
this document). The implementation **order** is different from the
numbering — see the "Sequencing" section at the end.

- **Chantier 1 — `message_id` on `sent_alerts`** (1 day) — foundation
  for clean metrics.
- **Chantier 2 — Cluster-based baseline maturity** (1-2 days) —
  autonomous, only depends on DB.
- **Chantier 3 — Anti-burst Levier 3** (1-2 days) — touches the
  dispatcher hot path.

Total dev effort: 3-5 days. Implementation order: **1 → 2 → 3**
(`message_id` first as the foundation, anti-burst last because it
modifies the dispatcher hot path).

Deferred (kept as ROADMAP entries):

- **Reinstate exceptional-discount bypass on L2** at ~100 active users
  or ~2026-08, whichever comes first. Today's reverification at ~95%
  makes the bypass redundant; at scale, a P→NRT at 280€ landing as the
  4th alert should pass.
- **Admin `/api/admin/messages?user_id=X` endpoint** — 1h follow-up
  that exploits the new `message_id` field. Without it, the migration
  serves only the L2 logic.
- **Snapshot table for baseline maturity deltas** — added in v2 when
  we have 4+ weekly runs to compare against.

## Chantier 1 — `message_id` on `sent_alerts`

### Problem

A grouped Telegram alert with N offers writes N rows to `sent_alerts`,
each with a distinct `alert_key` (so the 168h dedup can match each
future re-emission) but the same `created_at`. Consequences:

- CTR is computed against row count, inflating the denominator.
- L2 cap counts rows, not messages, so a 3-offer message saturates the
  3/day cap by itself. Current workaround: a 5-minute bucket dedup in
  `levier_2_daily_cap_blocks` — accurate enough but fragile.
- Baseline maturity reports, feedback button proposals, and any future
  per-message analytics inherit the same bias.

### Design

A single UUID column `sent_alerts.message_id`, shared by all N rows of
one Telegram message, generated Python-side before insert.

#### Migration 039

```sql
ALTER TABLE sent_alerts
  ADD COLUMN IF NOT EXISTS message_id uuid;
CREATE INDEX IF NOT EXISTS idx_sent_alerts_message_id
  ON sent_alerts(message_id);
```

Idempotent. The existing unique index `(user_id, alert_key)` is
preserved — it serves the 168h offer-level dedup, which is orthogonal
to message-level grouping.

#### Backfill — `scripts/backfill_message_id.py`

**Dry-run first.** Before mutating prod, the script produces a CSV
report with:

- Number of detected groups
- Distribution of rows-per-group (1, 2, 3, 4+)
- "Suspect" groups with >10 rows flagged for manual review

Operator runs the dry-run, reviews the CSV. If the distribution is
healthy (median 1-3 rows/group, no group with 50+ rows), runs the
backfill. Otherwise investigates first.

**Backfill logic** when greenlit:

```python
# Group rows missing message_id by (user_id, destination, created_at-to-second)
# - destination is in the key because two simultaneous messages to
#   different destinations are distinct events.
# - created_at to the second handles microsecond-different rows from
#   the same upsert batch.
# - user_id is implicit (no cross-user grouping).

# Process in batches of 500, COMMIT each batch.
# WHERE message_id IS NULL is idempotent: a crashed run resumes naturally.
# No global transaction — losing one batch is acceptable, losing 3200 isn't.
```

#### Application code

Three call sites in `app/scheduler/jobs.py` (lines ~1170, ~1866,
~2125) currently build a `rows` list and `upsert` it. Each is modified
to:

```python
import uuid
message_id = str(uuid.uuid4())
rows = [
    {..., "message_id": message_id}
    for k in keys_to_store
]
db.table("sent_alerts").upsert(rows, on_conflict="user_id,alert_key").execute()
```

**Invariant**: every new `sent_alerts` insert has `message_id IS NOT
NULL`. The only NULL rows are pre-migration historical ones.

#### Downstream updates

- **`dispatch_guards.py::levier_2_daily_cap_blocks`** — the bucket-5min
  dedup is kept as a fallback for rows where `message_id IS NULL`. When
  `message_id` is present, rows sharing it count as one event.
- **`baseline_maturity.py`** (chantier 3) — uses `message_id` where
  applicable for per-message counts.

#### One-month follow-up constraint

A month after deploy, when no NULL `message_id` rows should remain
(historical backfill + every new insert populating the field), add:

```sql
ALTER TABLE sent_alerts
  ADD CONSTRAINT message_id_required
  CHECK (message_id IS NOT NULL OR created_at < '2026-05-17');
```

This forces future code to respect the invariant.

### Tests

1. Insert one message with 3 offers → 3 rows with the same
   `message_id`.
2. Insert two distinct messages → two distinct `message_id`s.
3. Backfill script groups a fixture of 5 rows = 2 messages correctly.
4. Backfill is idempotent — second run on already-backfilled data
   changes nothing.
5. L2 cap uses `message_id` when present, falls back to the 5-min
   bucket otherwise.
6. **Cohérence post-backfill** — for every distinct `(user_id,
   destination, created_at-to-second)` in pre-migration rows, exactly
   one `message_id` exists after backfill.
7. **Mixed old/new in L2** — a user with 3 messages in the last 24h,
   1 NULL `message_id` (bucket-handled) + 2 with `message_id`, is
   counted as 3, not 4 or 6.

### Risks

- **Race during backfill** — scheduler inserts a new alert (with its
  own UUID) while backfill is running. Backfill query `WHERE
  message_id IS NULL` skips it. No collision.
- **False grouping in historical data** — two distinct messages to the
  same user, same destination, at the exact same second. The
  dry-run's "suspect" CSV catches this before it matters. Going
  forward, Python-side UUID generation removes the ambiguity.

## Chantier 2 — Cluster-based baseline maturity

### Problem

The current `baseline_maturity.py` reports a single score (39/100
today) and an ETA (82 days) derived from `(20 - median_samples) /
samples_per_day`. The formula assumes a uniform sample distribution
across baselines. In production, 72% of samples land on 5 Spain
destinations. Long-haul baselines never acquire enough samples at the
current rate. The global score is dominated by routes that already
work and demoralized by zombies that never will.

### Design

Classify each baseline into one of four clusters based on its current
sample count and its 7-day acquisition rate, then report per-cluster
counts and per-cluster ETAs.

#### Clustering

```python
def cluster_baseline(samples: int, rate_per_day: float) -> str:
    if samples >= 30:  return "hot"
    if samples >= 10:  return "warm"
    if rate_per_day > 0.1:  return "cold"      # will mature
    return "dormant"                            # zombie
```

Thresholds are the textbook ones (n≥30 = CLT comfortable, n≥10 =
z-score usable). Not invented in-house.

#### Sample-rate measurement

`rate_per_day` for a baseline `(origin, destination)`:

```sql
SELECT origin, destination, COUNT(*) as samples_7d
FROM raw_flights
WHERE scraped_at > NOW() - INTERVAL '7 days'
GROUP BY origin, destination;
```

One query, ~50-200 ms with the right index (see below). The result
is a `Dict[(origin, dest), int]` that the Python clustering loop
consults.

**Index required:**

```sql
CREATE INDEX IF NOT EXISTS idx_raw_flights_route_date
  ON raw_flights(origin, destination, scraped_at DESC);
```

The implementation plan checks for the index's existence via
`pg_indexes` in the first step of chantier 2; if absent, it ships
migration 040 with the `CREATE INDEX IF NOT EXISTS` above. The index
is idempotent so re-running the migration is safe.

#### Parsing `route_key`

Observed formats in `price_baselines.route_key`:

- `CDG-LIS-1m`
- `CDG-HKT-bucket_long`
- `*-HKT-bucket_medium`
- `CDG-HKT-bucket_long-m09-lt90p`

Parser:

```python
ROUTE_KEY_PATTERN = re.compile(r'^(?P<origin>[A-Z*]{3})-(?P<dest>[A-Z]{3})-.+$')

def parse_route_key(route_key: str) -> tuple[Optional[str], Optional[str]]:
    m = ROUTE_KEY_PATTERN.match(route_key)
    if not m:
        return None, None
    origin = m.group('origin')
    return (origin if origin != '*' else None), m.group('dest')
```

Wildcard handling for `*-XXX-...` baselines: the `rate_per_day` sums
all origins toward that destination:

```python
if origin is None:
    rate_per_day = sum(
        samples_count_dict.get((o, dest), 0)
        for o in known_origins
    ) / 7
else:
    rate_per_day = samples_count_dict.get((origin, dest), 0) / 7
```

`known_origins` is the set of distinct origins observed in
`raw_flights` over the same 7-day window.

Parse failures (unknown format) → log WARNING, classify as
`"unknown"`, aggregate with `cold` in the report. Tracked in the
diagnostic line below so a sudden surge of unknowns is visible.

#### Headline score

`mature_coverage_pct = (hot + warm) / (hot + warm + cold)`. Dormants
are excluded from the denominator — they are zombies, not failing
baselines, and have no place in the maturity number.

Estimated for current data: 162 hot + 487 warm + 542 cold + 1123
dormant → `649 / 1191 = 54%`. Much more legible than 39/100.

#### Telegram report format (≤12 lines)

```
🟡 Couverture mature : 54%

  🟢 Hot     162  (14%)  ≥30 samples
  🟡 Warm    487  (41%)  10-29 samples
  🟠 Cold    542  (45%)  ETA warm: 45j (médiane)
  🔴 Dormant 1123       → CSV envoyé

samples/baseline/jour (méd) : 0.17

📊 Saison scheduler actuelle : spring
⚠️ Parsing route_key : 2310/2314 OK, 4 unknown
```

No `+X vs S-1` delta in v1 — that requires a snapshot table, deferred
to v2 once we have 4+ weekly runs.

#### Dormant CSV (monthly)

New cron `job_monthly_dormant_baselines_csv` (1st of month, 09:30)
generates a CSV with columns:

- `route_key`
- `sample_count`
- `last_scrape_at`
- `rate_per_day_7d`
- `last_seen_in_season` — current scheduler season; tells operator
  whether the dormant is a real zombie or an off-season route that
  will revive in summer/autumn rotation

Uploaded to Supabase storage (private bucket). Admin Telegram message
includes the signed URL.

### Tests

1. `parse_route_key` on four formats: `CDG-LIS-1m`, `*-HKT-bucket_long`,
   `CDG-HKT-bucket_long-m09-lt90p`, `MALFORMED` → OK / wildcard / OK /
   unknown.
2. `cluster_baseline`: samples=35 → hot, samples=15 → warm, samples=5
   with rate=0.5 → cold, samples=5 with rate=0.05 → dormant.
3. Wildcard origin: `*-HKT-bucket_long` aggregates samples from all
   origins toward HKT.
4. Edge case `rate_per_day == 0.1` exact: must classify as cold
   (strictly `> 0.1` → cold; `≤ 0.1` → dormant). Test at 0.099 and
   0.101.
5. `mature_coverage_pct` excludes dormants: (100 hot, 100 warm, 100
   cold, 100 dormant) → 200/300 = 66.7%, not 50%.
6. Dormant CSV generation produces a valid file with all expected
   columns including `last_seen_in_season`.
7. Telegram report fits in ≤12 lines (regex `re.fullmatch`) and
   includes the four cluster rows + season + parsing-diagnostic
   lines.

### Risks

- **New `route_key` format introduced** → parsing falls back to
  unknown. The diagnostic line `2310/2314 OK, 4 unknown` makes this
  observable immediately.
- **Query cost on 7-day window** → mitigated by the new compound
  index; 367 distinct routes × 14k flights/day on 7 days = ~98k rows
  to scan, completes in <200 ms.
- **Seasonality confounds the "dormant" label** in May before the
  summer rotation. `last_seen_in_season` in the CSV gives the
  operator the context to keep or purge.

## Chantier 3 — Anti-burst Levier 3

### Problem

A user receiving 4 notifications between 00h and 04h experiences spam
even when the pool cap is respected. Observed: 889be488 on 2026-05-16
(RAK 00:22, SPU 02:05, CMN 02:09, PTP 04:08). Smoothing perception
matters more than reducing volume.

### Design

A new dispatch guard `levier_3_burst_blocks`, applied **before** L2 in
the dispatcher pipeline.

#### Rule

For a candidate alert at time `now` for `(user_id, destination,
new_discount_pct)`:

1. Lookup the most recent `sent_alerts` row for this user in the last
   3 hours (alert_types `flight`, `one_way`, `split_ticket`).
2. If no row found → pass.
3. If a row exists, evaluate the exception threshold:
   - **Long-haul candidate** (per `is_long_haul(destination)`):
     pass if `new_discount_pct >= 60`.
   - **Short-haul candidate**: pass if `new_discount_pct >= 70`.
4. Otherwise → block.

The `is_long_haul` function is the one already used in L2 (imported
from `app.analysis.route_selector`). Coherence with L2 is the goal —
a single source of truth for "what counts as long-haul" across the
whole guard stack.

#### Treatment of `split_ticket`

A split-ticket message is a single Telegram notification (two one-way
segments shown in one message). It consumes one burst slot like any
other alert. The current `sent_alerts` schema writes one row per
alert_type=`split_ticket` send (verified), so the burst lookup
naturally counts it as one event.

#### Pending in-run alerts

The dispatcher's in-run pending list — alerts already sent to this
user earlier in the current dispatch tick but not yet flushed to DB —
must also count against burst. To avoid double-counting on retries,
this is stored as `Dict[user_id, datetime]` (most recent ts per
user), not a list of timestamps.

#### Ordering in the dispatcher

```
L1 (destination cooldown 7d)
  → L3 (burst 3h)              ← NEW, cheapest query (LIMIT 1)
    → L2 (pool 5/24h)
      → send_telegram
```

L3 is cheaper than L2 (single-row lookup vs 24h window scan), so
putting it second after L1 saves a query when burst blocks.

### Tests

1. No burst in window → pass.
2. Burst recent + short-haul discount <70% → block.
3. Burst recent + short-haul discount ≥70% → pass.
4. Burst recent + long-haul discount ≥60% (e.g. 65% to NRT) → pass.
5. Burst recent + long-haul discount <60% (e.g. 50% to NRT) → block.
6. **Boundary** — burst at T-2h59 blocks; burst at T-3h01 passes.
7. **User isolation** — recent burst for user A does not block user B.

### Backtest gate

Before merging chantier 3, replay the last 14 days of `sent_alerts`
through a simulator that applies L3 + the existing L2 and L1 logic.
Pass criteria:

1. **<20% additional alerts blocked** beyond what L2 already blocks.
2. **No alert with `discount_pct ≥ 70%` (short) or `≥ 60%` (long)
   would be blocked** — proves the exception threshold works.
3. **Identified bursts visibly broken** — Moussa's 4-alert window on
   2026-05-15 (00h-04h) is reduced to 1 alert + 3 blocked. Attribution
   in the simulator output must distinguish "blocked by L3 burst" from
   "blocked by L2 pool" (the latter should not be re-attributed to
   L3 in the analysis).

The 20% headroom (vs the 15% in the original proposal) is intentional
slack for an early-stage product where we'd rather over-block than
spam.

### Risks

- **Legitimate spaced-out chains blocked** — a user actively browsing
  a destination at 11h, 14h, 17h could see the 14h alert blocked. The
  exception threshold handles the truly exceptional case; the
  remaining is by design (the 14h alert lives in `qualified_items`
  and surfaces on `/home`).
- **Edge case: first alert ever for a user** — no row in `sent_alerts`
  in 3h → L3 passes. No special case needed.

## Sequencing

Implementation order:

1. **Chantier 1** (`message_id`) — foundation. After merge, L2 and the
   maturity report read clean data.
2. **Chantier 2** (cluster maturity) — autonomous, reads
   `price_baselines` and `raw_flights`.
3. **Chantier 3** (L3 anti-burst) — touches the dispatcher hot path,
   merged last after chantiers 1 and 2 are stable in prod.

Each chantier ships as one PR. Backtest gates before merge. No
combined PR.

## Out of scope

The following are explicitly deferred:

- Health endpoint `/api/admin/health` — relies on clean metrics, which
  these chantiers establish. Schedule after this sprint.
- Feedback buttons on Telegram alerts — useful only at higher user
  count; current 6 active recipients (early-onboarding contacts)
  produce no actionable signal.
- Articles auto-generation pipeline fix — anthropic credit reload
  during the prior session restored generation; the deferred batch
  for 7 remaining destinations runs after this sprint.
- Stopover detection via `flight_search v1` — blocked on
  Travelpayouts partner access request (sent 2026-05-13).
- Reinstating the L2 exceptional bypass — revisit at ~100 active
  users or 2026-08, whichever first. TODO comment added in
  `dispatch_guards.py` and a line in `ROADMAP.md` Deferred section.
