import logging
from datetime import datetime, timedelta, timezone
from app.config import settings, IATA_TO_CITY
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
        # ── VOLS : toutes les 4h (6x/jour) — optimise pour couts ──
        *[{
            "id": f"scrape_flights_{h:02d}",
            "func": job_scrape_flights,
            "trigger": "cron",
            "hour": h,
        } for h in [2, 6, 10, 14, 18, 22]],
        # ── HOTELS : 1x/jour a 3h ──
        {
            "id": "scrape_accommodations_03",
            "func": job_scrape_accommodations,
            "trigger": "cron",
            "hour": 3,
        },
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

    # Only scrape hotels for destinations where flights have 30%+ discount
    # This saves API costs and targets the right destinations
    qualified_flights = (
        db.table("qualified_items")
        .select("item_id, discount_pct")
        .eq("type", "flight")
        .eq("status", "active")
        .gte("discount_pct", 30)
        .execute()
    )

    if not qualified_flights.data:
        # Fallback: check raw flights vs baselines for 30%+ discounts
        flights_resp = (
            db.table("raw_flights")
            .select("id, origin, destination, departure_date, return_date, price")
            .gte("expires_at", datetime.now(timezone.utc).isoformat())
            .execute()
        )

        if not flights_resp.data:
            logger.info("No active flights, skipping accommodation scrape")
            return

        # Find flights with 30%+ discount vs baseline
        route_dates = set()
        from app.scraper.flights import _window_label
        for f in flights_resp.data:
            try:
                dep = datetime.strptime(f["departure_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days_ahead = max((dep - datetime.now(timezone.utc)).days, 15)
            except (ValueError, TypeError):
                days_ahead = 30

            window = _window_label(days_ahead)
            route_key = f"{f['origin']}-{f['destination']}-{window}"

            bl = db.table("price_baselines").select("avg_price").eq("route_key", route_key).execute()
            if not bl.data:
                continue

            avg = bl.data[0]["avg_price"]
            if avg > 0:
                discount = (avg - f["price"]) / avg * 100
                if discount >= 30:
                    route_dates.add((f["destination"], f["departure_date"], f["return_date"]))
                    logger.info(f"  Flight deal: {f['origin']}→{f['destination']} {f['price']}€ vs {avg}€ (-{discount:.0f}%)")
    else:
        # Get flight details for qualified items
        route_dates = set()
        for qi in qualified_flights.data:
            flight = db.table("raw_flights").select("destination, departure_date, return_date").eq("id", qi["item_id"]).execute()
            if flight.data:
                f = flight.data[0]
                route_dates.add((f["destination"], f["departure_date"], f["return_date"]))

    if not route_dates:
        logger.info("No flights with 30%+ discount, skipping hotel scrape")
        return

    destinations = {rd[0] for rd in route_dates}
    logger.info(f"Scraping hotels for {len(destinations)} destinations with 30%+ flight discounts ({len(route_dates)} date combos)")

    started_at = datetime.now(timezone.utc)

    # Scrape accommodations for exact flight dates (not generic sample dates)
    from app.scraper.accommodations import scrape_accommodations_for_city
    all_accommodations = []
    errors = 0
    for dest_code, dep_date, ret_date in route_dates:
        city = IATA_TO_CITY.get(dest_code)
        if not city:
            continue
        try:
            items = await scrape_accommodations_for_city(city, dep_date, ret_date)
            all_accommodations.extend(items)
            if items:
                logger.info(f"  {city} {dep_date}→{ret_date}: {len(items)} hotels")
        except Exception as e:
            errors += 1
            logger.warning(f"Failed to scrape hotels in {city}: {e}")
    accommodations = all_accommodations

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
    # Expire qualified items older than 24h (they don't have expires_at)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    db.table("qualified_items").update({"status": "expired"}).eq("status", "active").lt("created_at", yesterday).execute()

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


async def job_travelpayouts_enrichment():
    """Enrich baselines with Travelpayouts data + check special offers."""
    logger.info("Starting Travelpayouts enrichment")
    if not db or not settings.TRAVELPAYOUTS_TOKEN:
        return

    from app.scraper.travelpayouts import build_baseline_from_travelpayouts, get_special_offers, get_cheap_destinations
    from app.scraper.flights import _window_label

    # 1. Enrich baselines for all MVP airports
    enriched = 0
    for airport in settings.MVP_AIRPORTS:
        # Discover cheap destinations
        try:
            cheap = get_cheap_destinations(airport, limit=15)
            for dest in cheap:
                dest_code = dest.get("destination", "")
                if not dest_code:
                    continue

                baseline_data = build_baseline_from_travelpayouts(airport, dest_code)
                if baseline_data:
                    route_key = f"{airport}-{dest_code}-tp"
                    db.table("price_baselines").upsert({
                        "route_key": route_key,
                        "type": "flight",
                        "avg_price": baseline_data["avg_price"],
                        "std_dev": max(baseline_data["std_dev"], 1.0),
                        "sample_count": baseline_data["sample_count"],
                        "calculated_at": datetime.now(timezone.utc).isoformat(),
                    }, on_conflict="route_key").execute()
                    enriched += 1
        except Exception as e:
            logger.warning(f"Travelpayouts enrichment failed for {airport}: {e}")

    logger.info(f"Travelpayouts: enriched {enriched} baselines")

    # 2. Check special offers (fare mistakes)
    try:
        offers = get_special_offers()
        if offers:
            logger.info(f"Travelpayouts: {len(offers)} special offers detected")
            for offer in offers[:10]:
                logger.info(f"  Special: {offer.get('origin','')}→{offer.get('destination','')} {offer.get('value','')}€")
    except Exception as e:
        logger.warning(f"Special offers check failed: {e}")
