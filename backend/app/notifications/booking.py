"""Booking.com deep-link builder with Travelpayouts affiliate marker."""
from urllib.parse import quote_plus


def build_booking_url(
    city: str,
    checkin: str,
    checkout: str,
    marker: str | None = None,
) -> str:
    """Build a Booking.com search URL pre-filled with city + dates.

    Booking.com accepts the affiliate `aid` parameter for tracking.
    Travelpayouts' Partner ID doubles as the Booking.com aid.
    """
    base = (
        "https://www.booking.com/searchresults.html"
        f"?ss={quote_plus(city)}"
        f"&checkin={checkin}"
        f"&checkout={checkout}"
    )
    if marker:
        base += f"&aid={marker}"
    return base
