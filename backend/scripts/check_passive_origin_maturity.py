"""Check whether a PASSIVE origin (BSL/MLH/EAP, BRU, GVA, ZRH) has
mature enough baselines to be promoted to an active MVP origin.

Context: passive origins are scraped with passive=true — their rows
feed price_baselines but never reach the alert pipeline (config.py
PASSIVE_ORIGINS). The promotion plan is "flip to MVP once baselines
are mature (~4 weeks)". This script measures that, per origin:

  - fresh baselines (calculated_at ≤ 21 days, the qualifier's gate)
  - baselines with sample_count ≥ MIN_BASELINE_SAMPLE_COUNT
  - raw_flights volume over the last 30 days

Verdict: READY when ≥ 8 distinct routes have a fresh baseline with
enough samples — below that, flipping the origin would mostly produce
fallback-discount qualifications on noisy young cells.

Usage (from backend/):
    python -m scripts.check_passive_origin_maturity [ORIGIN ...]

With no argument, checks every origin in settings.PASSIVE_ORIGINS.

To promote an origin once READY (env change, no deploy needed):
  1. Add it to MVP_AIRPORTS on Railway
     (e.g. MVP_AIRPORTS=CDG,ORY,LYS,MRS,NCE,BOD,NTE,TLS,BVA,BSL)
  2. Remove it (and its IATA aliases — BSL/MLH/EAP are one airport)
     from PASSIVE_ORIGINS so rows stop being flagged passive.
  3. Restart the backend. The origin becomes user-selectable
     (api/routes.py VALID_AIRPORTS reads MVP_AIRPORTS).
"""
import sys
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db import db
from app.thresholds import MIN_BASELINE_SAMPLE_COUNT

BASELINE_MAX_AGE_DAYS = 21   # mirror of jobs.py qualifier gate
READY_MIN_ROUTES = 8


def check_origin(origin: str) -> bool:
    now = datetime.now(timezone.utc)
    fresh_cutoff = (now - timedelta(days=BASELINE_MAX_AGE_DAYS)).isoformat()
    volume_cutoff = (now - timedelta(days=30)).isoformat()

    resp = (
        db.table("price_baselines")
        .select("route_key,sample_count,calculated_at")
        .like("route_key", f"{origin}-%")
        .eq("type", "flight")
        .execute()
    )
    baselines = resp.data or []

    # One route can have several cells (seasonal / legacy buckets); a
    # route counts as mature when at least one of its cells is fresh
    # AND sufficiently sampled.
    mature_routes: set[str] = set()
    fresh_cells = 0
    for b in baselines:
        route = "-".join((b.get("route_key") or "").split("-")[:2])
        calc_at = b.get("calculated_at") or ""
        is_fresh = bool(calc_at) and calc_at >= fresh_cutoff
        if is_fresh:
            fresh_cells += 1
        if is_fresh and (b.get("sample_count") or 0) >= MIN_BASELINE_SAMPLE_COUNT:
            mature_routes.add(route)

    vol_resp = (
        db.table("raw_flights")
        .select("id", count="exact")
        .eq("origin", origin)
        .gte("scraped_at", volume_cutoff)
        .limit(1)
        .execute()
    )
    rows_30d = vol_resp.count or 0

    ready = len(mature_routes) >= READY_MIN_ROUTES
    verdict = "✅ READY — promotable en MVP" if ready else "⏳ PAS ENCORE"
    print(f"\n── {origin} ──")
    print(f"  raw_flights (30j)              : {rows_30d}")
    print(f"  cellules baseline (total)      : {len(baselines)}")
    print(f"  cellules fraîches (≤{BASELINE_MAX_AGE_DAYS}j)      : {fresh_cells}")
    print(f"  routes matures (fresh + ≥{MIN_BASELINE_SAMPLE_COUNT} obs): {len(mature_routes)}"
          f" (seuil READY: {READY_MIN_ROUTES})")
    if mature_routes:
        print(f"  routes: {', '.join(sorted(mature_routes))}")
    print(f"  verdict: {verdict}")
    return ready


def main() -> None:
    if not db:
        print("DB non configurée (SUPABASE_URL / SUPABASE_SERVICE_KEY).")
        sys.exit(1)
    origins = [o.upper() for o in sys.argv[1:]] or list(settings.PASSIVE_ORIGINS)
    if not origins:
        print("Aucune origine passive configurée.")
        return
    print(f"Audit de maturité des origines passives: {', '.join(origins)}")
    any_ready = any(check_origin(o) for o in origins)
    if any_ready:
        print(
            "\nPour promouvoir une origine READY: ajoutez-la à MVP_AIRPORTS et "
            "retirez-la (avec ses alias IATA) de PASSIVE_ORIGINS sur Railway, "
            "puis redémarrez. Voir le docstring du script."
        )


if __name__ == "__main__":
    main()
