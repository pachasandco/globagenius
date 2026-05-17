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
from datetime import datetime, timezone, timedelta

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
    seven_days_ago_iso = (
        datetime.now(timezone.utc) - timedelta(days=7)
    ).isoformat()
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
