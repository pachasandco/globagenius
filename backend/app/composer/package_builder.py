from datetime import datetime, timezone
from dateutil.parser import parse as parse_date
from app.config import IATA_TO_CITY, settings
from app.analysis.scorer import compute_score

MIN_RATING = 4.0
MAX_PACKAGES_PER_FLIGHT = 3


def _get_city_for_iata(code: str) -> str | None:
    return IATA_TO_CITY.get(code)


def _baseline_key(city: str, source: str) -> str:
    return f"{city.lower()}-{source}"


def match_accommodations(flight: dict, accommodations: list[dict]) -> list[dict]:
    city = _get_city_for_iata(flight["destination"])
    if not city:
        return []

    now = datetime.now(timezone.utc)
    matched = []

    for acc in accommodations:
        if acc["city"] != city:
            continue
        if acc["check_in"] != flight["departure_date"]:
            continue
        if acc["check_out"] != flight["return_date"]:
            continue
        if acc.get("rating") is not None and acc["rating"] < MIN_RATING:
            continue
        expires = parse_date(acc["expires_at"])
        if expires < now:
            continue
        matched.append(acc)

    return matched


def build_packages(
    flight: dict,
    accommodations: list[dict],
    flight_baseline: dict,
    accommodation_baselines: dict,
) -> list[dict]:
    matched = match_accommodations(flight, accommodations)
    if not matched:
        return []

    candidates = []
    now = datetime.now(timezone.utc)

    for acc in matched:
        bl_key = _baseline_key(acc["city"], acc["source"])
        acc_baseline = accommodation_baselines.get(bl_key)
        if not acc_baseline:
            continue

        total_price = flight["price"] + acc["total_price"]
        baseline_total = flight_baseline["avg_price"] + acc_baseline["avg_price"]

        if baseline_total <= 0:
            continue

        discount_pct = (baseline_total - total_price) / baseline_total * 100

        if discount_pct < 20:  # Accept 20%+ for free plan, 40%+ for premium
            continue

        score = compute_score(
            discount_pct=discount_pct,
            destination_code=flight["destination"],
            date_flexibility=0,
            accommodation_rating=acc.get("rating"),
        )

        candidates.append({
            "flight_id": flight["id"],
            "origin": flight["origin"],
            "destination": flight["destination"],
            "departure_date": flight["departure_date"],
            "return_date": flight["return_date"],
            "flight_price": flight["price"],
            "accommodation_id": acc["id"],
            "accommodation_price": acc["total_price"],
            "total_price": round(total_price, 2),
            "baseline_total": round(baseline_total, 2),
            "discount_pct": round(discount_pct, 2),
            "score": score,
            "status": "active",
            "created_at": now.isoformat(),
            "expires_at": acc["expires_at"],
        })

    candidates.sort(key=lambda p: p["score"], reverse=True)
    return candidates[:MAX_PACKAGES_PER_FLIGHT]
