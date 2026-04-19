import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from app.config import settings, IATA_TO_CITY
from app.db import db
from app.scraper.travelpayouts_flights import scrape_all_flights
from app.analysis.baselines import compute_baseline, compute_baselines_by_bucket, MIN_SAMPLE_COUNT
from app.scraper.travelpayouts import get_prices_for_dates
from app.scraper.travelpayouts_flights import _normalize_priced_entry
from app.analysis.route_selector import get_priority_destinations, is_long_haul
from app.analysis.anomaly_detector import detect_anomaly
from app.analysis.scorer import compute_score
from app.analysis.buckets import bucket_for_duration, stops_allowed
from app.scraper.reverify import reverify_flight_price
from app.notifications.aviasales import build_aviasales_url
from app.notifications.dedup import compute_alert_key
from app.notifications.telegram import (
    send_deal_alert,
    send_flight_deal_alert,
    send_grouped_flight_alerts,
    send_digest,
    send_admin_report,
    send_admin_alert,
)
from app.api.routes import _get_user_tier

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

        # Lookup baseline for this (route, bucket)
        route_key = f"{flight['origin']}-{flight['destination']}-bucket_{bucket}"
        baseline_resp = (
            db.table("price_baselines")
            .select("*")
            .eq("route_key", route_key)
            .eq("type", "flight")
            .execute()
        )
        if not baseline_resp.data:
            counters["rejected_no_baseline"] += 1
            continue

        baseline = baseline_resp.data[0]
        if (baseline.get("sample_count") or 0) < MIN_SAMPLE_COUNT:
            counters["rejected_low_sample"] += 1
            continue

        # Anomaly detection (existing helper)
        anomaly = detect_anomaly(price=flight["price"], baseline=baseline)
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

        # Tier classification
        tier = "premium" if anomaly.discount_pct >= 30 else "free"

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

        db.table("qualified_items").insert({
            "type": "flight",
            "item_id": flight_id,
            "price": anomaly.price,
            "baseline_price": anomaly.baseline_price,
            "discount_pct": anomaly.discount_pct,
            "score": score,
            "tier": tier,
            "status": "active",
        }).execute()

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

    try:
        subs_resp = (
            db.table("telegram_subscribers")
            .select("chat_id,user_id,airport_code")
            .in_("airport_code", origins)
            .execute()
        )
        subs = subs_resp.data or []
    except Exception as e:
        logger.warning(f"Failed to fetch subscribers for grouped dispatch: {e}")
        return

    if not isinstance(subs, list):
        return

    # Bulk-fetch user preferences (min_discount) once for all subscribers.
    prefs_by_user: dict[str, int] = {}
    user_ids = [s["user_id"] for s in subs if isinstance(s, dict) and s.get("user_id")]
    if user_ids:
        try:
            prefs_resp = (
                db.table("user_preferences")
                .select("user_id,min_discount")
                .in_("user_id", user_ids)
                .execute()
            )
            for p in (prefs_resp.data or []):
                if isinstance(p, dict) and p.get("user_id"):
                    prefs_by_user[p["user_id"]] = p.get("min_discount", 20)
        except Exception as e:
            logger.warning(f"Failed to fetch user preferences: {e}")

    for sub in subs:
        if not isinstance(sub, dict):
            continue
        try:
            user_id = sub.get("user_id")
            user_min = prefs_by_user.get(user_id, 20) if user_id else 20
            # Phase D4: resolve subscriber tier once. Free-tier users must not
            # receive any offer >= 30% discount, regardless of their
            # min_discount preference.
            try:
                sub_tier = _get_user_tier(user_id) if user_id else "free"
            except Exception as e:
                logger.warning(f"Failed to resolve tier for {user_id}: {e}")
                sub_tier = "free"
            sub_origin = sub.get("airport_code")
            chat_id = sub.get("chat_id")
            if not sub_origin or chat_id is None:
                continue

            for (grp_origin, grp_dest), flight_tuples in groups.items():
                if grp_origin != sub_origin:
                    continue

                # Build candidate list after min_discount + tier filter
                candidates: list[tuple[str | None, dict, object, str]] = []
                for flight, anomaly, tier in flight_tuples:
                    if anomaly.discount_pct < user_min:
                        continue
                    # Phase D4: strict tier gate — free users never see >=30%.
                    if sub_tier == "free" and anomaly.discount_pct >= 30:
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

                already_keys: set[str] = set()
                if user_id:
                    keys_to_check = [k for (k, _, _, _) in candidates if k]
                    if keys_to_check:
                        try:
                            sent_resp = (
                                db.table("sent_alerts")
                                .select("alert_key")
                                .eq("user_id", user_id)
                                .in_("alert_key", keys_to_check)
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
                    offers.append({
                        "departure_date": flight["departure_date"],
                        "return_date": flight["return_date"],
                        "price": flight["price"],
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
                    })
                    if key:
                        keys_to_store.append(key)
                    if tier == "premium":
                        group_tier = "premium"

                if not offers:
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
                        tier=group_tier,
                    )
                    if success:
                        logger.info(f"✅ Sent {len(offers)} flight alerts to {origin_city}→{dest_city} for user {user_id}")
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
            .select("origin, destination, price, scraped_at, trip_duration_days, stops, duration_minutes")
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


async def job_travelpayouts_enrichment():
    """Build per-bucket baselines for all MVP routes via Travelpayouts."""
    logger.info("Starting Travelpayouts bucket baseline enrichment")
    if not db or not settings.TRAVELPAYOUTS_TOKEN:
        return

    destinations = get_priority_destinations(max_count=25)
    total_published = 0

    for origin in settings.MVP_AIRPORTS:
        for dest in destinations:
            if dest == origin:
                continue
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
            # Yield the event loop after each route to keep HTTP requests responsive.
            await asyncio.sleep(0)

    logger.info(f"Travelpayouts enrichment: {total_published} bucket baselines upserted")
