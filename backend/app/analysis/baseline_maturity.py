"""Baseline maturity scoring.

Computes 7 objective signals on the `price_baselines` table and emits a
0–100 score plus a chiffré ETA for when the baseline reaches the
"production-ready" threshold. Designed to be called weekly so the founder
no longer has to eyeball the numbers — the score tells you whether
tuning still adds value or whether you should ship features instead.

Thresholds (cible production-ready):
  - median sample_count             ≥ 20
  - % baselines with samples < 10   ≤ 20%
  - % baselines with samples ≥ 30   ≥ 50%
  - median CV (std/avg)             ≤ 15%
  - % baselines with CV > 30%       ≤ 5%
  - reverification rate (qualified) ≥ 75%
  - % qual method 'unknown'         ≤ 5%
"""
from __future__ import annotations
import logging
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from app.db import db

logger = logging.getLogger(__name__)


@dataclass
class MaturitySignal:
    name: str
    value: float
    target: float
    higher_is_better: bool
    score: float  # 0..1, where 1 = at or beyond target


@dataclass
class MaturityReport:
    score: int  # 0..100
    signals: list[MaturitySignal]
    sample_count_median: int
    samples_per_day: float  # raw_flights/jour, used for ETA
    eta_days_to_mature: int | None
    eta_date: str | None  # YYYY-MM-DD or None if already mature
    generated_at: str

    def as_dict(self) -> dict:
        return {
            **asdict(self),
            "signals": [asdict(s) for s in self.signals],
        }


def _score_signal(value: float, target: float, higher_is_better: bool) -> float:
    """Linear score in [0, 1]. 1.0 means target is met or exceeded."""
    if higher_is_better:
        return min(1.0, value / target) if target > 0 else 1.0
    # lower-is-better: 1.0 when value=0, 0 when value≥2*target
    if value <= target:
        return 1.0
    return max(0.0, 1.0 - (value - target) / target)


def compute_report() -> MaturityReport | None:
    """Pull everything from DB and compute the maturity score."""
    if not db:
        return None

    baselines = []
    offset = 0
    while True:
        chunk = db.table("price_baselines").select(
            "sample_count,avg_price,std_dev"
        ).range(offset, offset + 999).execute()
        rows = chunk.data or []
        baselines.extend(rows)
        if len(rows) < 1000:
            break
        offset += 1000

    if not baselines:
        return None

    samples = [b["sample_count"] for b in baselines if b.get("sample_count")]
    cvs = [
        b["std_dev"] / b["avg_price"]
        for b in baselines
        if b.get("avg_price") and b.get("std_dev") is not None and b["avg_price"] > 0
    ]
    sample_med = int(statistics.median(samples)) if samples else 0
    weak_pct = 100 * sum(1 for s in samples if s < 10) / len(samples) if samples else 100
    strong_pct = 100 * sum(1 for s in samples if s >= 30) / len(samples) if samples else 0
    cv_med = statistics.median(cvs) if cvs else 1.0
    cv_noisy_pct = 100 * sum(1 for c in cvs if c > 0.30) / len(cvs) if cvs else 100

    # Reverification rate + legacy method share (last 30 days only — older data is noise)
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    qi = db.table("qualified_items").select(
        "qualification_method,reverified_at"
    ).gte("created_at", cutoff).execute()
    qi_rows = qi.data or []
    rev_rate = (
        100 * sum(1 for q in qi_rows if q.get("reverified_at")) / len(qi_rows)
        if qi_rows else 0
    )
    unknown_pct = (
        100 * sum(1 for q in qi_rows if q.get("qualification_method") == "unknown") / len(qi_rows)
        if qi_rows else 100
    )

    signals = [
        MaturitySignal("Médiane samples/baseline", sample_med, 20, True,
                       _score_signal(sample_med, 20, True)),
        MaturitySignal("% baselines à <10 samples", weak_pct, 20, False,
                       _score_signal(weak_pct, 20, False)),
        MaturitySignal("% baselines à ≥30 samples", strong_pct, 50, True,
                       _score_signal(strong_pct, 50, True)),
        MaturitySignal("CV médian (std/avg, %)", cv_med * 100, 15, False,
                       _score_signal(cv_med * 100, 15, False)),
        MaturitySignal("% baselines bruitées (CV>30%)", cv_noisy_pct, 5, False,
                       _score_signal(cv_noisy_pct, 5, False)),
        MaturitySignal("Reverification rate (30j)", rev_rate, 75, True,
                       _score_signal(rev_rate, 75, True)),
        MaturitySignal("% qual_method 'unknown' (30j)", unknown_pct, 5, False,
                       _score_signal(unknown_pct, 5, False)),
    ]

    # Equal-weighted average across signals
    score = int(round(100 * sum(s.score for s in signals) / len(signals)))

    # ETA — sample_count is the dominant blocker.
    # Naïve "raw_flights/day per baseline" is misleading because raw volume
    # concentrates on hot routes (BCN/AGP/MAD) while the median baseline
    # belongs to a cold tail that barely accumulates samples.
    # Better proxy: the median sample_count grows roughly with calendar
    # depth — empirically ~1 sample/week per cold-tail baseline. Use the
    # age of the oldest raw_flight to extrapolate.
    oldest = db.table("raw_flights").select("scraped_at").order(
        "scraped_at"
    ).limit(1).execute()
    history_days = 1.0
    if oldest.data:
        ts = oldest.data[0]["scraped_at"].replace("Z", "+00:00")
        # tolerate non-6-digit microseconds (Postgres can emit 5)
        if "." in ts and "+" in ts:
            base, tz = ts.rsplit("+", 1)
            head, frac = base.rsplit(".", 1)
            ts = f"{head}.{frac[:6].ljust(6, '0')}+{tz}"
        try:
            start = datetime.fromisoformat(ts)
            history_days = max((datetime.now(timezone.utc) - start).total_seconds() / 86400, 1.0)
        except ValueError:
            pass
    samples_per_day = sample_med / history_days

    eta_days = None
    eta_date = None
    if sample_med < 20 and samples_per_day > 0:
        eta_days = int((20 - sample_med) / samples_per_day)
        eta_date = (datetime.now(timezone.utc) + timedelta(days=eta_days)).date().isoformat()

    return MaturityReport(
        score=score,
        signals=signals,
        sample_count_median=sample_med,
        samples_per_day=round(samples_per_day, 2),
        eta_days_to_mature=eta_days,
        eta_date=eta_date,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def format_for_telegram(r: MaturityReport) -> str:
    """Render the report as a Markdown Telegram message."""
    emoji = "🟢" if r.score >= 80 else "🟡" if r.score >= 60 else "🔴"
    lines = [
        f"{emoji} *Baseline maturity : {r.score}/100*",
        "",
        f"Médiane samples/baseline : *{r.sample_count_median}* (cible 20)",
    ]
    if r.eta_date:
        lines.append(f"ETA mature : *{r.eta_date}* ({r.eta_days_to_mature}j au rythme actuel)")
    else:
        lines.append("✅ Cible samples atteinte")
    lines.append("")
    lines.append("*Détail des signaux :*")
    for s in r.signals:
        check = "✅" if s.score >= 0.95 else "🟡" if s.score >= 0.7 else "🔴"
        val = f"{s.value:.0f}" if s.value >= 1 else f"{s.value:.1f}"
        lines.append(f"{check} {s.name} : {val} (cible {s.target:.0f})")
    return "\n".join(lines)
