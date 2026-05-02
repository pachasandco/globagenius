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
    """Build a Travelpayouts-affiliated Aviasales round-trip search URL.

    Follows the pattern used by scraper/travelpayouts_flights._build_aviasales_url
    (https://www.aviasales.com/search/{ORIG}{DDMM_dep}{DEST}{DDMM_ret}1) and
    appends the affiliate marker when provided.
    """
    try:
        dep = datetime.strptime(departure_date, "%Y-%m-%d")
        ret = datetime.strptime(return_date, "%Y-%m-%d")
        slug = f"{origin}{dep.strftime('%d%m')}{destination}{ret.strftime('%d%m')}1"
        url = f"https://www.aviasales.com/search/{slug}"
    except (ValueError, TypeError):
        url = (
            f"https://www.aviasales.com/search?"
            f"origin={quote(origin)}&destination={quote(destination)}"
        )
    if marker:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}marker={marker}"
    return url


def build_aviasales_oneway_url(
    origin: str,
    destination: str,
    departure_date: str,
    marker: str | None = None,
) -> str:
    """Build a Travelpayouts-affiliated Aviasales ONE-WAY search URL.

    Aviasales encodes one-way trips as the round-trip slug minus the
    return-date segment (https://www.aviasales.com/search/{ORIG}{DDMM_dep}{DEST}1).
    Used for V5 one-way alerts and for the two legs of a split-ticket combo
    so the user can land directly on a one-way booking page.
    """
    try:
        dep = datetime.strptime(departure_date, "%Y-%m-%d")
        slug = f"{origin}{dep.strftime('%d%m')}{destination}1"
        url = f"https://www.aviasales.com/search/{slug}"
    except (ValueError, TypeError):
        url = (
            f"https://www.aviasales.com/search?"
            f"origin={quote(origin)}&destination={quote(destination)}"
        )
    if marker:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}marker={marker}"
    return url
