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
