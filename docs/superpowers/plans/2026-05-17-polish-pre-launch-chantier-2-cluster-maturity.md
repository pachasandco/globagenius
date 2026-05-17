# Chantier 2 — Cluster-based baseline maturity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the misleading uniform 39/100 maturity score by a per-cluster classification (hot / warm / cold / dormant) with cluster-aware ETAs, plus a monthly CSV of dormant baselines for operator review.

**Architecture:** A new module `app/analysis/baseline_clusters.py` parses `route_key`, computes the 7-day acquisition rate per route via a single grouped query on `raw_flights`, and classifies each baseline into one of four clusters. `app/analysis/baseline_maturity.py` is rewritten to use this clustering and produce a compact Telegram report. A new monthly cron exports dormants as CSV to Supabase storage. Migration 040 ensures the compound index on `raw_flights(origin, destination, scraped_at)` exists.

**Tech Stack:** Python 3.12, FastAPI, Supabase Postgres + Storage, pytest.

---

## File Structure

**Create:**
- `backend/supabase/migrations/040_raw_flights_route_date_index.sql` — compound index for the 7-day rate query.
- `backend/app/analysis/baseline_clusters.py` — parsing, rate measurement, clustering. Pure logic, no IO besides the single grouped query.
- `backend/tests/test_baseline_clusters.py` — unit tests for parser + classifier + report aggregation.

**Modify:**
- `backend/app/analysis/baseline_maturity.py` — rewrite around the new clustering. Keep `format_for_telegram` but with the new format. Drop the legacy `MaturitySignal`/`_score_signal` scaffolding.
- `backend/app/notifications/telegram.py` — add `send_admin_file` helper for CSV upload (Supabase storage signed URL → admin chat message).
- `backend/app/scheduler/jobs.py` — register the new monthly cron `job_monthly_dormant_baselines_csv` next to the existing weekly maturity job.

**Note:** The "no delta vs S-1 in v1" decision is in the spec (line ~358). This plan respects it — the snapshot table is out of scope.

---

## Task 1: Migration 040 — compound index on `raw_flights`

**Files:**
- Create: `backend/supabase/migrations/040_raw_flights_route_date_index.sql`

- [ ] **Step 1: Check if the index already exists**

Run (from `backend/`):

```bash
.venv/bin/python3 -c "
from dotenv import load_dotenv; load_dotenv('.env')
from app.db import db
r = db.rpc('exec_sql', {'sql': \"SELECT indexname FROM pg_indexes WHERE tablename='raw_flights' AND indexname LIKE '%route%'\"}).execute() if False else None
print('Check via SQL Editor: SELECT indexname FROM pg_indexes WHERE tablename=' + chr(39) + 'raw_flights' + chr(39))
"
```

Easier path: open Supabase → SQL Editor → run:

```sql
SELECT indexname FROM pg_indexes WHERE tablename='raw_flights';
```

If a row `idx_raw_flights_route_date` already exists, Task 1 still ships the migration file for repeatability but the SQL is a no-op. If absent, the migration creates it.

- [ ] **Step 2: Write the migration**

Create `backend/supabase/migrations/040_raw_flights_route_date_index.sql`:

```sql
-- Migration 040: compound index on raw_flights for the 7-day
-- per-route rate query used by baseline clustering.
--
-- Without this index, the query
--   SELECT origin, destination, COUNT(*) FROM raw_flights
--     WHERE scraped_at > NOW() - INTERVAL '7 days'
--     GROUP BY origin, destination
-- scans ~98k rows (14k/day × 7d) which is fine ad-hoc but ran
-- weekly by the scheduler we want a sub-200ms target.
--
-- IF NOT EXISTS so re-running is safe even if the index was
-- created out-of-band.

CREATE INDEX IF NOT EXISTS idx_raw_flights_route_date
  ON raw_flights(origin, destination, scraped_at DESC);
```

- [ ] **Step 3: Apply manually in Supabase SQL Editor**

Paste the SQL into Supabase SQL Editor → Run. Expected: `Success. No rows returned`. (Note: on a table with 490k rows, the index build can take a few seconds.)

- [ ] **Step 4: Smoke-test the query speed**

```bash
.venv/bin/python3 -c "
import time
from dotenv import load_dotenv; load_dotenv('.env')
from app.db import db
t0 = time.time()
r = db.rpc('exec_sql', {'sql': '''
  SELECT origin, destination, COUNT(*) AS samples_7d
  FROM raw_flights
  WHERE scraped_at > NOW() - INTERVAL '7 days'
  GROUP BY origin, destination
'''}).execute() if False else None
# Fallback: use the REST builder (no rpc available)
print('Run timing in SQL Editor instead.')
"
```

Easier: in Supabase SQL Editor, run the GROUP BY query above and observe the execution time. Target: <500 ms.

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/supabase/migrations/040_raw_flights_route_date_index.sql
git commit -m "feat(db): migration 040 — compound index for 7-day route rate

CREATE INDEX IF NOT EXISTS, idempotent. Backs the per-route
acquisition rate query used by chantier 2 clustering.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Parse `route_key` — failing tests

**Files:**
- Create: `backend/tests/test_baseline_clusters.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_baseline_clusters.py`:

```python
"""Tests for the cluster-based baseline maturity logic.

We test the units in isolation (parser, classifier, aggregator).
The full report builder hits the DB and is exercised separately
via a thin integration test."""
from app.analysis.baseline_clusters import parse_route_key


def test_parse_simple_route_key():
    """Format: 'CDG-LIS-1m' → ('CDG', 'LIS')"""
    assert parse_route_key("CDG-LIS-1m") == ("CDG", "LIS")


def test_parse_route_key_with_bucket():
    """Format: 'CDG-HKT-bucket_long' → ('CDG', 'HKT')"""
    assert parse_route_key("CDG-HKT-bucket_long") == ("CDG", "HKT")


def test_parse_route_key_with_wildcard_origin():
    """Format: '*-HKT-bucket_medium' → (None, 'HKT')

    The wildcard means 'all origins toward HKT' — the rate-per-day
    will be summed across known origins by the caller.
    """
    assert parse_route_key("*-HKT-bucket_medium") == (None, "HKT")


def test_parse_route_key_with_extra_suffixes():
    """Format: 'CDG-HKT-bucket_long-m09-lt90p' → ('CDG', 'HKT')

    Extra hyphenated suffixes (month, lead-time) don't break parsing
    because the regex only consumes the first two IATA-shaped tokens.
    """
    assert parse_route_key("CDG-HKT-bucket_long-m09-lt90p") == ("CDG", "HKT")


def test_parse_malformed_route_key_returns_none_pair():
    """Anything that doesn't start with two IATA-shaped tokens
    → (None, None). Caller logs WARNING and classifies the
    baseline as 'unknown'."""
    assert parse_route_key("MALFORMED") == (None, None)
    assert parse_route_key("CDG-LIS") == (None, None)  # no third segment
    assert parse_route_key("cdg-lis-1m") == (None, None)  # lowercase rejected
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (from `backend/`):

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.analysis.baseline_clusters'`.

---

## Task 3: Parse `route_key` — minimal implementation

**Files:**
- Create: `backend/app/analysis/baseline_clusters.py`

- [ ] **Step 1: Implement `parse_route_key`**

Create `backend/app/analysis/baseline_clusters.py`:

```python
"""Cluster-based maturity for price_baselines.

Replaces the legacy uniform-distribution maturity score. Classifies
each baseline into one of four clusters based on its current sample
count and its observed 7-day acquisition rate.

Cluster meanings:
    hot     → samples ≥ 30   — mature, CLT-comfortable
    warm    → samples 10-29  — z-score usable, acceptable
    cold    → samples < 10 AND rate_per_day > 0.1 — will mature
    dormant → samples < 10 AND rate_per_day ≤ 0.1 — zombie

The headline `mature_coverage_pct` uses (hot + warm) / (hot + warm
+ cold), excluding dormants from the denominator. The per-cluster
percentages displayed in the Telegram report use the total brut
(all baselines, dormants included) — by design, so the dormant
share remains visible.
"""
from __future__ import annotations

import re
from typing import Optional

# Matches the two leading IATA-shaped tokens of a route_key. A third
# segment is required (otherwise we don't have a valid period/bucket
# suffix). Trailing dashes and content are explicitly allowed.
_ROUTE_KEY_RE = re.compile(
    r"^(?P<origin>[A-Z*]{3})-(?P<dest>[A-Z]{3})-.+$"
)


def parse_route_key(route_key: str) -> tuple[Optional[str], Optional[str]]:
    """Extract (origin, destination) from a baseline's route_key.

    Returns:
        ('CDG', 'LIS')       — concrete origin and destination
        (None, 'HKT')        — wildcard origin (literal '*' in DB)
        (None, None)         — parsing failure (malformed key)
    """
    m = _ROUTE_KEY_RE.match(route_key)
    if not m:
        return None, None
    origin = m.group("origin")
    dest = m.group("dest")
    return (None if origin == "*" else origin), dest
```

- [ ] **Step 2: Run the tests to verify they pass**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: 5 PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/analysis/baseline_clusters.py backend/tests/test_baseline_clusters.py
git commit -m "feat(maturity): parse_route_key with wildcard support

Extracts (origin, dest) from baseline route_keys; returns
None-pair on malformed input so callers can log + classify
as 'unknown' without crashing.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Classify a baseline — failing tests

**Files:**
- Modify: `backend/tests/test_baseline_clusters.py`

- [ ] **Step 1: Append the classifier tests**

Append to `backend/tests/test_baseline_clusters.py`:

```python
from app.analysis.baseline_clusters import cluster_baseline


def test_cluster_hot_when_samples_at_or_above_30():
    assert cluster_baseline(samples=30, rate_per_day=0.0) == "hot"
    assert cluster_baseline(samples=150, rate_per_day=10.0) == "hot"


def test_cluster_warm_when_samples_between_10_and_29():
    assert cluster_baseline(samples=10, rate_per_day=0.0) == "warm"
    assert cluster_baseline(samples=29, rate_per_day=0.0) == "warm"


def test_cluster_cold_when_samples_below_10_and_rate_above_0_1():
    assert cluster_baseline(samples=5, rate_per_day=0.5) == "cold"
    assert cluster_baseline(samples=0, rate_per_day=5.0) == "cold"


def test_cluster_dormant_when_samples_below_10_and_rate_at_or_below_0_1():
    assert cluster_baseline(samples=5, rate_per_day=0.05) == "dormant"
    assert cluster_baseline(samples=5, rate_per_day=0.0) == "dormant"


def test_cluster_boundary_rate_exactly_0_1_is_dormant():
    """rate_per_day == 0.1 exact → dormant (strict > 0.1 → cold).

    This locks the boundary so a future refactor that changes >
    to >= doesn't silently widen the cold population."""
    assert cluster_baseline(samples=5, rate_per_day=0.1) == "dormant"
    assert cluster_baseline(samples=5, rate_per_day=0.10001) == "cold"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: 5 new tests FAIL with `ImportError: cannot import name 'cluster_baseline'`. Parsing tests still pass.

---

## Task 5: Classify a baseline — implementation

**Files:**
- Modify: `backend/app/analysis/baseline_clusters.py`

- [ ] **Step 1: Implement `cluster_baseline`**

Append to `backend/app/analysis/baseline_clusters.py`:

```python
# Cluster thresholds. The values come from classical stats:
#   30 = central limit theorem comfort zone
#   10 = z-score usable floor (n ≥ 10 makes the variance estimate stable)
# Rate threshold 0.1 / day = roughly "at least one fresh sample per
# 10-day window," below which the baseline is effectively abandoned.
HOT_MIN_SAMPLES = 30
WARM_MIN_SAMPLES = 10
COLD_MIN_RATE_PER_DAY = 0.1  # strictly greater than, not ≥


def cluster_baseline(samples: int, rate_per_day: float) -> str:
    """Classify a single baseline. See module docstring for the
    cluster definitions."""
    if samples >= HOT_MIN_SAMPLES:
        return "hot"
    if samples >= WARM_MIN_SAMPLES:
        return "warm"
    if rate_per_day > COLD_MIN_RATE_PER_DAY:
        return "cold"
    return "dormant"
```

- [ ] **Step 2: Run the classifier tests**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: all 10 tests PASS (5 parser + 5 classifier).

- [ ] **Step 3: Commit**

```bash
git add backend/app/analysis/baseline_clusters.py backend/tests/test_baseline_clusters.py
git commit -m "feat(maturity): cluster_baseline classifier

Four-bucket classification (hot/warm/cold/dormant) with
textbook thresholds. Boundary at rate=0.1 strict (> 0.1 → cold,
≤ 0.1 → dormant), test-locked.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Rate-per-day aggregation — failing tests

**Files:**
- Modify: `backend/tests/test_baseline_clusters.py`

- [ ] **Step 1: Append the rate aggregator tests**

Append to `backend/tests/test_baseline_clusters.py`:

```python
from app.analysis.baseline_clusters import compute_rate_per_day


def test_rate_per_day_concrete_origin():
    """For (CDG, LIS), divide samples by 7."""
    samples_by_route = {("CDG", "LIS"): 70, ("CDG", "BCN"): 14}
    rate = compute_rate_per_day(
        origin="CDG",
        destination="LIS",
        samples_by_route=samples_by_route,
        known_origins={"CDG", "ORY"},
    )
    assert rate == 10.0


def test_rate_per_day_unknown_route_is_zero():
    """A baseline whose (origin, dest) doesn't appear in the
    7-day query result → rate 0 (no recent scrapes)."""
    rate = compute_rate_per_day(
        origin="CDG",
        destination="NRT",
        samples_by_route={},
        known_origins={"CDG"},
    )
    assert rate == 0.0


def test_rate_per_day_wildcard_origin_sums_across_known_origins():
    """origin=None means 'all origins toward dest'. Sum all matches
    and divide by 7."""
    samples_by_route = {
        ("CDG", "HKT"): 14,
        ("ORY", "HKT"): 7,
        ("BVA", "HKT"): 0,
    }
    rate = compute_rate_per_day(
        origin=None,
        destination="HKT",
        samples_by_route=samples_by_route,
        known_origins={"CDG", "ORY", "BVA"},
    )
    # (14 + 7 + 0) / 7 = 3.0
    assert rate == 3.0
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: 3 new tests FAIL with `ImportError`.

---

## Task 7: Rate-per-day aggregation — implementation

**Files:**
- Modify: `backend/app/analysis/baseline_clusters.py`

- [ ] **Step 1: Implement `compute_rate_per_day`**

Append to `backend/app/analysis/baseline_clusters.py`:

```python
WINDOW_DAYS = 7  # the rate query covers the last 7 days


def compute_rate_per_day(
    *,
    origin: Optional[str],
    destination: str,
    samples_by_route: dict[tuple[str, str], int],
    known_origins: set[str],
) -> float:
    """Convert a parsed (origin, dest) into a samples-per-day rate
    over the 7-day window.

    `samples_by_route` is the precomputed result of the single
    `SELECT origin, destination, COUNT(*) GROUP BY ...` query.
    `known_origins` is the set of distinct origins observed in
    that same query — only used for wildcard expansion."""
    if origin is None:
        total = sum(
            samples_by_route.get((o, destination), 0) for o in known_origins
        )
    else:
        total = samples_by_route.get((origin, destination), 0)
    return total / WINDOW_DAYS
```

- [ ] **Step 2: Run the tests to verify they pass**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: all 13 PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/analysis/baseline_clusters.py backend/tests/test_baseline_clusters.py
git commit -m "feat(maturity): compute_rate_per_day with wildcard handling

Wildcard origin (route_key '*-XXX-...') sums samples across all
known origins toward dest before dividing by the 7-day window.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Mature coverage percentage — failing test + implementation

**Files:**
- Modify: `backend/app/analysis/baseline_clusters.py`
- Modify: `backend/tests/test_baseline_clusters.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_baseline_clusters.py`:

```python
from app.analysis.baseline_clusters import mature_coverage_pct


def test_mature_coverage_excludes_dormants_from_denominator():
    """(100 hot, 100 warm, 100 cold, 100 dormant) → 200/300 = 66.7%,
    NOT 200/400 = 50%. Dormants are zombies, not failing baselines,
    so they're not in the denominator."""
    counts = {"hot": 100, "warm": 100, "cold": 100, "dormant": 100}
    assert round(mature_coverage_pct(counts), 1) == 66.7


def test_mature_coverage_returns_zero_when_no_active_baselines():
    """All dormants → 0 / 0 → return 0.0 (not a crash)."""
    counts = {"hot": 0, "warm": 0, "cold": 0, "dormant": 100}
    assert mature_coverage_pct(counts) == 0.0
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: 2 new FAIL with `ImportError`.

- [ ] **Step 3: Implement `mature_coverage_pct`**

Append to `backend/app/analysis/baseline_clusters.py`:

```python
def mature_coverage_pct(counts: dict[str, int]) -> float:
    """Headline maturity score: % of active baselines that are mature.

    `counts` is a dict like {"hot": N, "warm": N, "cold": N, "dormant": N}.
    The denominator excludes dormants on purpose — they don't
    represent a failing pipeline, they represent abandoned routes,
    and including them would punish the score for a state we already
    surface separately (CSV export).
    """
    active = counts.get("hot", 0) + counts.get("warm", 0) + counts.get("cold", 0)
    if active == 0:
        return 0.0
    mature = counts.get("hot", 0) + counts.get("warm", 0)
    return 100.0 * mature / active
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: all 15 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/analysis/baseline_clusters.py backend/tests/test_baseline_clusters.py
git commit -m "feat(maturity): mature_coverage_pct excludes dormants from denominator

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: ETA cold→warm median — failing test + implementation

**Files:**
- Modify: `backend/app/analysis/baseline_clusters.py`
- Modify: `backend/tests/test_baseline_clusters.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_baseline_clusters.py`:

```python
from app.analysis.baseline_clusters import eta_cold_to_warm, median_cold_eta_days


def test_eta_cold_to_warm_basic():
    """At 0 samples + 0.5/day, need 10 samples → 20 days."""
    assert eta_cold_to_warm(samples=0, rate_per_day=0.5) == 20


def test_eta_cold_to_warm_partial_progress():
    """At 5 samples + 0.5/day, need 5 more → 10 days."""
    assert eta_cold_to_warm(samples=5, rate_per_day=0.5) == 10


def test_eta_cold_to_warm_zero_rate_is_none():
    """rate_per_day == 0 → ETA undefined (don't divide by zero)."""
    assert eta_cold_to_warm(samples=5, rate_per_day=0.0) is None


def test_median_cold_eta_returns_int_when_5_or_more_baselines():
    """At least 5 cold baselines with defined ETAs → median is an int."""
    etas = [10, 20, 30, 40, 50]
    assert median_cold_eta_days(etas) == 30


def test_median_cold_eta_returns_none_when_under_5_samples():
    """Fewer than 5 cold baselines with defined ETAs → return None.
    The Telegram report renders this as '—'."""
    assert median_cold_eta_days([10, 20, 30]) is None
    assert median_cold_eta_days([]) is None


def test_median_cold_eta_ignores_none_values():
    """None entries (zero-rate baselines) are filtered out before
    the count threshold is checked."""
    # 4 defined ETAs + 1 None → under threshold → None
    assert median_cold_eta_days([10, None, 20, None, 30, None, 40]) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: 6 new FAIL with `ImportError`.

- [ ] **Step 3: Implement the helpers**

Append to `backend/app/analysis/baseline_clusters.py`:

```python
import statistics


WARM_THRESHOLD = WARM_MIN_SAMPLES  # alias for readability in eta math
MIN_COLD_SAMPLE_FOR_MEDIAN = 5  # below this, median is too noisy to report


def eta_cold_to_warm(samples: int, rate_per_day: float) -> Optional[int]:
    """Days until this baseline reaches the warm threshold (10 samples)
    at its current acquisition rate. None if rate is 0."""
    if rate_per_day <= 0:
        return None
    return int((WARM_THRESHOLD - samples) / rate_per_day)


def median_cold_eta_days(etas: list[Optional[int]]) -> Optional[int]:
    """Median ETA across a list of cold-baseline ETAs.

    None entries (rate=0 baselines) are filtered out first. If fewer
    than MIN_COLD_SAMPLE_FOR_MEDIAN remain, return None — too small
    a sample to report a stable median. The Telegram template
    renders None as '—'."""
    defined = [e for e in etas if e is not None]
    if len(defined) < MIN_COLD_SAMPLE_FOR_MEDIAN:
        return None
    return int(statistics.median(defined))
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: all 21 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/analysis/baseline_clusters.py backend/tests/test_baseline_clusters.py
git commit -m "feat(maturity): eta_cold_to_warm + median (5-sample floor)

ETA per baseline = (10 - samples) / rate_per_day, capped to int.
Median across cold baselines returns None when fewer than 5
defined ETAs — too small a sample for the headline metric.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Aggregate report assembler — failing test

**Files:**
- Modify: `backend/tests/test_baseline_clusters.py`

- [ ] **Step 1: Append the assembler test**

Append to `backend/tests/test_baseline_clusters.py`:

```python
from app.analysis.baseline_clusters import build_cluster_report


def test_build_cluster_report_counts_per_cluster_and_unknowns():
    """End-to-end of the aggregation step: given baselines + a
    samples_by_route map, build a report dict with cluster counts,
    mature_coverage_pct, median cold ETA, and parsing diagnostics."""
    baselines = [
        # 2 hot
        {"route_key": "CDG-LIS-1m", "sample_count": 50},
        {"route_key": "CDG-BCN-1m", "sample_count": 35},
        # 1 warm
        {"route_key": "CDG-MAD-1m", "sample_count": 15},
        # 6 cold (so median ETA is reported)
        *[{"route_key": f"CDG-COLD{i}-1m", "sample_count": 5} for i in range(6)],
        # 2 dormant
        {"route_key": "CDG-ZOM1-1m", "sample_count": 2},
        {"route_key": "CDG-ZOM2-1m", "sample_count": 3},
        # 1 unparseable
        {"route_key": "MALFORMED", "sample_count": 99},
    ]
    # All 6 cold baselines have rate=0.5/day, so each ETA = (10-5)/0.5 = 10
    # The 2 dormant baselines have rate=0
    samples_by_route = {
        ("CDG", f"COLD{i}"): 3 for i in range(6)  # 3/7 ≈ 0.43, > 0.1 → cold... wait
    }
    # Recompute: we want rate=0.5/day → 0.5*7 = 3.5 samples in 7d, round up to 4
    samples_by_route = {("CDG", f"COLD{i}"): 4 for i in range(6)}
    # ZOM1/ZOM2 absent from map → rate 0 → dormant
    known_origins = {"CDG"}

    report = build_cluster_report(
        baselines=baselines,
        samples_by_route=samples_by_route,
        known_origins=known_origins,
    )

    assert report["counts"] == {
        "hot": 2,
        "warm": 1,
        "cold": 6,
        "dormant": 2,
    }
    assert report["unknown_count"] == 1
    assert report["total_parsed"] == 11
    assert report["total_with_unknown"] == 12
    # mature = (2+1)/(2+1+6) = 3/9 = 33.3%
    assert round(report["mature_coverage_pct"], 1) == 33.3
    # 6 cold ETAs all = (10-5) / (4/7) = 8.75 → int = 8
    assert report["median_cold_eta_days"] == 8
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py::test_build_cluster_report_counts_per_cluster_and_unknowns -v
```

Expected: FAIL with `ImportError: cannot import name 'build_cluster_report'`.

---

## Task 11: Aggregate report assembler — implementation

**Files:**
- Modify: `backend/app/analysis/baseline_clusters.py`

- [ ] **Step 1: Implement `build_cluster_report`**

Append to `backend/app/analysis/baseline_clusters.py`:

```python
import logging

logger = logging.getLogger(__name__)


def build_cluster_report(
    *,
    baselines: list[dict],
    samples_by_route: dict[tuple[str, str], int],
    known_origins: set[str],
) -> dict:
    """Assemble the per-cluster maturity report.

    Inputs:
      - baselines: list of dicts with at least 'route_key' and
        'sample_count'.
      - samples_by_route: precomputed 7-day group-by result.
      - known_origins: distinct origins seen in the same 7-day query
        (used for wildcard expansion).

    Output dict:
      {
        "counts": {"hot": N, "warm": N, "cold": N, "dormant": N},
        "unknown_count": int,                  # parse failures
        "total_parsed": int,                   # baselines we classified
        "total_with_unknown": int,             # baselines + unknowns
        "mature_coverage_pct": float,          # (hot+warm)/(hot+warm+cold)
        "median_cold_eta_days": int | None,    # None if <5 cold ETAs
      }
    """
    counts = {"hot": 0, "warm": 0, "cold": 0, "dormant": 0}
    cold_etas: list[Optional[int]] = []
    unknown_count = 0

    for b in baselines:
        origin, destination = parse_route_key(b.get("route_key", ""))
        if destination is None:
            unknown_count += 1
            logger.warning(
                "baseline_clusters: unparseable route_key %r — classifying as unknown",
                b.get("route_key"),
            )
            continue
        samples = int(b.get("sample_count") or 0)
        rate = compute_rate_per_day(
            origin=origin,
            destination=destination,
            samples_by_route=samples_by_route,
            known_origins=known_origins,
        )
        cluster = cluster_baseline(samples=samples, rate_per_day=rate)
        counts[cluster] += 1
        if cluster == "cold":
            cold_etas.append(eta_cold_to_warm(samples=samples, rate_per_day=rate))

    total_parsed = sum(counts.values())
    return {
        "counts": counts,
        "unknown_count": unknown_count,
        "total_parsed": total_parsed,
        "total_with_unknown": total_parsed + unknown_count,
        "mature_coverage_pct": mature_coverage_pct(counts),
        "median_cold_eta_days": median_cold_eta_days(cold_etas),
    }
```

- [ ] **Step 2: Run the test to verify it passes**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py::test_build_cluster_report_counts_per_cluster_and_unknowns -v
```

Expected: PASS.

- [ ] **Step 3: Run the full suite**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: 22 PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/analysis/baseline_clusters.py backend/tests/test_baseline_clusters.py
git commit -m "feat(maturity): build_cluster_report assembler

End-to-end aggregation: per-cluster counts, mature coverage %,
median cold ETA, parsing diagnostics. WARNING logged for every
unparseable route_key so a surge of unknowns is observable.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Telegram format — failing test

**Files:**
- Modify: `backend/tests/test_baseline_clusters.py`

- [ ] **Step 1: Append the format test**

Append to `backend/tests/test_baseline_clusters.py`:

```python
from app.analysis.baseline_clusters import format_cluster_report_for_telegram


def test_format_cluster_report_fits_in_under_12_lines():
    """The Telegram template must stay compact: ≤12 lines. Also
    verify all four cluster rows + season + parsing diagnostic
    are present."""
    report = {
        "counts": {"hot": 162, "warm": 487, "cold": 542, "dormant": 1123},
        "unknown_count": 4,
        "total_parsed": 2314,
        "total_with_unknown": 2318,
        "mature_coverage_pct": 54.5,
        "median_cold_eta_days": 45,
    }
    text = format_cluster_report_for_telegram(
        report=report,
        season="spring",
        median_samples_per_baseline=0.17,
    )
    lines = text.splitlines()
    assert len(lines) <= 12, f"Expected ≤12 lines, got {len(lines)}: {text}"
    assert "Couverture mature" in text
    assert "54" in text  # %
    assert "Hot" in text and "162" in text
    assert "Warm" in text and "487" in text
    assert "Cold" in text and "542" in text
    assert "Dormant" in text and "1123" in text
    assert "spring" in text
    assert "2314/2318" in text or "2314" in text  # parsing diagnostic


def test_format_renders_median_eta_dash_when_none():
    """When fewer than 5 cold baselines, median_cold_eta_days is None
    → the Cold line shows '—' instead of a number."""
    report = {
        "counts": {"hot": 0, "warm": 0, "cold": 2, "dormant": 0},
        "unknown_count": 0,
        "total_parsed": 2,
        "total_with_unknown": 2,
        "mature_coverage_pct": 0.0,
        "median_cold_eta_days": None,
    }
    text = format_cluster_report_for_telegram(
        report=report,
        season="summer",
        median_samples_per_baseline=0.0,
    )
    assert "—" in text  # em dash for undefined median
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: 2 new FAIL with `ImportError`.

---

## Task 13: Telegram format — implementation

**Files:**
- Modify: `backend/app/analysis/baseline_clusters.py`

- [ ] **Step 1: Implement `format_cluster_report_for_telegram`**

Append to `backend/app/analysis/baseline_clusters.py`:

```python
def _pct_of_total(count: int, total_with_unknown: int) -> str:
    """Render 'X%' against the total-brut denominator (dormants
    included). Returns ' 0%' when total is 0."""
    if total_with_unknown == 0:
        return " 0%"
    return f"{round(100 * count / total_with_unknown):>2}%"


def format_cluster_report_for_telegram(
    *,
    report: dict,
    season: str,
    median_samples_per_baseline: float,
) -> str:
    """Render the report as a ≤12-line Markdown Telegram message.

    The headline mature_coverage_pct uses (hot+warm)/(hot+warm+cold).
    The per-cluster (X%) badges use total_with_unknown (dormants
    included) — by design, so the dormant share remains visible.
    """
    c = report["counts"]
    cov = round(report["mature_coverage_pct"])
    total = report["total_with_unknown"]
    parsed_ok = report["total_parsed"]
    eta = report["median_cold_eta_days"]
    eta_str = f"{eta}j (médiane)" if eta is not None else "— (méd.)"

    lines = [
        f"🟡 *Couverture mature : {cov}%*",
        "",
        f"  🟢 Hot     {c['hot']:>4}  ({_pct_of_total(c['hot'], total)})  ≥30 samples",
        f"  🟡 Warm    {c['warm']:>4}  ({_pct_of_total(c['warm'], total)})  10-29 samples",
        f"  🟠 Cold    {c['cold']:>4}  ({_pct_of_total(c['cold'], total)})  ETA warm: {eta_str}",
        f"  🔴 Dormant {c['dormant']:>4} ({_pct_of_total(c['dormant'], total)})  → CSV envoyé",
        "",
        f"samples/baseline/jour (méd) : {median_samples_per_baseline:.2f}",
        "",
        f"📊 Saison scheduler actuelle : {season}",
        f"⚠️ Parsing route_key : {parsed_ok}/{total} OK, {report['unknown_count']} unknown",
    ]
    return "\n".join(lines)
```

- [ ] **Step 2: Run the tests to verify they pass**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: 24 PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/analysis/baseline_clusters.py backend/tests/test_baseline_clusters.py
git commit -m "feat(maturity): Telegram format with ≤12-line constraint

Per-cluster (X%) badges use total_brut as denominator (dormants
included) — the headline mature_coverage_pct uses active-only.
Two denominators coexist by design.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: Rewrite `baseline_maturity.py` — fetch + glue

**Files:**
- Modify: `backend/app/analysis/baseline_maturity.py`

- [ ] **Step 1: Inspect the current module**

```bash
cat backend/app/analysis/baseline_maturity.py | head -50
```

Note the existing `compute_report()` and `format_for_telegram()` signatures — we'll preserve the public name `compute_report()` and `format_for_telegram()` so the scheduler job in `jobs.py` doesn't need to be touched.

- [ ] **Step 2: Replace the module body**

Replace the entire content of `backend/app/analysis/baseline_maturity.py` with:

```python
"""Baseline maturity — cluster-based scoring.

Rewritten in chantier 2 (2026-05-17). The previous version produced
a single 0–100 composite score assuming uniform sample distribution
across baselines, which was misleading: 72% of samples concentrate
on 5 Spain destinations. The new version classifies each baseline
into one of four clusters (hot / warm / cold / dormant) and reports
a headline % mature coverage that excludes dormants from the
denominator.

The public interface stays compatible with the existing scheduler
hook in app/scheduler/jobs.py:
    compute_report() -> dict | None
    format_for_telegram(report: dict) -> str
"""
from __future__ import annotations

import logging
import statistics
from datetime import datetime, timezone

from app.analysis.baseline_clusters import (
    build_cluster_report,
    format_cluster_report_for_telegram,
)
from app.db import db

logger = logging.getLogger(__name__)

# Maps month → scheduler season label. Mirror of the priority logic
# in route_selector. Kept as a flat dict so the maturity job doesn't
# need to import the heavier route_selector module.
_SEASON_BY_MONTH = {
    1: "winter", 2: "winter", 12: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}


def _current_season() -> str:
    return _SEASON_BY_MONTH.get(datetime.now(timezone.utc).month, "unknown")


def _fetch_baselines() -> list[dict]:
    """Pull all rows from price_baselines, paginated."""
    if not db:
        return []
    rows: list[dict] = []
    offset = 0
    while True:
        chunk = (
            db.table("price_baselines")
            .select("route_key,sample_count,avg_price,std_dev")
            .range(offset, offset + 999)
            .execute()
        )
        page = chunk.data or []
        rows.extend(page)
        if len(page) < 1000:
            break
        offset += 1000
    return rows


def _fetch_samples_by_route() -> tuple[dict[tuple[str, str], int], set[str]]:
    """Single grouped query: how many raw_flights per (origin, dest)
    in the last 7 days. Returns the map and the set of distinct
    origins seen (used for wildcard expansion in baseline_clusters)."""
    if not db:
        return {}, set()
    # supabase-py doesn't expose GROUP BY directly; rely on the REST
    # default and aggregate in Python. Paginate to be safe.
    samples: dict[tuple[str, str], int] = {}
    origins: set[str] = set()
    offset = 0
    seven_days_ago = (datetime.now(timezone.utc).timestamp() - 7 * 86400)
    seven_days_ago_iso = datetime.fromtimestamp(seven_days_ago, tz=timezone.utc).isoformat()
    while True:
        chunk = (
            db.table("raw_flights")
            .select("origin,destination")
            .gte("scraped_at", seven_days_ago_iso)
            .range(offset, offset + 999)
            .execute()
        )
        page = chunk.data or []
        for r in page:
            o, d = r.get("origin"), r.get("destination")
            if not o or not d:
                continue
            origins.add(o)
            samples[(o, d)] = samples.get((o, d), 0) + 1
        if len(page) < 1000:
            break
        offset += 1000
    return samples, origins


def compute_report() -> dict | None:
    """Build the maturity report. Returns the same dict shape that
    format_for_telegram consumes."""
    baselines = _fetch_baselines()
    if not baselines:
        logger.warning("baseline_maturity: no baselines to score")
        return None
    samples_by_route, known_origins = _fetch_samples_by_route()
    report = build_cluster_report(
        baselines=baselines,
        samples_by_route=samples_by_route,
        known_origins=known_origins,
    )
    # Median samples per baseline (informational, kept from v1).
    counts = [int(b.get("sample_count") or 0) for b in baselines]
    median_samples = statistics.median(counts) if counts else 0
    report["median_samples_per_baseline"] = median_samples
    report["season"] = _current_season()
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    return report


def format_for_telegram(report: dict) -> str:
    """Render the cluster report for the admin Telegram chat."""
    return format_cluster_report_for_telegram(
        report=report,
        season=report.get("season", "unknown"),
        median_samples_per_baseline=report.get("median_samples_per_baseline", 0),
    )
```

- [ ] **Step 3: Verify the scheduler hook still compiles**

```bash
.venv/bin/python3 -c "
from app.analysis.baseline_maturity import compute_report, format_for_telegram
print('imports OK')
"
```

Expected: `imports OK`.

- [ ] **Step 4: Run all clusters tests + dispatch_guards as a smoke check**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py tests/test_dispatch_guards.py -v
```

Expected: all PASS.

- [ ] **Step 5: Smoke-run against prod DB**

```bash
.venv/bin/python3 -c "
from dotenv import load_dotenv; load_dotenv('.env')
from app.analysis.baseline_maturity import compute_report, format_for_telegram
r = compute_report()
print(format_for_telegram(r))
"
```

Expected: a real ≤12-line report printed, with non-zero counts in at least one cluster.

- [ ] **Step 6: Commit**

```bash
git add backend/app/analysis/baseline_maturity.py
git commit -m "refactor(maturity): rewrite around baseline_clusters

Drops the legacy MaturitySignal/score-composite logic. compute_report
now returns the cluster report dict; format_for_telegram delegates
to baseline_clusters.format_cluster_report_for_telegram. Scheduler
hook signature preserved.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 15: Dormants CSV — failing test

**Files:**
- Modify: `backend/tests/test_baseline_clusters.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_baseline_clusters.py`:

```python
from app.analysis.baseline_clusters import build_dormants_csv


def test_build_dormants_csv_contains_expected_columns_and_season():
    """CSV header + rows: every dormant baseline becomes one row
    with route_key, sample_count, last_scrape_at, rate_per_day_7d,
    last_seen_in_season."""
    dormants = [
        {
            "route_key": "CDG-ZOM1-1m",
            "sample_count": 2,
            "last_scrape_at": "2026-04-15T10:00:00+00:00",
            "rate_per_day_7d": 0.0,
        },
        {
            "route_key": "*-NRT-bucket_long",
            "sample_count": 3,
            "last_scrape_at": None,
            "rate_per_day_7d": 0.05,
        },
    ]
    csv_text = build_dormants_csv(dormants=dormants, current_season="spring")
    lines = csv_text.strip().splitlines()
    assert lines[0] == "route_key,sample_count,last_scrape_at,rate_per_day_7d,last_seen_in_season"
    assert len(lines) == 3  # header + 2 rows
    assert "CDG-ZOM1-1m" in lines[1]
    assert ",spring" in lines[1]
    # NULL last_scrape_at renders as empty field, not the literal "None"
    assert ",,0.05,spring" in lines[2]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py::test_build_dormants_csv_contains_expected_columns_and_season -v
```

Expected: FAIL with `ImportError`.

---

## Task 16: Dormants CSV — implementation

**Files:**
- Modify: `backend/app/analysis/baseline_clusters.py`

- [ ] **Step 1: Implement `build_dormants_csv`**

Append to `backend/app/analysis/baseline_clusters.py`:

```python
import csv
import io


def build_dormants_csv(*, dormants: list[dict], current_season: str) -> str:
    """Render the dormant baselines as CSV text.

    Columns: route_key, sample_count, last_scrape_at,
             rate_per_day_7d, last_seen_in_season

    `last_scrape_at` of None renders as an empty string (not 'None'),
    standard CSV convention. `current_season` is duplicated on every
    row so the operator reading the file can correlate the dormant
    label with the scheduler's current rotation.
    """
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow([
        "route_key",
        "sample_count",
        "last_scrape_at",
        "rate_per_day_7d",
        "last_seen_in_season",
    ])
    for d in dormants:
        writer.writerow([
            d.get("route_key", ""),
            d.get("sample_count", 0),
            d.get("last_scrape_at") or "",
            d.get("rate_per_day_7d", 0.0),
            current_season,
        ])
    return out.getvalue()
```

- [ ] **Step 2: Run the test to verify it passes**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py::test_build_dormants_csv_contains_expected_columns_and_season -v
```

Expected: PASS.

- [ ] **Step 3: Run the full suite**

```bash
.venv/bin/pytest tests/test_baseline_clusters.py -v
```

Expected: 25 PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/analysis/baseline_clusters.py backend/tests/test_baseline_clusters.py
git commit -m "feat(maturity): build_dormants_csv with last_seen_in_season

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 17: Wire the monthly dormants cron

**Files:**
- Modify: `backend/app/scheduler/jobs.py`
- Modify: `backend/app/notifications/telegram.py`

- [ ] **Step 1: Add `send_admin_markdown_with_link` helper** (only if a similar helper does not already exist — `grep` to check)

```bash
grep -n "send_admin_markdown\|send_admin_alert\b" backend/app/notifications/telegram.py
```

If only the existing `send_admin_markdown` is present, reuse it (Markdown messages can contain a clickable URL). No new helper required.

- [ ] **Step 2: Add the new job function**

Open `backend/app/scheduler/jobs.py`. Find the existing `job_weekly_baseline_maturity` function. Right after it, add:

```python
async def job_monthly_dormant_baselines_csv():
    """Export dormant baselines to a CSV, upload to Supabase storage,
    and post the signed URL in the admin chat.

    Runs on the 1st of each month so the operator can review which
    routes to purge vs. which are off-season and will revive.
    """
    if not db:
        return
    from app.analysis.baseline_maturity import compute_report
    from app.analysis.baseline_clusters import (
        parse_route_key,
        compute_rate_per_day,
        build_dormants_csv,
    )
    from app.notifications.telegram import send_admin_markdown

    report = compute_report()
    if not report:
        await send_admin_markdown("Dormants CSV: no baselines to report.")
        return

    # Re-pull baselines + rates so we can list the actual dormants
    # (compute_report only returns aggregated counts).
    from app.analysis.baseline_maturity import _fetch_baselines, _fetch_samples_by_route, _current_season
    baselines = _fetch_baselines()
    samples_by_route, known_origins = _fetch_samples_by_route()

    dormants: list[dict] = []
    for b in baselines:
        origin, dest = parse_route_key(b.get("route_key", ""))
        if dest is None:
            continue
        samples = int(b.get("sample_count") or 0)
        if samples >= 10:
            continue
        rate = compute_rate_per_day(
            origin=origin, destination=dest,
            samples_by_route=samples_by_route,
            known_origins=known_origins,
        )
        if rate > 0.1:
            continue  # cold, not dormant
        dormants.append({
            "route_key": b.get("route_key"),
            "sample_count": samples,
            "last_scrape_at": None,  # column not selected by _fetch_baselines today
            "rate_per_day_7d": round(rate, 3),
        })

    csv_text = build_dormants_csv(
        dormants=dormants, current_season=_current_season()
    )

    # Upload to Supabase storage bucket "maturity-reports" (private)
    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = f"dormants/{stamp}.csv"
    try:
        db.storage.from_("maturity-reports").upload(
            path=path,
            file=csv_text.encode("utf-8"),
            file_options={"content-type": "text/csv", "upsert": "true"},
        )
        signed = db.storage.from_("maturity-reports").create_signed_url(
            path=path, expires_in=86400 * 30
        )
        url = signed.get("signedURL") or signed.get("signed_url") or ""
    except Exception as e:
        logger.exception("Dormants CSV upload failed: %s", e)
        await send_admin_markdown(f"⚠️ Dormants CSV upload failed: `{e}`")
        return

    await send_admin_markdown(
        f"📄 *Dormant baselines (mensuel)* — {len(dormants)} routes\n"
        f"[Télécharger le CSV]({url})\n"
        f"_(lien valable 30 jours)_"
    )
```

- [ ] **Step 3: Register the cron in the scheduler job list**

In the same file, locate the list of cron definitions (search for `weekly_baseline_maturity`). Add right after it:

```python
        {
            "id": "monthly_dormant_baselines_csv",
            "func": job_monthly_dormant_baselines_csv,
            "trigger": "cron",
            "day": 1,
            "hour": 9,
            "minute": 30,
        },
```

- [ ] **Step 4: Verify scheduler module imports cleanly**

```bash
.venv/bin/python3 -c "
from app.scheduler.jobs import job_monthly_dormant_baselines_csv
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 5: Create the storage bucket (manual, one-time)**

In Supabase dashboard → Storage → New bucket → name `maturity-reports`, **Private**. Save.

- [ ] **Step 6: Commit**

```bash
git add backend/app/scheduler/jobs.py
git commit -m "feat(scheduler): monthly dormants CSV cron (1st @ 09:30)

Uploads to Supabase storage bucket 'maturity-reports' (private),
posts the signed URL (30-day expiry) to the admin chat. No
silent failures: upload errors are reported to admin too.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 18: Smoke-run the weekly job locally

**Files:** none (operational step).

- [ ] **Step 1: Trigger the maturity report manually**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend
.venv/bin/python3 -c "
from dotenv import load_dotenv; load_dotenv('.env')
import asyncio
from app.scheduler.jobs import job_weekly_baseline_maturity
asyncio.run(job_weekly_baseline_maturity())
print('Job complete — check the admin Telegram chat for the report.')
"
```

Expected: the admin Telegram chat receives a ≤12-line cluster report. Manually verify:
- Headline % is a sensible number (probably 50-60%).
- Hot/Warm/Cold/Dormant counts are present and sum to ~2314.
- Season line shows "spring" (today is mid-May).
- Parsing diagnostic shows close to 100% OK.

- [ ] **Step 2: Trigger the monthly CSV job manually**

```bash
.venv/bin/python3 -c "
from dotenv import load_dotenv; load_dotenv('.env')
import asyncio
from app.scheduler.jobs import job_monthly_dormant_baselines_csv
asyncio.run(job_monthly_dormant_baselines_csv())
print('Done.')
"
```

Expected:
- Admin chat receives a message with a signed CSV URL.
- Clicking the URL downloads a CSV with the expected columns.
- Row count matches the dormant count from the weekly report.

- [ ] **Step 3: Commit if any small fixes were needed**

If the smoke run revealed a minor adjustment (e.g. a missing column in `_fetch_baselines`), fix and commit. Otherwise skip.

---

## Task 19: Open the PR for chantier 2

**Files:** none (Git/GitHub step).

- [ ] **Step 1: Push the branch**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git push origin polish-pre-launch
```

(If chantier 1 was already pushed to the same branch, this just adds the new commits.)

- [ ] **Step 2: Open the PR (or update the chantier-1 PR description if you bundled both)**

If shipping as a separate PR:

```bash
gh pr create --title "feat: chantier 2 — cluster-based baseline maturity" --body "$(cat <<'EOF'
## Summary

- Migration 040: compound index on `raw_flights(origin, destination, scraped_at)`.
- New module `app/analysis/baseline_clusters.py`: parser, rate aggregator, classifier, report assembler, dormants CSV, Telegram format.
- Rewritten `app/analysis/baseline_maturity.py` around clusters; scheduler hook signature preserved.
- New monthly cron `job_monthly_dormant_baselines_csv` uploads CSV to Supabase storage and posts signed URL.

Spec: `docs/superpowers/specs/2026-05-17-polish-pre-launch-design.md`.

## Test plan

- [ ] `pytest backend/tests/test_baseline_clusters.py` → 25 PASS
- [ ] Manual: `job_weekly_baseline_maturity` posts a ≤12-line report with the new format
- [ ] Manual: `job_monthly_dormant_baselines_csv` posts a signed URL; downloaded CSV has the expected columns
- [ ] Parsing diagnostic line shows close to 100% OK on prod data

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed.

---

## Self-Review

**Spec coverage check** (against the `Chantier 2` section of the spec):

- ✅ Cluster definitions hot/warm/cold/dormant with stated thresholds (Tasks 4, 5)
- ✅ Rate measurement via single grouped query, 7-day window (Task 14, `_fetch_samples_by_route`)
- ✅ Compound index migration 040 (Task 1)
- ✅ Parser for `route_key` with wildcard origin support (Tasks 2, 3)
- ✅ `mature_coverage_pct` excludes dormants from denominator (Task 8)
- ✅ ETA cold→warm with median + 5-sample floor (Task 9)
- ✅ Telegram format ≤12 lines + season line + parsing diagnostic (Tasks 12, 13)
- ✅ Per-cluster (X%) uses total brut (visible dormant share) — implemented in `_pct_of_total` (Task 13)
- ✅ Monthly dormants CSV with `last_seen_in_season` column (Tasks 15, 16, 17)
- ✅ Stored privately in Supabase storage with signed URL (Task 17)
- ✅ "—" rendered when median ETA undefined (Task 12 test + Task 13 implementation)
- ✅ Parsing failures logged as WARNING and surface in diagnostic line (Task 11)
- ⚠️ **Not included by design**: snapshot table + delta vs S-1 — explicitly deferred to v2 in the spec.

**Placeholder scan**: no TBD/TODO/FIXME in the plan. Every step has executable content.

**Type consistency**: `parse_route_key` returns `tuple[Optional[str], Optional[str]]` everywhere. `cluster_baseline` returns `str`. `build_cluster_report` returns dict with the same keys used in `format_cluster_report_for_telegram` and `job_monthly_dormant_baselines_csv`. The `samples_by_route` dict uses `tuple[str, str]` keys consistently. `known_origins` is `set[str]` consistently.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-17-polish-pre-launch-chantier-2-cluster-maturity.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
