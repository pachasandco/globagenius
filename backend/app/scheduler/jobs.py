import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from app.config import settings, IATA_TO_CITY
from app.db import db
from app.scraper.travelpayouts_flights import scrape_all_flights
from app.scraper.tier1_scraper import scrape_all_tier1
from app.analysis.baselines import compute_baseline, compute_baselines_by_bucket, MIN_SAMPLE_COUNT
from app.scraper.travelpayouts import get_prices_for_dates
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
        if not anomaly:
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
        }
        if competitor_prices is not None:
            qualified_item_row["competitor_prices"] = competitor_prices

        db.table("qualified_items").insert(qualified_item_row).execute()

        # Defer flight alert dispatch: accumulate and send as grouped alerts
        # (by origin+destination) after the analysis pass completes. This lets
        # us batch multiple offers per destination into a single Telegram msg
        # and apply deal-level dedup via the sent_alerts table.
        if score >= settings.MIN_SCORE_ALERT:
            # Stash score back on the flight dict so the grouped dispatcher
            # can surface it in offers without re-computing.
            flight["score"] = score
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
            .select("user_id,telegram_chat_id,telegram_connected,airport_codes,alerts_paused_until,deal_tier")
            .eq("telegram_connected", True)
            .execute()
        )
        all_prefs = prefs_resp.data or []
    except Exception as e:
        err_msg = str(e)
        if "alerts_paused_until" in err_msg or "deal_tier" in err_msg:
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
    for pref in all_prefs:
        if isinstance(pref, dict) and pref.get("user_id"):
            uid = pref["user_id"]
            if pref.get("alerts_paused_until"):
                paused_until_by_user[uid] = pref["alerts_paused_until"]
            deal_tier_by_user[uid] = pref.get("deal_tier") or "regular"

    # Track teasers already sent this run — at most once per user per run
    teaser_sent_quota: set[str] = set()
    teaser_sent_premium: set[str] = set()
    # Track best price already dispatched per (user_id, destination, dep_date, ret_date)
    # this run. When a user tracks multiple origins (CDG + ORY + BVA) and the same
    # itinerary appears from several airports, only send the cheapest one.
    # Key: (user_id, dest, dep_date, ret_date) → best price sent
    dispatched_this_run: dict[tuple, float] = {}

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

            # Free tier weekly quota
            FREE_TIER_WEEKLY_LIMIT = 3
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
                # Free:    40–50% → full info (max 3/week), >50% → masked teaser
                # Premium: ≥40%  → full info, no limit
                FREE_TIER_FULL_MAX = 50   # above this → masked for free users
                GLOBAL_MIN_DISCOUNT = 40  # below this → no alert for anyone

                candidates: list[tuple[str | None, dict, object, str]] = []
                for flight, anomaly, tier in flight_tuples:
                    if matching_wl is not None:
                        max_price = matching_wl.get("max_price")
                        if max_price is not None and flight.get("price", 9999) > max_price:
                            continue
                    else:
                        if anomaly.discount_pct < GLOBAL_MIN_DISCOUNT:
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

                # Free tier: deals >50% → masked teaser (once per run)
                if sub_tier == "free" and not tier_error and chat_id is not None and user_id not in teaser_sent_premium:
                    masked = [
                        (f, a) for f, a, _ in flight_tuples
                        if a.discount_pct > FREE_TIER_FULL_MAX
                    ]
                    if masked:
                        teaser_sent_premium.add(user_id)
                        best_f, best_a = max(masked, key=lambda x: x[1].discount_pct)
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
                        except Exception:
                            pass

                # Free tier: weekly quota gate (max 3 full alerts/week)
                if sub_tier == "free" and matching_wl is None and weekly_sent_count >= FREE_TIER_WEEKLY_LIMIT:
                    if not tier_error and chat_id is not None and user_id not in teaser_sent_quota:
                        teaser_sent_quota.add(user_id)
                        try:
                            from app.notifications.telegram import _get_bot
                            bot = _get_bot()
                            if bot:
                                await bot.send_message(
                                    chat_id=chat_id,
                                    text=(
                                        f"🔒 Limite hebdomadaire atteinte\n\n"
                                        f"Tu as reçu {FREE_TIER_WEEKLY_LIMIT} alertes cette semaine "
                                        f"(limite du compte gratuit).\n\n"
                                        f"💎 Passe en premium pour recevoir toutes les alertes "
                                        f"en temps réel, sans limite.\n"
                                        f"👉 {settings.FRONTEND_URL}/premium"
                                    ),
                                )
                        except Exception:
                            pass
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

                # Within a single run, if we already dispatched this destination
                # at the same or cheaper price (from another origin), skip.
                best_offer_price = min((o["price"] for o in offers), default=0)
                run_key = (user_id or "", grp_dest)
                prev_best = dispatched_this_run.get(run_key)
                if prev_best is not None and best_offer_price >= prev_best:
                    continue

                origin_city = IATA_TO_CITY.get(grp_origin, grp_origin)
                dest_city = IATA_TO_CITY.get(grp_dest, grp_dest)
                try:
                    success = await send_grouped_flight_alerts(
                        chat_id=chat_id,
                        origin_city=origin_city,
                        dest_city=dest_city,
                        destination_iata=grp_dest,
                        offers=offers,
                        tier=sub_tier,
                        user_id=user_id,
                        alert_key=keys_to_store[0] if keys_to_store else None,
                        origin_iata=grp_origin,
                    )
                    if success:
                        logger.info(f"✅ Sent {len(offers)} flight alerts to {origin_city}→{dest_city} for user {user_id}")
                        dispatched_this_run[(user_id or "", grp_dest)] = best_offer_price
                        if sub_tier == "free":
                            weekly_sent_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send grouped flight alert: {e}")
                    success = False

                if success and user_id and keys_to_store:
                    rows = [{
                        "user_id": user_id,
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
        except Exception as e:
            logger.warning(f"Grouped dispatch error for subscriber: {e}")

        await asyncio.sleep(0)


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
