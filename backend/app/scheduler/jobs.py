import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from app.config import settings, IATA_TO_CITY, iata_label
from app.db import db
from app.scraper.travelpayouts_flights import scrape_all_flights
from app.scraper.tier1_scraper import scrape_all_tier1
from app.analysis.baselines import compute_baseline, compute_baselines_by_bucket, MIN_SAMPLE_COUNT
from app.scraper.travelpayouts import get_prices_for_dates, get_oneway_calendar
from app.scraper.normalizer import normalize_flight
from app.scraper.travelpayouts_flights import _normalize_priced_entry
from app.analysis.route_selector import get_priority_destinations, is_long_haul
from app.analysis.destination_updater import update_priority_destinations_in_db
from app.analysis.anomaly_detector import detect_anomaly
from app.analysis.scorer import compute_score
from app.analysis.buckets import bucket_for_duration, stops_allowed
from app.analysis.velocity_detector import save_snapshots_bulk, detect_velocity_drops_bulk, purge_old_snapshots
from app.analysis.cross_airline_comparator import compare_cross_airline, format_competitor_context
from app.scraper.reverify import reverify_flight_price
from app.notifications.aviasales import build_aviasales_url
from app.notifications.dedup import compute_alert_key, ALERT_INHIBIT_HOURS
from app.notifications.telegram import (
    send_deal_alert,
    send_flight_deal_alert,
    send_grouped_flight_alerts,
    send_digest,
    send_admin_report,
    send_admin_alert,
)
from app.api.routes import _get_user_tier
from app.scraper.scraper_health_agent import run_scraper_health_check

logger = logging.getLogger(__name__)


def get_scheduler_jobs() -> list[dict]:
    return [
        # ── VOLS : toutes les 2h (12x/jour) ──
        # Travelpayouts est gratuit et rapide, on scrape TOUS les airports
        # à chaque run pour que les alertes soient réactives.
        *[{
            "id": f"scrape_flights_{h:02d}",
            "func": job_scrape_flights,
            "trigger": "cron",
            "hour": h,
        } for h in [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]],
        # ── VOLS ONE-WAY : toutes les 4h, décalées de 30min du round-trip ──
        # V5 : récupère les aller-simples (outbound + inbound) pour les routes priorité.
        # Cadence + faible que les A/R car volume API plus faible.
        *[{
            "id": f"scrape_oneway_{h:02d}",
            "func": job_scrape_oneway_flights,
            "trigger": "cron",
            "hour": h,
            "minute": 30,
        } for h in [1, 5, 9, 13, 17, 21]],
        # ── TRAVELPAYOUTS ENRICHMENT : 1x/jour a 4h ──
        {
            "id": "travelpayouts_enrichment",
            "func": job_travelpayouts_enrichment,
            "trigger": "cron",
            "hour": 4,
        },
        # ── BASELINES & MAINTENANCE ──
        {
            "id": "recalculate_baselines",
            "func": job_recalculate_baselines,
            "trigger": "cron",
            "hour": settings.BASELINE_RECALC_HOUR,
        },
        {
            "id": "expire_stale_data",
            "func": job_expire_stale_data,
            "trigger": "cron",
            "hour": 5,  # Une fois par jour a 5h suffit
        },
        # ── REVERIFICATION : toutes les 2h ──
        # Re-vérifie les qualified_items actifs dont reverified_at date de plus de 2h.
        # Expire les deals dont le prix n'est plus valide.
        *[{
            "id": f"reverify_active_deals_{h:02d}",
            "func": job_reverify_active_deals,
            "trigger": "cron",
            "hour": h,
            "minute": 45,
        } for h in range(24)],
        {
            "id": "daily_digest",
            "func": job_daily_digest,
            "trigger": "cron",
            "hour": settings.DIGEST_HOUR,
        },
        {
            "id": "daily_admin_report",
            "func": job_daily_admin_report,
            "trigger": "cron",
            "hour": 9,
        },
        # ── TIER 1 : toutes les 20 min (CDG + ORY via endpoints directs LCC) ──
        # Ryanair + Transavia directs → données quasi temps-réel pour les routes chaudes.
        # Polling intensif justifié : ces routes contiennent les mistake fares éphémères.
        *[{
            "id": f"scrape_tier1_{h:02d}h{m:02d}",
            "func": job_scrape_tier1,
            "trigger": "cron",
            "hour": h,
            "minute": m,
        } for h in range(24) for m in [0, 20, 40]],
        # ── DESTINATION SELECTOR : 1x/semaine le lundi a 3h ──
        # Requête Travelpayouts + scoring saisonnier → met à jour priority_destinations en DB
        {
            "id": "update_destinations",
            "func": job_update_destinations,
            "trigger": "cron",
            "day_of_week": "mon",
            "hour": 3,
        },
        # ── STRIPE SYNC : 1x/jour à 6h ──
        # Vérifie les abonnements Stripe actifs et met à jour premium_expires_at.
        {
            "id": "sync_stripe_subscriptions",
            "func": job_sync_stripe_subscriptions,
            "trigger": "cron",
            "hour": 6,
        },
        # ── SCRAPER HEALTH : 1x/jour à 7h ──
        # Vérifie les APIs Transavia et Vueling. Si une API morte revient ou
        # qu'une nouvelle URL est trouvée → réactive le scraper automatiquement.
        {
            "id": "check_scraper_health",
            "func": job_check_scraper_health,
            "trigger": "cron",
            "hour": 7,
        },
        # ── SCRAPER WATCHDOG : toutes les 2h, alerte admin Telegram ──
        # V8.3 : si un scraper tourne mais ne persiste aucune ligne sur 24h,
        # envoie une alerte au TELEGRAM_ADMIN_CHAT_ID. Cooldown 6h/source.
        *[{
            "id": f"scraper_watchdog_{h:02d}",
            "func": job_scraper_watchdog,
            "trigger": "cron",
            "hour": h,
            "minute": 15,  # offset des autres jobs
        } for h in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]],
    ]


async def job_scrape_flights():
    logger.info("Starting flight scraping job")
    started_at = datetime.now(timezone.utc)

    flights, errors, baselines = await scrape_all_flights()

    if not db:
        logger.warning("No database connection, skipping insert")
        return

    # Save bootstrapped baselines from Google Flights price insights
    for baseline in baselines:
        try:
            db.table("price_baselines").upsert(baseline, on_conflict="route_key").execute()
        except Exception as e:
            logger.warning(f"Failed to save baseline: {e}")
    if baselines:
        logger.info(f"Bootstrapped {len(baselines)} baselines from Google Flights price insights")

    inserted = 0
    for idx, flight in enumerate(flights):
        try:
            resp = db.table("raw_flights").upsert(flight, on_conflict="hash").execute()
            # Capture the DB-generated id so _analyze_new_flights can reference it
            # when inserting a qualified_item (item_id column is uuid NOT NULL).
            if resp.data:
                flight["id"] = resp.data[0].get("id")
            inserted += 1
        except Exception as e:
            logger.warning(f"Failed to insert flight: {e}")
            errors += 1
        # Yield the event loop every 10 upserts so HTTP requests
        # (like /health or /api/auth/login) don't stall during big scrapes.
        if idx % 10 == 9:
            await asyncio.sleep(0)

    completed_at = datetime.now(timezone.utc)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    status = "success" if errors == 0 else ("partial" if inserted > 0 else "failed")
    db.table("scrape_logs").insert({
        "actor_id": "flights",
        "source": "google_flights",
        "type": "flights",
        "items_count": inserted,
        "errors_count": errors,
        "duration_ms": duration_ms,
        "status": status,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
    }).execute()

    logger.info(f"Flight scraping complete: {inserted} inserted, {errors} errors")
    await _analyze_new_flights(flights)


async def _analyze_new_flights(flights: list[dict]):
    if not db:
        return

    # Temporary instrumentation: count rejections at each filter step
    counters = {
        "total": len(flights),
        "rejected_no_bucket": 0,
        "rejected_stops": 0,
        "rejected_no_baseline": 0,
        "rejected_low_sample": 0,
        "rejected_no_anomaly": 0,
        "rejected_low_discount_or_z": 0,
        "rejected_reverify": 0,
        "qualified": 0,
    }

    # Accumulate qualified flights to dispatch as grouped alerts after the
    # analysis pass. Each entry: (flight, anomaly, tier).
    qualified_flights: list[tuple[dict, object, str]] = []

    for idx, flight in enumerate(flights):
        # Yield the event loop every 10 flights so HTTP requests
        # don't stall during big analyze passes.
        if idx % 10 == 9:
            await asyncio.sleep(0)

        # Bucket lookup based on trip duration
        days = flight.get("trip_duration_days") or 0
        bucket = bucket_for_duration(days)
        if not bucket:
            counters["rejected_no_bucket"] += 1
            continue

        # Stops rule based on haul type. Missing duration_minutes is treated
        # as short-haul (strictest rule, 0 stops max) to avoid false positives.
        duration_minutes = flight.get("duration_minutes") or 0
        max_stops = stops_allowed(duration_minutes)
        if (flight.get("stops") or 0) > max_stops:
            counters["rejected_stops"] += 1
            continue

        # Lookup baseline — 3-level cascade (most specific → least specific):
        # 1. Seasonal: route + bucket + departure_month + lead_time  (best quality)
        # 2. Legacy:   route + bucket                                (fallback)
        # 3. Dest-wide: any origin + bucket                         (cold-start)
        from app.analysis.baselines import lead_time_bucket as _lt_bucket
        dep_date = flight.get("departure_date") or flight.get("departure_at", "")[:10]
        scraped_at = flight.get("scraped_at", "")
        try:
            month_str = f"m{int(dep_date[5:7]):02d}"
        except (ValueError, IndexError):
            month_str = "m00"
        lt_label = _lt_bucket(dep_date, scraped_at)

        seasonal_key = f"{flight['origin']}-{flight['destination']}-bucket_{bucket}-{month_str}-{lt_label}"
        legacy_key   = f"{flight['origin']}-{flight['destination']}-bucket_{bucket}"
        dest_key     = f"*-{flight['destination']}-bucket_{bucket}"

        baseline = None
        for rk in (seasonal_key, legacy_key, dest_key):
            resp = (
                db.table("price_baselines")
                .select("*")
                .eq("route_key", rk)
                .eq("type", "flight")
                .execute()
            )
            if resp.data:
                baseline = resp.data[0]
                break

        if not baseline:
            counters["rejected_no_baseline"] += 1
            continue
        if (baseline.get("sample_count") or 0) < MIN_SAMPLE_COUNT:
            counters["rejected_low_sample"] += 1
            continue

        # Anomaly detection (existing helper)
        anomaly = detect_anomaly(price=flight["price"], baseline=baseline)
        # Track which qualification path succeeded — needed downstream to
        # measure baseline maturity (fallback share) and to filter analytics.
        qualification_method: str | None = None
        if anomaly:
            qualification_method = f"zscore_{anomaly.alert_level}"
        else:
            # Fallback: qualify on raw discount alone when z-score is unreliable
            # (high variance baselines or young seasonal cells with few samples).
            # A deal ≥40% below avg_price is worth showing regardless of z-score.
            avg = baseline.get("avg_price") or 0
            if avg > 0 and flight["price"] < avg:
                raw_discount = (avg - flight["price"]) / avg * 100
                std = baseline.get("std_dev") or 0
                raw_z = (avg - flight["price"]) / std if std > 0 else 0
                if raw_discount >= 40:
                    from app.analysis.anomaly_detector import QualifiedItem
                    anomaly = QualifiedItem(
                        price=round(flight["price"], 2),
                        baseline_price=round(avg, 2),
                        discount_pct=round(raw_discount, 2),
                        z_score=round(raw_z, 2),
                        alert_level="good_deal",
                    )
                    qualification_method = "fallback_discount"
            if not anomaly:
                counters["rejected_no_anomaly"] += 1
                continue

        # Extra filters on top of detect_anomaly's tiering
        # Qualify if EITHER discount is good (>=15%) OR statistical anomaly is strong (z>=1.5)
        # This avoids over-filtering deals that are either value-driven or statistically rare
        if anomaly.discount_pct < 15 and anomaly.z_score < 1.5:
            counters["rejected_low_discount_or_z"] += 1
            continue

        # Real-time re-verification — reject silently if the deal is gone
        if not await reverify_flight_price(flight):
            counters["rejected_reverify"] += 1
            continue

        counters["qualified"] += 1

        # Tier classification: ≥50% → premium (masked for free users)
        tier = "premium" if anomaly.discount_pct >= 50 else "free"

        score = compute_score(
            discount_pct=anomaly.discount_pct,
            destination_code=flight["destination"],
            date_flexibility=0,
            accommodation_rating=None,
        )

        # item_id must be a valid UUID; skip if we couldn't capture it at upsert time
        flight_id = flight.get("id")
        if not flight_id:
            logger.warning(f"Skipping qualified_item insert: missing flight id for {flight['origin']}->{flight['destination']}")
            continue

        # Cross-airline comparison — only meaningful for Tier 1 sources
        # (ryanair_direct / transavia_direct). Tier 2 (Travelpayouts) flights
        # don't have per-airline snapshots to compare against.
        competitor_prices = None
        source = flight.get("source", "")
        if source in ("ryanair_direct", "transavia_direct"):
            comparison = compare_cross_airline(db, flight)
            if comparison and comparison.signal != "none":
                competitor_prices = comparison.to_dict()
                # Stash comparison on flight dict so dispatch can use it for
                # Telegram message context without re-querying.
                flight["_comparison"] = comparison

        now_utc = datetime.now(timezone.utc).isoformat()
        qualified_item_row = {
            "type": "flight",
            "item_id": flight_id,
            "price": anomaly.price,
            "baseline_price": anomaly.baseline_price,
            "discount_pct": anomaly.discount_pct,
            "score": score,
            "tier": tier,
            "status": "active",
            "reverified_at": now_utc,
            "qualification_method": qualification_method or "unknown",
        }
        if competitor_prices is not None:
            qualified_item_row["competitor_prices"] = competitor_prices

        # Upsert: if this raw_flight already has an active qualified_item, update
        # price/score/reverified_at in place instead of inserting a duplicate row.
        # The unique constraint on item_id (migration 021) enforces this at DB level.
        db.table("qualified_items").upsert(
            qualified_item_row, on_conflict="item_id"
        ).execute()

        # Defer flight alert dispatch: accumulate and send as grouped alerts
        # (by origin+destination) after the analysis pass completes. This lets
        # us batch multiple offers per destination into a single Telegram msg
        # and apply deal-level dedup via the sent_alerts table.
        if score >= settings.MIN_SCORE_ALERT:
            # Stash score back on the flight dict so the grouped dispatcher
            # can surface it in offers without re-computing.
            flight["score"] = score
            # Propagate qualification_method for downstream click-tracking
            # analytics (CTR breakdown by qualification path).
            flight["_qualification_method"] = qualification_method or "unknown"
            qualified_flights.append((flight, anomaly, tier))

    logger.info(f"Analyze pipeline counters: {counters}")
    logger.info(f"Dispatching {len(qualified_flights)} qualified flights for alert delivery")

    await _dispatch_grouped_flight_alerts(qualified_flights)


async def _dispatch_velocity_alerts(flights: list[dict]):
    """Dispatch velocity-detected mistake fares immediately.

    These bypass the normal z-score qualification because:
    1. A 40-60% price drop in < 2h is a near-certain mistake fare signal
    2. These deals last 2-8h max — waiting for the 2h Travelpayouts cycle would miss them
    3. Re-verification still runs to confirm the price is still live

    Uses the same grouped dispatch and dedup logic as the normal pipeline."""
    if not db or not flights:
        return

    # Re-verify each flight before dispatching
    verified: list[tuple[dict, object, str]] = []
    for flight in flights:
        if not await reverify_flight_price(flight):
            logger.info(
                f"Velocity alert rejected by reverify: "
                f"{flight['origin']}->{flight['destination']} {flight.get('departure_date')}"
            )
            continue

        drop_pct = float(flight.get("velocity_drop_pct") or 0)
        ref_price = float(flight.get("velocity_reference_price") or flight["price"])
        alert_level = flight.get("ai_alert_level", "fare_mistake")

        # Create a synthetic anomaly-like object for the dispatch pipeline
        from app.analysis.anomaly_detector import QualifiedItem
        anomaly = QualifiedItem(
            price=float(flight["price"]),
            baseline_price=ref_price,
            discount_pct=round(drop_pct, 1),
            z_score=99.0,  # Sentinel: velocity alerts always pass z-score gate
            alert_level=alert_level,
        )

        score = compute_score(
            discount_pct=drop_pct,
            destination_code=flight["destination"],
            date_flexibility=0,
            accommodation_rating=None,
        )
        flight["score"] = score
        tier = "premium"  # Velocity alerts are always premium (high-value)

        # Cross-airline comparison for velocity alerts (Tier 1 only)
        source = flight.get("source", "")
        if source in ("ryanair_direct", "transavia_direct"):
            comparison = compare_cross_airline(db, flight)
            if comparison and comparison.signal != "none":
                flight["_comparison"] = comparison

        verified.append((flight, anomaly, tier))

    if verified:
        logger.info(f"Dispatching {len(verified)} verified velocity alerts")
        await _dispatch_grouped_flight_alerts(verified)


def _deal_label(discount_pct: float) -> str:
    """Return a human-readable deal tier label for Telegram teaser messages."""
    if discount_pct >= 60:
        return "🔴 ERREUR DE PRIX"
    elif discount_pct >= 40:
        return "🟠 PROMO FLASH"
    else:
        return "🟡 BON DEAL"


async def _dispatch_grouped_flight_alerts(
    qualified_flights: list[tuple[dict, object, str]],
) -> None:
    """Group qualified flights by (origin, destination) and dispatch a single
    Telegram alert per user per destination via send_grouped_flight_alerts.
    Deals already present in sent_alerts (per user) are skipped. Successful
    sends are persisted back to sent_alerts for cross-run dedup.
    """
    if not db or not qualified_flights:
        return

    groups: dict[tuple[str, str], list[tuple[dict, object, str]]] = defaultdict(list)
    for flight, anomaly, tier in qualified_flights:
        groups[(flight["origin"], flight["destination"])].append((flight, anomaly, tier))

    origins = list({o for (o, _) in groups.keys()})
    if not origins:
        return

    # Fetch users with Telegram enabled who track any of these airports.
    # alerts_paused_until is fetched optimistically: if the column doesn't exist yet
    # (migration 012 not applied), we fall back to a SELECT without it so alerts
    # still flow — pause feature simply degrades gracefully until migration is applied.
    all_prefs = []
    try:
        prefs_resp = (
            db.table("user_preferences")
            .select("user_id,telegram_chat_id,telegram_connected,airport_codes,alerts_paused_until,deal_tier,blocked_destinations,flight_trip_types")
            .eq("telegram_connected", True)
            .execute()
        )
        all_prefs = prefs_resp.data or []
    except Exception as e:
        err_msg = str(e)
        if any(col in err_msg for col in ("alerts_paused_until", "deal_tier", "blocked_destinations", "flight_trip_types")):
            logger.warning("Migration not yet applied — fetching prefs without optional columns")
            try:
                prefs_resp = (
                    db.table("user_preferences")
                    .select("user_id,telegram_chat_id,telegram_connected,airport_codes")
                    .eq("telegram_connected", True)
                    .execute()
                )
                all_prefs = prefs_resp.data or []
            except Exception as e2:
                logger.warning(f"Failed to fetch user preferences: {e2}")
                return
        else:
            logger.warning(f"Failed to fetch user preferences: {e}")
            return

    # Bulk-fetch active wishlists for all routes present in this batch
    # keyed by user_id → list of {origin, destination, max_price, month}
    wishlists_by_user: dict[str, list[dict]] = {}
    try:
        route_origins = list({o for (o, _) in groups.keys()})
        wl_resp = (
            db.table("destination_wishlists")
            .select("user_id,origin,destination,max_price,month")
            .eq("active", True)
            .in_("origin", route_origins)
            .execute()
        )
        for wl in (wl_resp.data or []):
            if not isinstance(wl, dict):
                continue
            uid = wl.get("user_id")
            if uid:
                wishlists_by_user.setdefault(uid, []).append(wl)
    except Exception as e:
        logger.warning(f"Failed to fetch destination_wishlists: {e}")

    # Filter: keep only users who track at least one of the origin airports
    subs = []
    for pref in all_prefs:
        if not isinstance(pref, dict):
            continue
        airports = pref.get("airport_codes", [])
        if not isinstance(airports, list):
            continue
        tracked_origins = [o for o in origins if o in airports]
        if not tracked_origins or not pref.get("telegram_chat_id"):
            continue
        for origin in tracked_origins:
            subs.append({
                "user_id": pref.get("user_id"),
                "chat_id": pref.get("telegram_chat_id"),
                "airport_code": origin,
            })

    if not subs:
        return

    # Build per-user lookups from the preferences we already fetched
    paused_until_by_user: dict[str, str] = {}
    deal_tier_by_user: dict[str, str] = {}
    blocked_by_user: dict[str, set] = {}
    trip_types_by_user: dict[str, set[str]] = {}
    for pref in all_prefs:
        if isinstance(pref, dict) and pref.get("user_id"):
            uid = pref["user_id"]
            if pref.get("alerts_paused_until"):
                paused_until_by_user[uid] = pref["alerts_paused_until"]
            deal_tier_by_user[uid] = pref.get("deal_tier") or "regular"
            blocked = pref.get("blocked_destinations") or []
            if blocked:
                blocked_by_user[uid] = set(blocked)
            # V5: flight trip type filter — default to round-trip only
            # to preserve pre-V5 behaviour for migrated users.
            trip_types_by_user[uid] = set(pref.get("flight_trip_types") or ["round_trip"])

    # V7: track premium teasers sent this run as a fast in-memory dedup
    # (the persistent dedup uses sent_alerts.alert_type='teaser_premium' with
    # a 7-day window). The 'limit reached' teaser was removed in V7.
    teaser_sent_premium: set[str] = set()
    # Track best price already dispatched per (user_id, destination, dep_date, ret_date)
    # this run. When a user tracks multiple origins (CDG + ORY + BVA) and the same
    # itinerary appears from several airports, only send the cheapest one.
    # Key: (user_id, dest, dep_date, ret_date) → best price sent
    dispatched_this_run: dict[tuple, float] = {}

    # V8.2: accumulate offers per (user, destination) BEFORE sending so a
    # user who tracks several origins (CDG + ORY + BVA) gets ONE Telegram
    # message with all matching dates from all of their airports, instead
    # of one message per origin. The send happens after the subs loop.
    # Schema:
    #   pending[(user_id, destination)] = {
    #     "chat_id": str, "tier": str, "user_id": str,
    #     "offers": [offer dicts ...],
    #     "keys_to_store": [alert_keys ...],
    #     "best_origin": str,  # the origin of the cheapest offer (header reference)
    #   }
    pending_by_user_dest: dict[tuple[str, str], dict] = {}

    for sub in subs:
        if not isinstance(sub, dict):
            continue
        try:
            user_id = sub.get("user_id")
            # Resolve tier first — needed by all subsequent gates.
            # On error, default to "free" but mark tier_error so teasers are suppressed.
            tier_error = False
            try:
                sub_tier = _get_user_tier(user_id) if user_id else "free"
            except Exception as e:
                logger.warning(f"Failed to resolve tier for {user_id}: {e}")
                sub_tier = "free"
                tier_error = True
            # Pause gate — skip entirely if alerts are muted
            if user_id and user_id in paused_until_by_user:
                paused_ts = paused_until_by_user[user_id]
                try:
                    paused_dt = datetime.fromisoformat(paused_ts.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) < paused_dt:
                        continue
                except (ValueError, TypeError):
                    pass

            sub_origin = sub.get("airport_code")
            chat_id = sub.get("chat_id")
            if not sub_origin or chat_id is None:
                continue

            # Free tier weekly quota — sourced from app.thresholds
            from app.thresholds import FREE_TIER_WEEKLY_LIMIT
            weekly_sent_count = 0
            if sub_tier == "free" and user_id:
                week_start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                try:
                    wk_resp = (
                        db.table("sent_alerts")
                        .select("alert_key", count="exact")
                        .eq("user_id", user_id)
                        .gte("created_at", week_start)
                        .execute()
                    )
                    weekly_sent_count = wk_resp.count or 0
                except Exception as e:
                    logger.warning(f"Failed to count weekly alerts for {user_id}: {e}")

            for (grp_origin, grp_dest), flight_tuples in groups.items():
                if grp_origin != sub_origin:
                    continue

                # Skip destinations the user has blocked
                if user_id and grp_dest in blocked_by_user.get(user_id, set()):
                    continue

                # Wishlist matching: check if this (origin, destination) is in any
                # of the user's active wishlists — bypass standard discount gates
                # and use the price target instead.
                user_wishlists = wishlists_by_user.get(user_id, []) if user_id else []
                matching_wl = None
                for wl in user_wishlists:
                    if wl.get("origin") == grp_origin and wl.get("destination") == grp_dest:
                        # Month filter: if the wishlist specifies a month, the
                        # departure must fall in that month.
                        wl_month = wl.get("month")
                        if wl_month is not None:
                            # Check against the cheapest flight's departure date
                            best_flight = min(
                                flight_tuples,
                                key=lambda t: t[0].get("price", 9999),
                                default=None,
                            )
                            if best_flight:
                                try:
                                    dep_month = datetime.fromisoformat(
                                        best_flight[0]["departure_date"]
                                    ).month
                                    if dep_month != wl_month:
                                        continue
                                except (ValueError, KeyError, TypeError):
                                    continue
                        matching_wl = wl
                        break

                # Build candidate list
                # Only deals ≥40% pass for everyone.
                # Free:    [40, 50)   → full info (max 3/week)
                #          [50, 60)   → silent skip (no signal at all)
                #          ≥60        → masked teaser, at most 1/week (strict)
                # Premium: ≥40        → full info, no limit
                # Thresholds sourced from app.thresholds (single source of truth).
                from app.thresholds import (
                    FREE_TIER_FULL_MAX_DISCOUNT_PCT as FREE_TIER_FULL_MAX,
                    FREE_TIER_TEASER_MIN_DISCOUNT_PCT as FREE_TIER_TEASER_MIN,
                    GLOBAL_MIN_DISCOUNT_PCT as GLOBAL_MIN_DISCOUNT,
                )

                # V5: per-user trip-type filter. Default to round-trip-only
                # so existing users keep their current Telegram experience.
                user_allowed_trip_types = trip_types_by_user.get(user_id or "", {"round_trip"})

                candidates: list[tuple[str | None, dict, object, str]] = []
                for flight, anomaly, tier in flight_tuples:
                    flight_trip_type = flight.get("trip_type") or "round_trip"
                    if flight_trip_type not in user_allowed_trip_types:
                        continue
                    if matching_wl is not None:
                        max_price = matching_wl.get("max_price")
                        if max_price is not None and flight.get("price", 9999) > max_price:
                            continue
                    else:
                        if anomaly.discount_pct < GLOBAL_MIN_DISCOUNT:
                            continue
                        # V7: free users get full alerts ONLY for discounts
                        # below FREE_TIER_FULL_MAX (50%). Deals ≥50% are
                        # routed entirely through the teaser path below
                        # — never as a full alert. Premium users keep all
                        # candidates.
                        if sub_tier == "free" and anomaly.discount_pct >= FREE_TIER_FULL_MAX:
                            continue
                    key = None
                    if user_id:
                        key = compute_alert_key(
                            user_id,
                            flight["origin"],
                            flight["destination"],
                            flight["departure_date"],
                            flight["return_date"],
                            flight["price"],
                        )
                    candidates.append((key, flight, anomaly, tier))

                if not candidates:
                    continue

                # V7: Free tier — deals ≥60% → masked teaser, ≤1/week strict.
                # Strict 7-day window: we look up sent_alerts for a row of
                # alert_type='teaser_premium' on this user; if found we skip.
                # Run-local set is a fast path to avoid re-querying within
                # the same dispatch pass.
                if (
                    sub_tier == "free" and not tier_error and chat_id is not None
                    and user_id and user_id not in teaser_sent_premium
                ):
                    masked = [
                        (f, a) for f, a, _ in flight_tuples
                        if a.discount_pct >= FREE_TIER_TEASER_MIN
                        and (f.get("trip_type") or "round_trip") in user_allowed_trip_types
                    ]
                    if masked:
                        # Weekly dedup: did we already send a teaser_premium
                        # to this user in the last 7 days?
                        already_teased = False
                        try:
                            week_start_iso = (
                                datetime.now(timezone.utc) - timedelta(days=7)
                            ).isoformat()
                            tz_resp = (
                                db.table("sent_alerts")
                                .select("alert_key", count="exact")
                                .eq("user_id", user_id)
                                .eq("alert_type", "teaser_premium")
                                .gte("created_at", week_start_iso)
                                .execute()
                            )
                            already_teased = (tz_resp.count or 0) > 0
                        except Exception as e:
                            logger.warning(
                                f"teaser_premium weekly dedup lookup failed for {user_id}: {e}"
                            )

                        if not already_teased:
                            teaser_sent_premium.add(user_id)
                            best_f, best_a = max(masked, key=lambda x: x[1].discount_pct)
                            sent_ok = False
                            try:
                                from app.notifications.telegram import _get_bot
                                bot = _get_bot()
                                if bot:
                                    await bot.send_message(
                                        chat_id=chat_id,
                                        text=(
                                            f"🔥 Deal exceptionnel détecté\n\n"
                                            f"🌍 ██████ → ██████\n"
                                            f"💰 ███€  ·  -{int(best_a.discount_pct)}%\n\n"
                                            f"Les détails sont réservés aux membres premium.\n"
                                            f"💎 Débloquer → {settings.FRONTEND_URL}/premium"
                                        ),
                                    )
                                    sent_ok = True
                            except Exception as e:
                                logger.warning(f"teaser_premium send failed for {user_id}: {e}")

                            # Persist a sent_alerts row so the next dispatch
                            # within 7 days will see already_teased=True.
                            if sent_ok:
                                try:
                                    db.table("sent_alerts").insert({
                                        "user_id": user_id,
                                        "chat_id": chat_id,
                                        "alert_key": f"teaser_premium:{user_id}:{int(datetime.now(timezone.utc).timestamp())}",
                                        "destination": best_f.get("destination", ""),
                                        "alert_type": "teaser_premium",
                                    }).execute()
                                except Exception as e:
                                    logger.warning(
                                        f"teaser_premium persistence failed for {user_id}: {e}"
                                    )

                # V7: weekly-quota teaser ('limit reached') — REMOVED.
                # The teaser_premium above already does the upsell signal;
                # a second 'limit reached' message was redundant.
                # Free users still get hard-capped at FREE_TIER_WEEKLY_LIMIT
                # full alerts (the existing free_unlocked counting handles it).
                if sub_tier == "free" and matching_wl is None and weekly_sent_count >= FREE_TIER_WEEKLY_LIMIT:
                    continue

                already_keys: set[str] = set()
                if user_id:
                    keys_to_check = list({k for (k, _, _, _) in candidates if k})
                    if keys_to_check:
                        try:
                            inhibit_since = (
                                datetime.now(timezone.utc)
                                - timedelta(hours=ALERT_INHIBIT_HOURS)
                            ).isoformat()
                            sent_resp = (
                                db.table("sent_alerts")
                                .select("alert_key")
                                .eq("user_id", user_id)
                                .in_("alert_key", keys_to_check)
                                .gte("created_at", inhibit_since)
                                .execute()
                            )
                            for row in (sent_resp.data or []):
                                if isinstance(row, dict) and row.get("alert_key"):
                                    already_keys.add(row["alert_key"])
                        except Exception as e:
                            logger.warning(
                                f"Failed sent_alerts check for {user_id}: {e}"
                            )

                offers: list[dict] = []
                keys_to_store: list[str] = []
                group_tier = "free"
                for key, flight, anomaly, tier in candidates:
                    if key and key in already_keys:
                        continue

                    # Filter: minimum 4 days stay
                    try:
                        departure = datetime.fromisoformat(flight["departure_date"])
                        return_date = datetime.fromisoformat(flight["return_date"])
                        nights = (return_date - departure).days
                        if nights < 4:
                            continue  # Skip trips shorter than 4 days
                    except (ValueError, KeyError, TypeError):
                        continue  # Skip if dates invalid

                    offer: dict = {
                        "departure_date": flight["departure_date"],
                        "return_date": flight["return_date"],
                        "price": flight["price"],
                        "baseline_price": anomaly.baseline_price,
                        "origin": flight["origin"],
                        "discount_pct": anomaly.discount_pct,
                        "score": flight.get("score", 0),
                        "airline": flight.get("airline", ""),
                        # Propagate the qualification path so click tracking
                        # can break CTR down by zscore_* vs fallback_discount.
                        "qualification_method": flight.get("_qualification_method"),
                        "booking_url": build_aviasales_url(
                            flight["origin"],
                            flight["destination"],
                            flight["departure_date"],
                            flight["return_date"],
                            marker=settings.TRAVELPAYOUTS_MARKER or None,
                        ),
                    }
                    # Attach cross-airline context if available
                    comparison = flight.get("_comparison")
                    if comparison:
                        ctx = format_competitor_context(comparison)
                        if ctx:
                            offer["competitor_context"] = ctx
                    offers.append(offer)
                    if key:
                        keys_to_store.append(key)
                    if tier == "premium":
                        group_tier = "premium"

                if not offers:
                    continue

                # V8.2: accumulate this (user, dest) bucket. We send AFTER
                # the subs loop so a user with multiple origins gets one
                # merged Telegram alert covering all their airports.
                bucket_key = (user_id or "", grp_dest)
                bucket = pending_by_user_dest.get(bucket_key)
                if bucket is None:
                    bucket = pending_by_user_dest[bucket_key] = {
                        "chat_id": chat_id,
                        "tier": sub_tier,
                        "user_id": user_id,
                        "offers": [],
                        "keys_to_store": [],
                        "best_origin": grp_origin,
                        "best_price": float("inf"),
                    }
                bucket["offers"].extend(offers)
                bucket["keys_to_store"].extend(keys_to_store)
                cheapest = min(o["price"] for o in offers)
                if cheapest < bucket["best_price"]:
                    bucket["best_price"] = cheapest
                    bucket["best_origin"] = grp_origin
                # Always upgrade tier to premium if any sub for this user
                # is premium (rare but possible mid-tier transition).
                if sub_tier == "premium":
                    bucket["tier"] = "premium"
        except Exception as e:
            logger.warning(f"Grouped dispatch error for subscriber: {e}")

        await asyncio.sleep(0)

    # V8.2: flush accumulated alerts. ONE message per (user, destination).
    for (uid, grp_dest), bucket in pending_by_user_dest.items():
        offers = bucket["offers"]
        if not offers:
            continue
        # Dedup offers by (origin, departure_date, return_date, price_bucket)
        # — when overlapping subs produced the same flight twice.
        seen_offer_keys: set[tuple] = set()
        unique_offers: list[dict] = []
        for o in offers:
            k = (o.get("origin"), o.get("departure_date"), o.get("return_date"), int(o.get("price", 0)) // 50)
            if k in seen_offer_keys:
                continue
            seen_offer_keys.add(k)
            unique_offers.append(o)
        offers = unique_offers
        if not offers:
            continue

        # Sort by discount descending so the most attractive deal lands first.
        offers.sort(key=lambda o: -(o.get("discount_pct") or 0))

        chat_id = bucket["chat_id"]
        sub_tier = bucket["tier"]
        keys_to_store = list(set(bucket["keys_to_store"]))
        best_origin = bucket["best_origin"]
        origin_city = iata_label(best_origin)
        dest_city = iata_label(grp_dest)

        success = False
        try:
            success = await send_grouped_flight_alerts(
                chat_id=chat_id,
                origin_city=origin_city,
                dest_city=dest_city,
                destination_iata=grp_dest,
                offers=offers,
                tier=sub_tier,
                user_id=uid or None,
                alert_key=keys_to_store[0] if keys_to_store else None,
                origin_iata=best_origin,
            )
            if success:
                logger.info(
                    f"✅ V8.2 sent merged alert: {len(offers)} offers, "
                    f"{len({o.get('origin') for o in offers})} origins → {grp_dest} "
                    f"for user {uid}"
                )
                dispatched_this_run[(uid or "", grp_dest)] = bucket["best_price"]
        except Exception as e:
            logger.warning(f"V8.2 merged dispatch failed for {uid}/{grp_dest}: {e}")
            success = False

        if success and uid and keys_to_store:
            rows = [{
                "user_id": uid,
                "chat_id": chat_id,
                "alert_key": k,
                "destination": grp_dest,
                "alert_type": "flight",
            } for k in keys_to_store]
            try:
                db.table("sent_alerts").upsert(
                    rows, on_conflict="user_id,alert_key"
                ).execute()
            except Exception as e:
                logger.warning(f"Failed to upsert sent_alerts: {e}")


async def job_recalculate_baselines():
    logger.info("Starting baseline recalculation")
    if not db:
        return

    now = datetime.now(timezone.utc)
    thirty_days_ago = (now - timedelta(days=30)).isoformat()

    # Paginate: Supabase defaults to a 1000-row cap per request. Older rows
    # (inserted before the trip_duration_days migration) have NULL and are
    # useless for bucket baselines, so we filter them out at the source.
    # We also page through up to 10k rows to cover the full 30-day window.
    flights_data: list[dict] = []
    page_size = 1000
    for offset in range(0, 10000, page_size):
        page = (
            db.table("raw_flights")
            .select("origin, destination, price, scraped_at, trip_duration_days, stops, duration_minutes, departure_date")
            .gte("scraped_at", thirty_days_ago)
            .not_.is_("trip_duration_days", "null")
            .order("scraped_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = page.data or []
        flights_data.extend(rows)
        if len(rows) < page_size:
            break

    logger.info(f"Recalculate: fetched {len(flights_data)} flights with trip_duration_days")

    routes: dict[str, list] = {}
    for f in flights_data:
        key = f"{f['origin']}-{f['destination']}"
        routes.setdefault(key, []).append(f)

    flight_baselines_published = 0
    for idx, (route_key_prefix, observations) in enumerate(routes.items()):
        baselines = compute_baselines_by_bucket(route_key_prefix, observations)
        for baseline in baselines:
            try:
                db.table("price_baselines").upsert(baseline, on_conflict="route_key").execute()
                flight_baselines_published += 1
            except Exception as e:
                logger.warning(f"Failed to upsert baseline {baseline['route_key']}: {e}")
        # Yield the event loop every 5 routes to keep HTTP requests responsive.
        if idx % 5 == 4:
            await asyncio.sleep(0)

    logger.info(f"Recalculated {flight_baselines_published} flight bucket baselines from {len(routes)} routes")


async def job_expire_stale_data():
    if not db:
        return
    now = datetime.now(timezone.utc).isoformat()

    # Expire qualified items older than 24h (they don't have expires_at)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    db.table("qualified_items").update({"status": "expired"}).eq("status", "active").lt("created_at", yesterday).execute()

    logger.info("Expired stale qualified items")

    # Purge price_snapshots older than 24h (velocity detector data)
    purge_old_snapshots(db)


async def job_daily_digest():
    if not db:
        return

    deals_resp = (
        db.table("qualified_items")
        .select("*")
        .eq("status", "active")
        .eq("type", "flight")
        .gte("score", settings.MIN_SCORE_DIGEST)
        .order("score", desc=True)
        .limit(5)
        .execute()
    )

    if not deals_resp.data:
        return

    subscribers = db.table("telegram_subscribers").select("chat_id").execute()
    for sub in (subscribers.data or []):
        await send_digest(sub["chat_id"], deals_resp.data)


async def job_daily_admin_report():
    if not db:
        return

    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).isoformat()

    logs = db.table("scrape_logs").select("*").gte("started_at", yesterday).execute()
    log_data = logs.data or []

    flight_scrapes = sum(1 for l in log_data if l["type"] == "flights")
    acc_scrapes = sum(1 for l in log_data if l["type"] == "accommodations")
    total_flights = sum(l.get("items_count", 0) for l in log_data if l["type"] == "flights")
    total_acc = sum(l.get("items_count", 0) for l in log_data if l["type"] == "accommodations")
    errors = sum(l.get("errors_count", 0) for l in log_data)

    packages_resp = db.table("packages").select("id", count="exact").gte("created_at", yesterday).execute()
    pkg_count = packages_resp.count or 0

    total_scraped = total_flights + total_acc
    qual_rate = round(pkg_count / total_scraped * 100, 1) if total_scraped > 0 else 0

    baselines_resp = db.table("price_baselines").select("id", count="exact").execute()

    stats = {
        "flight_scrapes": flight_scrapes,
        "accommodation_scrapes": acc_scrapes,
        "total_flights": total_flights,
        "total_accommodations": total_acc,
        "errors": errors,
        "packages_qualified": pkg_count,
        "qualification_rate": qual_rate,
        "alerts_sent": 0,
        "active_baselines": baselines_resp.count or 0,
    }

    await send_admin_report(stats)

    if qual_rate < 5 and total_scraped > 0:
        await send_admin_alert(f"Taux qualification bas : {qual_rate}%")


async def job_scrape_tier1():
    """Tier 1 scrape — Ryanair + Transavia + Vueling direct endpoints, every 20 min."""
    started_at = datetime.now(timezone.utc)
    logger.info("Starting Tier 1 scrape (Ryanair + Transavia + Vueling direct)")
    if not db:
        return

    flights, errors = await scrape_all_tier1()

    if not flights:
        logger.info("Tier 1 scrape: no flights returned")
        return

    inserted = 0
    skipped = 0
    velocity_alerts: list[dict] = []

    # --- Velocity detection: bulk snapshot insert + bulk drop detection ---
    # Two DB round-trips total for the whole batch (was 2N previously).
    save_snapshots_bulk(db, flights)
    v_alerts = detect_velocity_drops_bulk(db, flights)
    for v_alert in v_alerts:
        # Find the matching flight dict to annotate it
        for flight in flights:
            dep = flight.get("departure_date") or flight.get("departure_at", "")[:10]
            ret = flight.get("return_date") or flight.get("return_at", "")[:10]
            if (
                flight["origin"] == v_alert.origin
                and flight["destination"] == v_alert.destination
                and dep == v_alert.departure_date
                and ret == v_alert.return_date
            ):
                velocity_alerts.append({
                    **flight,
                    "ai_alert_level": v_alert.alert_level,
                    "velocity_drop_pct": v_alert.drop_pct,
                    "velocity_reference_price": v_alert.reference_price,
                })
                break

    for flight in flights:
        try:
            result = (
                db.table("raw_flights")
                .upsert(flight, on_conflict="hash")
                .execute()
            )
            if result.data:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            logger.warning(f"Tier1 insert error: {e}")

    completed_at = datetime.now(timezone.utc)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)
    t1_status = "success" if errors == 0 else ("partial" if inserted > 0 else "failed")
    try:
        db.table("scrape_logs").insert({
            "actor_id": "tier1",
            "source": "ryanair+transavia+vueling",
            "type": "flights",
            "items_count": inserted,
            "errors_count": errors,
            "duration_ms": duration_ms,
            "status": t1_status,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to write tier1 scrape_log: {e}")

    logger.info(
        f"Tier 1 scrape done: {inserted} inserted, {skipped} skipped (dupes), "
        f"{errors} errors, {len(velocity_alerts)} velocity alerts, {duration_ms}ms"
    )

    # --- Dispatch velocity alerts immediately (bypass normal 2h window) ---
    if velocity_alerts:
        logger.info(f"Dispatching {len(velocity_alerts)} velocity alerts immediately")
        await _dispatch_velocity_alerts(velocity_alerts)

    # --- Run qualification pipeline on all fresh Tier 1 data ---
    if inserted > 0:
        await job_qualify_and_alert()


async def job_qualify_and_alert():
    """Run the qualification + alert dispatch pipeline on flights scraped in the last 30 min.

    Called by job_scrape_tier1 after each Tier 1 scrape so mistake fares trigger
    alerts within minutes rather than waiting for the next 2h Travelpayouts window."""
    logger.info("Running qualification + alert pipeline (Tier 1 trigger)")
    if not db:
        return

    now = datetime.now(timezone.utc)
    thirty_min_ago = (now - timedelta(minutes=30)).isoformat()

    resp = (
        db.table("raw_flights")
        .select("*")
        .gte("scraped_at", thirty_min_ago)
        .execute()
    )
    flights = resp.data or []
    if not flights:
        return

    logger.info(f"Qualify pipeline (Tier 1): {len(flights)} recent flights to evaluate")
    await _analyze_new_flights(flights)


async def job_scrape_oneway_flights():
    """V5: scrape one-way flights for priority routes via Travelpayouts.

    Two passes per route: outbound (home → destination) + inbound (destination → home).
    Inserts into raw_flights with trip_type='one_way' and the matching direction.
    Cadence: every 4h (offset 30min from round-trip job) — half the volume of the
    round-trip job since one-way is opt-in and we lighten the API load."""
    logger.info("Starting one-way flight scraping job (V5)")
    started_at = datetime.now(timezone.utc)

    if not db or not settings.TRAVELPAYOUTS_TOKEN:
        logger.warning("DB or Travelpayouts token not configured — skipping one-way scrape")
        return

    destinations = get_priority_destinations(max_count=40, db=db)
    inserted = 0
    errors = 0

    for origin in settings.MVP_AIRPORTS:
        for dest in destinations:
            if dest == origin:
                continue
            if is_long_haul(dest) and origin != "CDG":
                continue

            for direction in ("outbound", "inbound"):
                api_origin = origin if direction == "outbound" else dest
                api_destination = dest if direction == "outbound" else origin

                try:
                    api_entries = get_oneway_calendar(api_origin, api_destination)
                except Exception as e:
                    logger.warning(
                        f"One-way fetch failed {api_origin}->{api_destination}: {e}"
                    )
                    errors += 1
                    continue

                for entry in api_entries:
                    departure_at = entry.get("departure_at") or ""
                    if not departure_at:
                        continue
                    try:
                        flight = normalize_flight(
                            {
                                "origin": api_origin,
                                "destination": api_destination,
                                "departureDate": departure_at[:10],
                                "returnDate": None,
                                "price": entry.get("price", 0),
                                "currency": "EUR",
                                "airline": entry.get("airline"),
                                "stops": entry.get("transfers", 0),
                                "tripType": "one_way",
                                "direction": direction,
                            },
                            source="travelpayouts",
                        )
                        db.table("raw_flights").upsert(
                            flight, on_conflict="hash"
                        ).execute()
                        inserted += 1
                    except Exception as e:
                        logger.warning(f"One-way insert failed: {e}")
                        errors += 1

            # Yield event loop after each route (both directions) so HTTP requests
            # don't stall during the scrape pass.
            await asyncio.sleep(0)

    completed_at = datetime.now(timezone.utc)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)
    status = "success" if errors == 0 else ("partial" if inserted > 0 else "failed")

    try:
        db.table("scrape_logs").insert({
            "actor_id": "flights_oneway",
            "source": "travelpayouts",
            "type": "flights",
            "items_count": inserted,
            "errors_count": errors,
            "duration_ms": duration_ms,
            "status": status,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to write one-way scrape_log: {e}")

    logger.info(
        f"One-way scrape complete: {inserted} inserted, {errors} errors, {duration_ms}ms"
    )

    # V5+ P1: detect standalone one-way deals (option C — pre-baseline,
    # discount vs 30-day median).
    if inserted > 0:
        try:
            await _detect_and_dispatch_oneway_alerts()
        except Exception as e:
            logger.warning(f"One-way detection failed: {e}")

    # V5+: scan freshly-scraped one-way data for split-ticket combos
    if inserted > 0:
        try:
            await _detect_and_dispatch_split_ticket_combos()
        except Exception as e:
            logger.warning(f"Split-ticket detection failed: {e}")


async def _detect_and_dispatch_oneway_alerts() -> None:
    """V5+ P1: scan recent one-way rows for standalone deals.

    For each (origin, destination, direction) seen in the last 24h, fetch
    the 30-day price history and run the qualifier. Qualified rows are
    persisted to qualified_items (with qualification_method='oneway_discount')
    and dispatched as Telegram alerts to users who opted in to one_way in
    flight_trip_types.
    """
    if not db:
        return

    from app.analysis.oneway_qualifier import qualify_oneway
    from app.notifications.telegram import send_oneway_deal_alert
    from app.thresholds import (
        ONEWAY_MEDIAN_LOOKBACK_DAYS,
    )

    now = datetime.now(timezone.utc)
    fresh_cutoff = (now - timedelta(hours=24)).isoformat()
    history_cutoff = (now - timedelta(days=ONEWAY_MEDIAN_LOOKBACK_DAYS)).isoformat()

    # Fetch users who opted in to one_way alerts (single round-trip).
    opt_in_subs: list[dict] = []
    try:
        prefs_resp = (
            db.table("user_preferences")
            .select("user_id,telegram_chat_id,airport_codes,flight_trip_types,blocked_destinations")
            .eq("telegram_connected", True)
            .execute()
        )
        for pref in (prefs_resp.data or []):
            ftt = pref.get("flight_trip_types") or ["round_trip"]
            if "one_way" in ftt and pref.get("telegram_chat_id"):
                opt_in_subs.append(pref)
    except Exception as e:
        logger.warning(f"One-way: failed to load opt-in users: {e}")
        return

    if not opt_in_subs:
        logger.info("One-way: no users opted in, skipping detection")
        return

    # Pull the freshest one-way candidates of the last 24h. We cap at 200 to
    # avoid scanning the entire one-way table on each run.
    try:
        cand_resp = (
            db.table("raw_flights")
            .select("id,origin,destination,departure_date,direction,price,airline,source_url,scraped_at")
            .eq("trip_type", "one_way")
            .gte("scraped_at", fresh_cutoff)
            .order("price")
            .limit(200)
            .execute()
        )
    except Exception as e:
        logger.warning(f"One-way: candidate fetch failed: {e}")
        return

    candidates = cand_resp.data or []
    if not candidates:
        return

    # Group candidates by (origin, destination, direction) and keep the
    # cheapest one in each cell — that's the pertinent deal candidate.
    cells: dict[tuple[str, str, str], dict] = {}
    for c in candidates:
        key = (c.get("origin", ""), c.get("destination", ""), c.get("direction", ""))
        if not all(key):
            continue
        existing = cells.get(key)
        if existing is None or (c.get("price") or 0) < (existing.get("price") or 0):
            cells[key] = c

    dispatched = 0
    for (origin, destination, direction), candidate in cells.items():
        # Pull the 30-day history for this exact (origin, destination, direction).
        try:
            hist_resp = (
                db.table("raw_flights")
                .select("price")
                .eq("origin", origin)
                .eq("destination", destination)
                .eq("direction", direction)
                .eq("trip_type", "one_way")
                .gte("scraped_at", history_cutoff)
                .execute()
            )
        except Exception as e:
            logger.warning(f"One-way history fetch failed for {origin}->{destination}/{direction}: {e}")
            continue

        history = [float(r["price"]) for r in (hist_resp.data or []) if r.get("price")]
        qualification = qualify_oneway(
            price=float(candidate.get("price") or 0),
            recent_prices=history,
        )
        if qualification is None:
            continue

        # Belt-and-braces 40% gate. qualify_oneway uses
        # ONEWAY_DISCOUNT_PCT_FLOOR (currently 60), but anchoring the
        # global product floor here protects users from accidental
        # threshold drift in the qualifier.
        from app.thresholds import GLOBAL_MIN_DISCOUNT_PCT as _MIN
        if qualification.discount_pct < _MIN:
            continue

        # Persist as a qualified_item so the homepage and analytics can see it.
        flight_id = candidate.get("id")
        if not flight_id:
            continue
        score = compute_score(
            discount_pct=qualification.discount_pct,
            destination_code=destination,
            date_flexibility=0,
        )
        # One-way deals never enter the round-trip premium tier (no A/R baseline).
        # We treat ≥60% as "premium-grade" for masking, ≥40% as free.
        tier = "premium" if qualification.discount_pct >= 60 else "free"
        try:
            db.table("qualified_items").upsert(
                {
                    "type": "flight",
                    "item_id": flight_id,
                    "price": qualification.price,
                    "baseline_price": qualification.median,
                    "discount_pct": qualification.discount_pct,
                    "score": score,
                    "tier": tier,
                    "status": "active",
                    "reverified_at": now.isoformat(),
                    "qualification_method": "oneway_discount",
                    "trip_type": "one_way",
                    "direction": direction,
                },
                on_conflict="item_id",
            ).execute()
        except Exception as e:
            logger.warning(f"One-way qualified_item upsert failed: {e}")
            continue

        # Dispatch Telegram alerts to opt-in users tracking this airport.
        # For inbound, the user's home airport is the destination of the
        # candidate (since we flipped origin/destination at scrape time).
        user_airport_for_filter = origin if direction == "outbound" else destination
        for sub in opt_in_subs:
            airports = sub.get("airport_codes") or []
            if user_airport_for_filter not in airports:
                continue
            blocked = set(sub.get("blocked_destinations") or [])
            # Block check uses the actual destination city the user flies to.
            travel_dest = destination if direction == "outbound" else origin
            if travel_dest in blocked:
                continue
            chat_id = sub["telegram_chat_id"]
            sub_user_id = sub.get("user_id")
            # Per-user dedup + click-tracking key.
            from app.notifications.dedup import compute_oneway_alert_key
            alert_key = (
                compute_oneway_alert_key(
                    user_id=sub_user_id,
                    origin=origin,
                    destination=destination,
                    direction=direction,
                    departure_date=candidate.get("departure_date") or "",
                    price=qualification.price,
                )
                if sub_user_id
                else None
            )
            try:
                await send_oneway_deal_alert(
                    chat_id=chat_id,
                    flight={
                        "origin": origin,
                        "destination": destination,
                        "departure_date": candidate.get("departure_date"),
                        "price": qualification.price,
                        "source_url": candidate.get("source_url"),
                        "direction": direction,
                        "airline": candidate.get("airline"),
                    },
                    discount_pct=qualification.discount_pct,
                    baseline_price=qualification.median,
                    user_id=sub_user_id,
                    alert_key=alert_key,
                )
                dispatched += 1
            except Exception as e:
                logger.warning(
                    f"One-way alert send failed user={sub_user_id}: {e}"
                )

        await asyncio.sleep(0)

    logger.info(f"One-way detection complete: {dispatched} alerts dispatched")


async def _detect_and_dispatch_split_ticket_combos() -> None:
    """V5+: scan recent one-way rows for 'combo malin' opportunities.

    For each (origin, destination) tracked in MVP_AIRPORTS × priority destinations,
    pull recent one-way outbounds + inbounds, look up the round-trip baseline,
    and run the matcher. Qualified combos are dispatched as Telegram alerts to
    users who opted in to one_way in flight_trip_types.
    """
    if not db:
        return

    from app.analysis.split_ticket_matcher import find_split_ticket_combos
    from app.notifications.telegram import send_split_ticket_alert

    fresh_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    destinations = get_priority_destinations(max_count=40, db=db)
    combos_dispatched = 0

    # Pre-fetch users who opted in to split-ticket combos.
    # A combo is conceptually an A/R (just sold as 2 separate tickets), so
    # we require:
    #   - 'round_trip' in flight_trip_types (the user wants A/R-style deals)
    #   - include_split_tickets = true (explicit consent for 2-booking format)
    opt_in_subs: list[dict] = []
    try:
        prefs_resp = (
            db.table("user_preferences")
            .select("user_id,telegram_chat_id,airport_codes,flight_trip_types,blocked_destinations,include_split_tickets")
            .eq("telegram_connected", True)
            .execute()
        )
        for pref in (prefs_resp.data or []):
            ftt = pref.get("flight_trip_types") or ["round_trip"]
            if (
                pref.get("include_split_tickets") is True
                and "round_trip" in ftt
                and pref.get("telegram_chat_id")
            ):
                opt_in_subs.append(pref)
    except Exception as e:
        logger.warning(f"Split-ticket: failed to load opt-in users: {e}")
        return

    if not opt_in_subs:
        logger.info("Split-ticket: no users opted in to combo alerts, skipping")
        return

    for origin in settings.MVP_AIRPORTS:
        for dest in destinations:
            if dest == origin:
                continue
            if is_long_haul(dest) and origin != "CDG":
                continue

            # Pull recent one-way rows for both directions in two queries
            try:
                out_resp = (
                    db.table("raw_flights")
                    .select("origin,destination,departure_date,price,airline,source_url,trip_type,direction")
                    .eq("origin", origin)
                    .eq("destination", dest)
                    .eq("trip_type", "one_way")
                    .eq("direction", "outbound")
                    .gte("scraped_at", fresh_cutoff)
                    .order("price")
                    .limit(20)
                    .execute()
                )
                in_resp = (
                    db.table("raw_flights")
                    .select("origin,destination,departure_date,price,airline,source_url,trip_type,direction")
                    .eq("origin", dest)
                    .eq("destination", origin)
                    .eq("trip_type", "one_way")
                    .eq("direction", "inbound")
                    .gte("scraped_at", fresh_cutoff)
                    .order("price")
                    .limit(20)
                    .execute()
                )
            except Exception as e:
                logger.warning(f"Split-ticket: query failed {origin}-{dest}: {e}")
                continue

            outbounds = out_resp.data or []
            inbounds = in_resp.data or []
            if not outbounds or not inbounds:
                continue

            # Round-trip baseline lookup. We use the "all-buckets" legacy key
            # as a coarse reference because the combo matcher doesn't slice
            # by stay duration here — keep it conservative and only qualify
            # combos with a comfortable margin.
            baseline_avg = _lookup_roundtrip_baseline_avg(origin, dest)
            if baseline_avg is None or baseline_avg <= 0:
                continue

            combos = find_split_ticket_combos(
                outbounds=outbounds,
                inbounds=inbounds,
                roundtrip_baseline=baseline_avg,
            )
            if not combos:
                continue
            combo = combos[0]

            # Belt-and-braces 40% gate. The matcher already enforces this via
            # SAVINGS_RATIO_FLOOR=0.40, but anchoring the same threshold here
            # protects against future regressions in the matcher constants.
            from app.thresholds import GLOBAL_MIN_DISCOUNT_PCT
            combo_savings_pct = (
                (combo.roundtrip_baseline - combo.total)
                / combo.roundtrip_baseline
                * 100.0
            ) if combo.roundtrip_baseline > 0 else 0
            if combo_savings_pct < GLOBAL_MIN_DISCOUNT_PCT:
                logger.info(
                    f"Split-ticket combo skipped (savings {combo_savings_pct:.1f}% "
                    f"< {GLOBAL_MIN_DISCOUNT_PCT}%): {origin}-{dest}"
                )
                continue

            from app.notifications.dedup import compute_split_ticket_alert_key

            for sub in opt_in_subs:
                if origin not in (sub.get("airport_codes") or []):
                    continue
                blocked = set(sub.get("blocked_destinations") or [])
                if dest in blocked:
                    continue
                chat_id = sub["telegram_chat_id"]
                sub_user_id = sub.get("user_id")
                alert_key = (
                    compute_split_ticket_alert_key(
                        user_id=sub_user_id,
                        origin=origin,
                        destination=dest,
                        outbound_date=combo.outbound.get("departure_date") or "",
                        inbound_date=combo.inbound.get("departure_date") or "",
                        total_price=combo.total,
                    )
                    if sub_user_id
                    else None
                )
                try:
                    await send_split_ticket_alert(
                        chat_id=chat_id,
                        outbound=combo.outbound,
                        inbound=combo.inbound,
                        roundtrip_baseline=combo.roundtrip_baseline,
                        user_id=sub_user_id,
                        alert_key=alert_key,
                    )
                    combos_dispatched += 1
                except Exception as e:
                    logger.warning(
                        f"Split-ticket alert failed user={sub_user_id}: {e}"
                    )

            await asyncio.sleep(0)

    logger.info(f"Split-ticket detection complete: {combos_dispatched} alerts dispatched")


def _lookup_roundtrip_baseline_avg(origin: str, dest: str) -> float | None:
    """Return the cheapest legacy bucket baseline for a route, or None."""
    if not db:
        return None
    try:
        resp = (
            db.table("price_baselines")
            .select("avg_price,sample_count")
            .like("route_key", f"{origin}-{dest}-bucket_%")
            .eq("type", "flight")
            .order("avg_price")
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return None
        avg = rows[0].get("avg_price")
        return float(avg) if avg else None
    except Exception as e:
        logger.warning(f"Baseline lookup failed {origin}-{dest}: {e}")
        return None


async def job_travelpayouts_enrichment():
    """Build per-bucket baselines for all MVP routes via Travelpayouts."""
    logger.info("Starting Travelpayouts bucket baseline enrichment")
    if not db or not settings.TRAVELPAYOUTS_TOKEN:
        return

    destinations = get_priority_destinations(max_count=40, db=db)
    total_published = 0

    for origin in settings.MVP_AIRPORTS:
        for dest in destinations:
            if dest == origin:
                continue
            # Long-haul routes only from CDG — the only French hub with direct transatlantic service
            if is_long_haul(dest) and origin != "CDG":
                continue

            try:
                api_entries = get_prices_for_dates(origin, dest)
            except Exception as e:
                logger.warning(f"Travelpayouts enrichment failed for {origin}->{dest}: {e}")
                continue

            observations = []
            for entry in api_entries:
                normalized = _normalize_priced_entry(entry)
                if normalized:
                    observations.append(normalized)

            if not observations:
                continue

            baselines = compute_baselines_by_bucket(f"{origin}-{dest}", observations)
            for baseline in baselines:
                try:
                    db.table("price_baselines").upsert(baseline, on_conflict="route_key").execute()
                    total_published += 1
                except Exception as e:
                    logger.warning(f"Failed to upsert baseline {baseline['route_key']}: {e}")

            # Also create destination-wide baselines for fallback (new routes like BVA→BCN)
            dest_baselines = compute_baselines_by_bucket(f"*-{dest}", observations)
            for baseline in dest_baselines:
                try:
                    db.table("price_baselines").upsert(baseline, on_conflict="route_key").execute()
                    total_published += 1
                except Exception as e:
                    logger.warning(f"Failed to upsert destination baseline {baseline['route_key']}: {e}")

            # Yield the event loop after each route to keep HTTP requests responsive.
            await asyncio.sleep(0)

    logger.info(f"Travelpayouts enrichment: {total_published} bucket baselines upserted")


async def job_update_destinations():
    """Weekly job: update priority_destinations table from Travelpayouts + seasonal scoring.

    Runs every Monday at 3am. Non-blocking — if it fails, existing DB rows remain
    and scraping jobs continue using the last good snapshot.
    """
    logger.info("Starting weekly destination update")
    if not db:
        logger.warning("No DB connection — skipping destination update")
        return
    try:
        count = update_priority_destinations_in_db(db, max_count=40)
        logger.info(f"Destination update complete: {count} destinations upserted")
    except Exception as e:
        logger.error(f"Destination update failed: {e}")


async def job_sync_stripe_subscriptions():
    """Sync premium_expires_at from Stripe for all users with a stripe_subscription_id.

    Runs daily at 6am. Queries Stripe for each active subscription and writes the
    current_period_end as premium_expires_at. If the subscription is cancelled or
    past_due, sets premium_expires_at to now() so _get_user_tier returns 'free'
    immediately on the next check.
    """
    if not db:
        logger.warning("No DB connection — skipping Stripe sync")
        return

    import stripe as stripe_lib
    from app.config import settings as _settings

    if not _settings.STRIPE_SECRET_KEY:
        logger.warning("STRIPE_SECRET_KEY not set — skipping Stripe sync")
        return

    stripe_lib.api_key = _settings.STRIPE_SECRET_KEY

    # Fetch all users that have a subscription_id
    try:
        rows = (
            db.table("user_preferences")
            .select("user_id,stripe_subscription_id,stripe_customer_id")
            .not_.is_("stripe_subscription_id", "null")
            .execute()
        )
        prefs = rows.data or []
    except Exception as e:
        logger.error(f"Stripe sync: failed to fetch prefs: {e}")
        return

    updated = expired = errors = 0
    now = datetime.now(timezone.utc)

    for pref in prefs:
        sub_id = pref.get("stripe_subscription_id")
        user_id = pref.get("user_id")
        if not sub_id or not user_id:
            continue
        try:
            sub = stripe_lib.Subscription.retrieve(sub_id)
            status = sub.get("status", "")
            period_end = sub.get("current_period_end")  # Unix timestamp

            if status in ("active", "trialing") and period_end:
                expires_at = datetime.fromtimestamp(period_end, tz=timezone.utc)
                db.table("user_preferences").update({
                    "premium_expires_at": expires_at.isoformat(),
                }).eq("user_id", user_id).execute()
                updated += 1
            else:
                # Cancelled, past_due, unpaid → expire immediately
                db.table("user_preferences").update({
                    "premium_expires_at": now.isoformat(),
                }).eq("user_id", user_id).execute()
                expired += 1
                logger.info(f"Stripe sync: subscription {sub_id} status={status} → premium expired for {user_id}")

        except Exception as e:
            logger.warning(f"Stripe sync: error for sub {sub_id}: {e}")
            errors += 1

    logger.info(f"Stripe sync complete: {updated} renewed, {expired} expired, {errors} errors")


async def job_check_scraper_health():
    """Daily scraper API health check.

    Probes Transavia and Vueling endpoints. If an API is dead, searches for
    a new endpoint. If found, patches the scraper file and re-enables it.
    If not found, keeps it disabled. If a previously dead API comes back,
    re-enables it automatically.
    """
    logger.info("Starting scraper health check")
    try:
        await run_scraper_health_check()
    except Exception as e:
        logger.error(f"Scraper health check failed: {e}")


# ─── V8.3 — scraper watchdog ────────────────────────────────────────────
# Anti-spam state: last admin-alert timestamp per scraper source. We keep
# this in-process — the watchdog runs from a single APScheduler so we
# don't need cross-process coordination.
_watchdog_last_alert: dict[str, datetime] = {}
_WATCHDOG_COOLDOWN_HOURS = 6


async def job_scraper_watchdog():
    """V8.3: ping the admin Telegram chat when a scraper logs runs but
    persists zero rows for 24h — a clear sign that the scraper is broken
    silently. Cooldown of 6h per source so we don't flood the admin
    channel during a long outage.
    """
    if not db:
        return
    if not settings.TELEGRAM_ADMIN_CHAT_ID:
        # No admin chat configured — nothing to do.
        return

    from app.notifications.telegram import send_admin_alert

    since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    # Per-source check: rows in DB vs runs logged.
    sources = {
        "ryanair_direct": "tier1",
        "vueling_direct": "tier1",
        "travelpayouts": "flights",
    }
    issues: list[str] = []
    for source, log_actor in sources.items():
        try:
            rows = (
                db.table("raw_flights")
                .select("id", count="exact", head=True)
                .eq("source", source)
                .gte("scraped_at", since_24h)
                .execute()
                .count
                or 0
            )
            runs = (
                db.table("scrape_logs")
                .select("id", count="exact", head=True)
                .eq("actor_id", log_actor)
                .gte("started_at", since_24h)
                .execute()
                .count
                or 0
            )
        except Exception as e:
            logger.warning(f"watchdog: query failed for {source}: {e}")
            continue

        # Flag the scraper if it ran more than twice in the last 24h but
        # hasn't landed a single row. Travelpayouts only runs ~12x/day,
        # the LCC scrapers run ~72x/day — pick a low common bar.
        if rows == 0 and runs >= 3:
            issues.append(f"{source}: {runs} runs / 0 rows (24h)")

    # One-way: separate trip_type filter
    try:
        ow_rows = (
            db.table("raw_flights")
            .select("id", count="exact", head=True)
            .eq("trip_type", "one_way")
            .gte("scraped_at", since_24h)
            .execute()
            .count
            or 0
        )
        ow_runs = (
            db.table("scrape_logs")
            .select("id", count="exact", head=True)
            .eq("actor_id", "flights_oneway")
            .gte("started_at", since_24h)
            .execute()
            .count
            or 0
        )
        if ow_rows == 0 and ow_runs >= 3:
            issues.append(f"one_way: {ow_runs} runs / 0 rows (24h)")
    except Exception as e:
        logger.warning(f"watchdog: oneway query failed: {e}")

    if not issues:
        return

    # Cooldown check per-source so we don't spam admin during a long outage.
    now = datetime.now(timezone.utc)
    fresh: list[str] = []
    for issue in issues:
        source = issue.split(":", 1)[0]
        last = _watchdog_last_alert.get(source)
        if last and (now - last) < timedelta(hours=_WATCHDOG_COOLDOWN_HOURS):
            continue
        _watchdog_last_alert[source] = now
        fresh.append(issue)

    if not fresh:
        return

    msg = (
        "Scraper watchdog detected silent failures:\n\n"
        + "\n".join(f"• {x}" for x in fresh)
        + "\n\nCheck /api/admin/scrapers/health for details."
    )
    try:
        await send_admin_alert(msg)
        logger.warning(f"watchdog admin alert sent: {len(fresh)} issue(s)")
    except Exception as e:
        logger.error(f"watchdog: admin alert send failed: {e}")


async def job_reverify_active_deals():
    """Re-verify all active qualified_items whose reverified_at is older than 2h.

    Deals that no longer exist at their original price are expired immediately,
    keeping the homepage free of stale offers. Deals that still hold get their
    reverified_at timestamp refreshed so they stay visible.
    """
    if not db:
        return

    stale_threshold = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    resp = (
        db.table("qualified_items")
        .select("id, item_id, price")
        .eq("status", "active")
        .lt("reverified_at", stale_threshold)
        .limit(50)
        .execute()
    )
    items = resp.data or []
    if not items:
        return

    logger.info(f"Re-verifying {len(items)} stale qualified_items")

    item_ids = [qi["item_id"] for qi in items]
    flights_resp = (
        db.table("raw_flights")
        .select("id, origin, destination, price, departure_date, return_date, source")
        .in_("id", item_ids)
        .execute()
    )
    flights_by_id = {f["id"]: f for f in (flights_resp.data or [])}

    now_utc = datetime.now(timezone.utc).isoformat()
    expired = 0
    refreshed = 0

    for qi in items:
        flight = flights_by_id.get(qi["item_id"])
        if not flight:
            db.table("qualified_items").update({"status": "expired"}).eq("id", qi["id"]).execute()
            expired += 1
            continue

        flight["price"] = qi["price"]
        try:
            still_valid = await reverify_flight_price(flight)
        except Exception as e:
            logger.warning(f"Reverify error for qi {qi['id']}: {e}")
            continue

        if still_valid:
            db.table("qualified_items").update({"reverified_at": now_utc}).eq("id", qi["id"]).execute()
            refreshed += 1
        else:
            db.table("qualified_items").update({"status": "expired"}).eq("id", qi["id"]).execute()
            expired += 1

    logger.info(f"Reverify pass: {refreshed} refreshed, {expired} expired")
    logger.info("Scraper health check complete")
