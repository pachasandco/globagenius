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

# Matches the two leading tokens of a route_key. The origin is either
# a 3-letter IATA code (CDG, ORY, …) or the literal "*" wildcard
# meaning "all origins". The destination is always a 3-letter IATA.
# A third segment is required (period/bucket suffix); extra hyphen-
# delimited suffixes (month, lead-time) are accepted via the trailing
# `.+`.
_ROUTE_KEY_RE = re.compile(
    r"^(?P<origin>[A-Z]{3}|\*)-(?P<dest>[A-Z]{3})-.+$"
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
