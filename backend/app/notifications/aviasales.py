"""Aviasales deep-link builder with Travelpayouts affiliate marker."""
from datetime import datetime
from urllib.parse import quote


def build_aviasales_url(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    marker: str | None = None,
) -> str:
    """Build a Travelpayouts-affiliated Aviasales search URL.

    Follows the pattern used by scraper/travelpayouts_flights._build_aviasales_url
    (https://www.aviasales.com/search/{ORIG}{DDMM_dep}{DEST}{DDMM_ret}1) and
    appends the affiliate marker when provided.
    """
    try:
        dep = datetime.strptime(departure_date, "%Y-%m-%d")
        ret = datetime.strptime(return_date, "%Y-%m-%d")
        slug = f"{origin}{dep.strftime('%d%m')}{destination}{ret.strftime('%d%m')}1"
        url = f"https://www.aviasales.com/search/{slug}?currency=eur"
    except (ValueError, TypeError):
        url = (
            f"https://www.aviasales.com/search?"
            f"origin={quote(origin)}&destination={quote(destination)}&currency=eur"
        )
    if marker:
        url = f"{url}&marker={marker}"
    return url
