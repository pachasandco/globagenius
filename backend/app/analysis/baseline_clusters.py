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
