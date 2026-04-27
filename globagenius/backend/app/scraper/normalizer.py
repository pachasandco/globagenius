import hashlib
from datetime import datetime, timedelta, timezone
from app.config import settings

CURRENCY_TO_EUR = {
    "EUR": 1.0,
    "USD": 0.92,
    "GBP": 1.16,
    "CHF": 1.04,
}


def _to_eur(price: float, currency: str) -> float:
    rate = CURRENCY_TO_EUR.get(currency.upper(), 1.0)
    return round(price * rate, 2)


def _title_case_city(city: str) -> str:
    return city.strip().title()


def compute_flight_hash(
    origin: str, destination: str, departure_date: str, return_date: str, price: float, source: str
) -> str:
    raw = f"{origin}|{destination}|{departure_date}|{return_date}|{price}|{source}"
    return hashlib.sha256(raw.encode()).hexdigest()


def compute_accommodation_hash(
    city: str, name: str, check_in: str, check_out: str, total_price: float, source: str
) -> str:
    raw = f"{city}|{name}|{check_in}|{check_out}|{total_price}|{source}"
    return hashlib.sha256(raw.encode()).hexdigest()


def normalize_flight(raw: dict, source: str) -> dict:
    price = _to_eur(raw["price"], raw.get("currency", "EUR"))
    now = datetime.now(timezone.utc)
    return {
        "hash": compute_flight_hash(
            raw["origin"], raw["destination"],
            raw["departureDate"], raw["returnDate"],
            price, source,
        ),
        "origin": raw["origin"],
        "destination": raw["destination"],
        "departure_date": raw["departureDate"],
        "return_date": raw["returnDate"],
        "price": price,
        "airline": raw.get("airline"),
        "stops": raw.get("stops", 0),
        "source_url": raw.get("url"),
        "source": source,
        "scraped_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=settings.DATA_FRESHNESS_HOURS)).isoformat(),
    }


def normalize_accommodation(raw: dict) -> dict:
    price_per_night = _to_eur(raw["pricePerNight"], raw.get("currency", "EUR"))
    total_price = _to_eur(raw["totalPrice"], raw.get("currency", "EUR"))
    city = _title_case_city(raw["city"])
    now = datetime.now(timezone.utc)
    return {
        "hash": compute_accommodation_hash(
            city, raw["name"],
            raw["checkIn"], raw["checkOut"],
            total_price, raw["source"],
        ),
        "city": city,
        "name": raw["name"],
        "price_per_night": price_per_night,
        "total_price": total_price,
        "rating": raw.get("rating"),
        "check_in": raw["checkIn"],
        "check_out": raw["checkOut"],
        "source_url": raw.get("url"),
        "source": raw["source"],
        "scraped_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=settings.DATA_FRESHNESS_HOURS)).isoformat(),
    }
