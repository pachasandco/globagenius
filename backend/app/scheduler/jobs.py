import logging
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.db import db
from app.scraper.flights import scrape_all_flights
from app.scraper.accommodations import scrape_accommodations_for_destinations
from app.analysis.baselines import compute_baseline
from app.analysis.anomaly_detector import detect_anomaly
from app.analysis.scorer import compute_score
from app.composer.package_builder import build_packages
from app.notifications.telegram import (
    send_deal_alert,
    send_digest,
    send_admin_report,
    send_admin_alert,
)

logger = logging.getLogger(__name__)


def get_scheduler_jobs() -> list[dict]:
    return [
        # ── VOLS : 3 scrapes/jour aux creneaux strategiques ──
        # Mardi-mercredi 2h : promos compagnies publiees lundi soir
        # Tous les jours 4h : error fares (minuit-6h = window d'erreurs de pricing)
        # Tous les jours 14h : rattraper les promos du matin
        {
            "id": "scrape_flights_early",
            "func": job_scrape_flights,
            "trigger": "cron",
            "hour": 4,
        },
        {
            "id": "scrape_flights_afternoon",
            "func": job_scrape_flights,
            "trigger": "cron",
            "hour": 14,
        },
        {
            "id": "scrape_flights_tuesday",
            "func": job_scrape_flights,
            "trigger": "cron",
            "day_of_week": "tue",
            "hour": 2,
        },
        # ── HOTELS : 2 scrapes/jour ──
        # Lundi 3h : meilleurs prix en debut de semaine
        # Jeudi 3h : capturer les baisses avant le weekend
        {
            "id": "scrape_accommodations_monday",
            "func": job_scrape_accommodations,
            "trigger": "cron",
            "day_of_week": "mon",
            "hour": 3,
        },
        {
            "id": "scrape_accommodations_thursday",
            "func": job_scrape_accommodations,
            "trigger": "cron",
            "day_of_week": "thu",
            "hour": 3,
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

    flights, errors, baselines = scrape_all_flights()

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
    for flight in flights:
        try:
            db.table("raw_flights").upsert(flight, on_conflict="hash").execute()
            inserted += 1
        except Exception as e:
            logger.warning(f"Failed to insert flight: {e}")
            errors += 1

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

    for flight in flights:
        # Calculate days ahead for this flight to pick the right baseline window
        try:
            dep = datetime.strptime(flight["departure_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days_ahead = (dep - datetime.now(timezone.utc)).days
        except (ValueError, TypeError):
            days_ahead = 30

        from app.scraper.flights import _window_label
        window = _window_label(max(days_ahead, 15))
        route_key = f"{flight['origin']}-{flight['destination']}-{window}"

        # Try window-specific baseline first, then generic
        baseline_resp = db.table("price_baselines").select("*").eq("route_key", route_key).eq("type", "flight").execute()
        if not baseline_resp.data:
            # Fallback: try without window
            generic_key = f"{flight['origin']}-{flight['destination']}"
            baseline_resp = db.table("price_baselines").select("*").eq("route_key", generic_key).eq("type", "flight").execute()
        if not baseline_resp.data:
            continue

        baseline = baseline_resp.data[0]
        anomaly = detect_anomaly(price=flight["price"], baseline=baseline)

        if anomaly:
            score = compute_score(
                discount_pct=anomaly.discount_pct,
                destination_code=flight["destination"],
                date_flexibility=0,
                accommodation_rating=None,
            )

            db.table("qualified_items").insert({
                "type": "flight",
                "item_id": flight.get("id", ""),
                "price": anomaly.price,
                "baseline_price": anomaly.baseline_price,
                "discount_pct": anomaly.discount_pct,
                "score": score,
                "status": "active",
            }).execute()

            await _compose_packages_for_flight(flight, baseline)


async def _compose_packages_for_flight(flight: dict, flight_baseline: dict):
    if not db:
        return

    from app.config import IATA_TO_CITY
    city = IATA_TO_CITY.get(flight["destination"])
    if not city:
        return

    acc_resp = (
        db.table("raw_accommodations")
        .select("*")
        .eq("city", city)
        .eq("check_in", flight["departure_date"])
        .eq("check_out", flight["return_date"])
        .gte("rating", 4.0)
        .gte("expires_at", datetime.now(timezone.utc).isoformat())
        .execute()
    )

    if not acc_resp.data:
        return

    acc_baselines = {}
    for acc in acc_resp.data:
        bl_key = f"{acc['city'].lower()}-{acc['source']}"
        if bl_key not in acc_baselines:
            bl_resp = db.table("price_baselines").select("*").eq("route_key", bl_key).eq("type", "accommodation").execute()
            if bl_resp.data:
                acc_baselines[bl_key] = bl_resp.data[0]

    packages = build_packages(
        flight=flight,
        accommodations=acc_resp.data,
        flight_baseline=flight_baseline,
        accommodation_baselines=acc_baselines,
    )

    for pkg in packages:
        acc_for_pkg = next((a for a in acc_resp.data if a["id"] == pkg["accommodation_id"]), None)

        # Step 1: AI curation — validate the deal before publishing
        try:
            from app.agents.curator import curate_deal
            curation = curate_deal(pkg, flight_data=flight, accommodation_data=acc_for_pkg)
            if curation and not curation.get("valid", True):
                logger.info(f"Deal rejected by curator: {pkg['origin']}→{pkg['destination']} — {curation.get('reason')}")
                continue  # Skip this deal
            if curation:
                pkg["ai_curated"] = True
                pkg["ai_is_error_fare"] = curation.get("is_error_fare", False)
                pkg["ai_urgency"] = curation.get("urgency", "medium")
        except Exception as e:
            logger.warning(f"AI curation failed, approving by default: {e}")

        # Step 2: AI enrichment — generate description
        try:
            from app.agents.enricher import enrich_package
            enrichment = enrich_package(pkg, flight=flight, accommodation=acc_for_pkg)
            if enrichment:
                pkg.update(enrichment)
        except Exception as e:
            logger.warning(f"AI enrichment failed, saving without: {e}")

        db.table("packages").insert(pkg).execute()

        if pkg["score"] >= settings.MIN_SCORE_ALERT:
            subscribers = (
                db.table("telegram_subscribers")
                .select("chat_id")
                .eq("airport_code", pkg["origin"])
                .lte("min_score", pkg["score"])
                .execute()
            )
            flight_data = db.table("raw_flights").select("source_url,airline").eq("id", pkg["flight_id"]).execute()
            acc_data = db.table("raw_accommodations").select("name,rating,source_url").eq("id", pkg["accommodation_id"]).execute()

            if flight_data.data and acc_data.data and subscribers.data:
                for sub in subscribers.data:
                    await send_deal_alert(sub["chat_id"], pkg, flight_data.data[0], acc_data.data[0])


async def job_scrape_accommodations():
    logger.info("Starting accommodation scraping job")
    if not db:
        return

    flights_resp = (
        db.table("raw_flights")
        .select("destination")
        .gte("expires_at", datetime.now(timezone.utc).isoformat())
        .execute()
    )
    destinations = {f["destination"] for f in (flights_resp.data or [])}

    if not destinations:
        logger.info("No active flight destinations, skipping accommodation scrape")
        return

    started_at = datetime.now(timezone.utc)
    accommodations, errors = scrape_accommodations_for_destinations(destinations)

    inserted = 0
    for acc in accommodations:
        try:
            db.table("raw_accommodations").upsert(acc, on_conflict="hash").execute()
            inserted += 1
        except Exception as e:
            logger.warning(f"Failed to insert accommodation: {e}")
            errors += 1

    completed_at = datetime.now(timezone.utc)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    status = "success" if errors == 0 else ("partial" if inserted > 0 else "failed")
    db.table("scrape_logs").insert({
        "actor_id": "accommodations",
        "source": "booking",
        "type": "accommodations",
        "items_count": inserted,
        "errors_count": errors,
        "duration_ms": duration_ms,
        "status": status,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
    }).execute()

    logger.info(f"Accommodation scraping complete: {inserted} inserted, {errors} errors")


async def job_recalculate_baselines():
    logger.info("Starting baseline recalculation")
    if not db:
        return

    now = datetime.now(timezone.utc)
    thirty_days_ago = (now - timedelta(days=30)).isoformat()

    flights_resp = (
        db.table("raw_flights")
        .select("origin, destination, price, scraped_at")
        .gte("scraped_at", thirty_days_ago)
        .execute()
    )

    routes: dict[str, list] = {}
    for f in (flights_resp.data or []):
        key = f"{f['origin']}-{f['destination']}"
        routes.setdefault(key, []).append({"price": f["price"], "scraped_at": f["scraped_at"]})

    for route_key, observations in routes.items():
        baseline = compute_baseline(route_key, "flight", observations)
        if baseline:
            db.table("price_baselines").upsert(baseline, on_conflict="route_key").execute()

    acc_resp = (
        db.table("raw_accommodations")
        .select("city, source, total_price, scraped_at")
        .gte("scraped_at", thirty_days_ago)
        .execute()
    )

    acc_routes: dict[str, list] = {}
    for a in (acc_resp.data or []):
        key = f"{a['city'].lower()}-{a['source']}"
        acc_routes.setdefault(key, []).append({"price": a["total_price"], "scraped_at": a["scraped_at"]})

    for route_key, observations in acc_routes.items():
        baseline = compute_baseline(route_key, "accommodation", observations)
        if baseline:
            db.table("price_baselines").upsert(baseline, on_conflict="route_key").execute()

    logger.info(f"Baselines recalculated: {len(routes)} flight routes, {len(acc_routes)} accommodation routes")


async def job_expire_stale_data():
    if not db:
        return
    now = datetime.now(timezone.utc).isoformat()

    db.table("packages").update({"status": "expired"}).eq("status", "active").lt("expires_at", now).execute()
    db.table("qualified_items").update({"status": "expired"}).eq("status", "active").execute()

    logger.info("Expired stale packages and qualified items")


async def job_daily_digest():
    if not db:
        return

    packages_resp = (
        db.table("packages")
        .select("*")
        .eq("status", "active")
        .gte("score", settings.MIN_SCORE_DIGEST)
        .order("score", desc=True)
        .limit(5)
        .execute()
    )

    if not packages_resp.data:
        return

    subscribers = db.table("telegram_subscribers").select("chat_id").execute()
    for sub in (subscribers.data or []):
        await send_digest(sub["chat_id"], packages_resp.data)


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
