"""V5+: detect 'combo malin' — buying outbound + inbound as two one-way tickets
when the total beats the round-trip baseline by a meaningful margin.

This module is pure: no DB, no I/O. Inputs are plain dicts (the same shape as
raw_flights rows for one-way entries) and a roundtrip baseline price for the
route+stay-duration cell. Callers persist results and dispatch alerts."""

from dataclasses import dataclass
from datetime import datetime

# Combo qualification thresholds — tuned to surface real wins without spam.
# A 14% saving on an A/R route can be daily noise; 15% with a 100€ floor is
# the threshold where Telegram alert volume stays sustainable.
SAVINGS_RATIO_FLOOR = 0.15        # total must be <= baseline * (1 - 0.15)
SAVINGS_EUR_FLOOR = 100.0
MIN_STAY_DAYS = 4
MAX_STAY_DAYS = 30


@dataclass(frozen=True)
class SplitTicketCombo:
    outbound: dict
    inbound: dict
    total: int                    # rounded EUR
    savings: int                  # rounded EUR vs roundtrip baseline
    roundtrip_baseline: int       # rounded EUR


def _parse_date(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def find_split_ticket_combos(
    outbounds: list[dict],
    inbounds: list[dict],
    roundtrip_baseline: float,
) -> list[SplitTicketCombo]:
    """Return at most one qualified combo per (origin, destination) — the pair
    with the largest absolute savings against the round-trip baseline.

    Pre-V5 callers should slice their data to one route + one stay-duration
    bucket before calling this so the baseline is comparable to the combo
    total. Mixing buckets here would falsely qualify combos."""
    if roundtrip_baseline <= 0 or not outbounds or not inbounds:
        return []

    threshold_total = roundtrip_baseline * (1 - SAVINGS_RATIO_FLOOR)

    best: SplitTicketCombo | None = None
    for out in outbounds:
        out_dt = _parse_date(out.get("departure_date", ""))
        if out_dt is None:
            continue
        for inb in inbounds:
            in_dt = _parse_date(inb.get("departure_date", ""))
            if in_dt is None:
                continue
            stay = (in_dt - out_dt).days
            if stay < MIN_STAY_DAYS or stay > MAX_STAY_DAYS:
                continue

            total = out.get("price", 0) + inb.get("price", 0)
            if total > threshold_total:
                continue
            savings = roundtrip_baseline - total
            if savings < SAVINGS_EUR_FLOOR:
                continue

            combo = SplitTicketCombo(
                outbound=out,
                inbound=inb,
                total=int(round(total)),
                savings=int(round(savings)),
                roundtrip_baseline=int(round(roundtrip_baseline)),
            )
            if best is None or combo.savings > best.savings:
                best = combo

    return [best] if best else []
