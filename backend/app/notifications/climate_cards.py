"""Estimated monthly climate context for Telegram deal cards.

This is deliberately not a forecast. Values are broad, rounded night/day
ranges intended to help with trips booked weeks or months ahead. Unknown
destinations stay silent rather than displaying a guessed value.
"""

from __future__ import annotations

import inspect
from datetime import datetime
from typing import Any, Callable


_FR_MONTHS = (
    "", "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)

# Each profile contains 12 "low,high,icon" values (January → December).
# The ranges are intentionally rounded; the copy always says "environ".
_PROFILE_DATA = {
    "oceanic": "4,11,🌦️;4,12,🌦️;6,14,🌦️;8,17,🌤️;11,20,🌤️;14,23,🌤️;16,25,🌤️;16,25,🌤️;14,22,🌤️;11,18,🌦️;7,14,🌦️;5,12,🌦️",
    "mediterranean": "7,15,🌦️;8,16,🌦️;10,18,🌤️;12,21,🌤️;16,25,☀️;20,29,☀️;23,32,☀️;23,32,☀️;20,28,☀️;16,24,🌤️;11,19,🌦️;8,16,🌦️",
    "med_hot": "9,17,🌤️;10,18,🌤️;12,21,🌤️;15,24,🌤️;18,28,☀️;22,33,☀️;25,36,☀️;25,36,☀️;22,32,☀️;18,27,☀️;13,22,🌦️;10,18,🌦️",
    "continental": "-3,5,❄️;-2,7,❄️;2,12,🌤️;6,18,🌤️;11,23,🌤️;15,27,🌤️;17,30,☀️;16,29,☀️;12,23,🌤️;7,16,🌤️;2,9,🌦️;-1,5,❄️",
    "nordic": "-8,1,❄️;-8,2,❄️;-4,6,❄️;1,11,🌤️;6,17,🌤️;10,21,🌤️;13,24,🌤️;12,22,🌤️;8,16,🌦️;3,10,🌦️;-2,4,❄️;-6,2,❄️",
    "canary": "15,22,☀️;15,22,☀️;16,23,☀️;17,24,☀️;18,25,☀️;20,27,☀️;22,29,☀️;23,30,☀️;22,29,☀️;20,27,☀️;18,25,🌤️;16,23,🌤️",
    "azores": "12,17,🌦️;12,17,🌦️;12,18,🌦️;13,19,🌦️;15,21,🌤️;17,23,🌤️;19,25,🌤️;20,26,🌤️;19,25,🌦️;17,23,🌦️;15,20,🌦️;13,18,🌦️",
    "maghreb_coast": "8,17,🌦️;9,18,🌤️;11,20,🌤️;13,23,🌤️;16,26,☀️;20,30,☀️;23,34,☀️;23,34,☀️;21,31,☀️;17,27,☀️;12,21,🌦️;9,18,🌦️",
    "morocco_inland": "6,19,☀️;8,21,☀️;10,24,☀️;13,27,☀️;16,31,☀️;20,36,☀️;23,39,☀️;23,39,☀️;20,34,☀️;16,29,☀️;10,23,☀️;7,19,☀️",
    "desert": "13,24,☀️;15,26,☀️;18,30,☀️;22,35,☀️;26,39,☀️;29,42,☀️;31,44,☀️;31,44,☀️;28,41,☀️;24,36,☀️;19,30,☀️;15,26,☀️",
    "north_america_east": "-5,5,❄️;-4,7,❄️;1,12,🌤️;7,19,🌤️;13,24,🌤️;18,29,🌤️;21,32,☀️;20,31,🌤️;16,27,🌤️;10,20,🌤️;4,13,🌤️;-2,7,❄️",
    "north_america_west": "6,15,🌦️;7,16,🌦️;8,18,🌤️;10,21,🌤️;13,24,☀️;15,27,☀️;17,30,☀️;17,30,☀️;15,28,☀️;12,23,🌤️;8,18,🌦️;6,15,🌦️",
    "subtropical_america": "18,26,🌤️;19,27,🌤️;20,28,🌤️;22,30,🌤️;24,32,🌦️;25,33,🌦️;26,33,🌦️;26,33,🌦️;25,32,🌦️;23,31,🌦️;21,29,🌤️;19,27,🌤️",
    "tropical_humid": "23,31,🌤️;23,32,🌤️;24,33,🌤️;25,34,🌦️;25,33,🌦️;25,32,🌦️;25,32,🌦️;25,32,🌦️;24,32,🌦️;24,32,🌦️;24,32,🌦️;23,31,🌦️",
    "east_asia": "0,10,❄️;1,11,❄️;5,16,🌤️;10,21,🌤️;15,25,🌤️;19,28,🌦️;23,32,🌦️;24,33,🌦️;20,29,🌦️;14,23,🌤️;8,17,🌤️;3,12,🌤️",
    "india_north": "8,21,☀️;11,25,☀️;16,31,☀️;22,38,☀️;27,42,☀️;29,41,☀️;27,36,🌦️;26,34,🌦️;25,34,🌦️;20,33,☀️;14,28,☀️;9,23,☀️",
    "india_west": "19,31,☀️;20,32,☀️;23,34,☀️;26,34,☀️;28,34,🌤️;26,31,🌧️;25,30,🌧️;25,30,🌧️;25,31,🌦️;24,33,🌤️;22,33,☀️;20,32,☀️",
    "highland_tropical": "8,21,🌦️;8,22,🌦️;9,22,🌦️;9,21,🌦️;9,21,🌦️;8,21,🌤️;8,21,🌤️;8,22,🌤️;8,22,🌦️;9,21,🌦️;9,21,🌦️;8,21,🌦️",
    "southern_temperate": "17,29,☀️;17,29,☀️;15,27,🌤️;12,23,🌤️;9,19,🌤️;6,16,🌦️;5,15,🌦️;6,17,🌤️;8,20,🌤️;11,23,🌤️;14,26,🌤️;16,28,☀️",
    "indian_ocean": "24,31,🌦️;24,31,🌦️;24,31,🌦️;23,30,🌦️;22,28,🌤️;20,27,🌤️;19,26,🌤️;19,26,🌤️;20,27,🌤️;21,28,🌤️;22,29,🌤️;23,30,🌦️",
    "lima_coast": "20,27,🌤️;21,28,🌤️;20,27,🌤️;18,24,🌤️;16,21,☁️;15,19,☁️;14,18,☁️;14,18,☁️;14,19,☁️;15,20,☁️;17,22,🌤️;19,25,🌤️",
    "anchorage": "-12,-5,❄️;-10,-3,❄️;-7,2,❄️;-1,8,❄️;5,14,🌤️;9,18,🌤️;12,20,🌤️;10,18,🌦️;6,14,🌦️;-1,6,❄️;-8,-2,❄️;-11,-4,❄️",
}


def _profiles() -> dict[str, tuple[tuple[int, int, str], ...]]:
    parsed = {}
    for name, raw in _PROFILE_DATA.items():
        parsed[name] = tuple(
            (int(low), int(high), icon)
            for low, high, icon in (item.split(",") for item in raw.split(";"))
        )
    return parsed


_PROFILES = _profiles()
_IATA_PROFILE: dict[str, str] = {}


def _assign(profile: str, codes: str) -> None:
    for code in codes.split():
        _IATA_PROFILE[code] = profile


_assign("oceanic", "CDG ORY BVA LYS BOD NTE TLS LIS OPO AMS DUB EDI BRU LHR LGW STN LTN MAN BHX GLA LUX")
_assign("mediterranean", "MRS NCE BCN FCO CIA NAP MXP LIN BGY VCE TSF BLQ BRI CAG CTA OLB ZAG SPU DBV TIV FNC")
_assign("med_hot", "ATH IST SAW MAD AGP PMI HER ALC CFU IBZ JMK JTR RHO SKG SVQ VLC FAO TIA SKP TGD TLV BEY AMM")
_assign("continental", "BER SXF PRG BUD VIE WAW WMI KRK ZRH GVA BRN BSL MLH EAP LJU BTS KSC OTP CLJ PRN SJJ BEG SOF RIX TLL VNO")
_assign("nordic", "CPH HEL OSL ARN NYO GOT AAR TRD TMP")
_assign("canary", "TFS ACE FUE LPA")
_assign("azores", "PDL")
_assign("maghreb_coast", "CMN AGA NDR TNG ESU TUN MIR DJE ALG ORN CZL TLM AAE BJA")
_assign("morocco_inland", "RAK FEZ")
_assign("desert", "CAI HRG SSH DXB AUH DOH RUH JED")
_assign("north_america_east", "JFK EWR YUL YYZ YOW ATL ORD DFW BOS IAD")
_assign("north_america_west", "LAX SFO YVR SEA")
_assign("subtropical_america", "MIA CUN PUJ")
_assign("tropical_humid", "BKK SIN KUL HKG DPS HKT CMB MNL ZNZ LOS ABV")
_assign("east_asia", "NRT HND ICN")
_assign("india_north", "DEL")
_assign("india_west", "BOM")
_assign("highland_tropical", "BOG ADD NBO JNB")
_assign("southern_temperate", "GIG GRU EZE SCL CPT SYD")
_assign("indian_ocean", "MLE MRU RUN PPT")
_assign("lima_coast", "LIM")
_assign("anchorage", "ANC")


def _parse_date(value: Any) -> datetime | None:
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d") if value else None
    except (TypeError, ValueError):
        return None


def climate_summary(
    destination_iata: str,
    departure_date: Any,
    return_date: Any = None,
    *,
    include_period: bool = True,
) -> str | None:
    """Build a concise climate estimate, or None when data is unavailable."""

    profile = _PROFILES.get(_IATA_PROFILE.get((destination_iata or "").upper(), ""))
    departure = _parse_date(departure_date)
    if not profile or not departure:
        return None
    end = _parse_date(return_date) or departure
    start_low, start_high, start_icon = profile[departure.month - 1]
    end_low, end_high, end_icon = profile[end.month - 1]
    low, high = min(start_low, end_low), max(start_high, end_high)

    icons = {start_icon, end_icon}
    icon = next(
        (candidate for candidate in ("🌧️", "🌦️", "❄️", "☀️", "☁️", "🌤️") if candidate in icons),
        start_icon,
    )
    if not include_period:
        return f"{icon} Climat habituel : environ {low}–{high} °C"
    if departure.month == end.month:
        period = f"en {_FR_MONTHS[departure.month]}"
    else:
        period = f"de {_FR_MONTHS[departure.month]} à {_FR_MONTHS[end.month]}"
    return f"{icon} Climat habituel {period} : environ {low}–{high} °C"


def _bind(original: Callable[..., str], args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    try:
        return dict(inspect.signature(original).bind_partial(*args, **kwargs).arguments)
    except (TypeError, ValueError):
        return dict(kwargs)


def _insert(message: str, addition: str | None, *, prefix: str = "", contains: str = "") -> str:
    if not addition:
        return message
    lines = message.splitlines()
    for index, line in enumerate(lines):
        if (prefix and line.lstrip().startswith(prefix)) or (contains and contains in line):
            lines.insert(index + 1, addition)
            return "\n".join(lines)
    return message


def _wrap_simple(original: Callable[..., str], payload_name: str) -> Callable[..., str]:
    def wrapper(*args: Any, **kwargs: Any) -> str:
        bound = _bind(original, args, kwargs)
        payload = bound.get(payload_name) or {}
        summary = climate_summary(
            payload.get("destination", ""),
            payload.get("departure_date"),
            payload.get("return_date"),
        )
        return _insert(original(*args, **kwargs), summary, prefix="📅")
    return wrapper


def install_climate_card_formatters(telegram_module: Any) -> None:
    """Patch message formatters once; dispatch and Freemium policy stay unchanged."""

    if getattr(telegram_module, "_climate_cards_installed", False):
        return

    telegram_module.format_deal_alert = _wrap_simple(telegram_module.format_deal_alert, "package")
    telegram_module.format_flight_deal_alert = _wrap_simple(telegram_module.format_flight_deal_alert, "flight")
    telegram_module.format_oneway_deal_alert = _wrap_simple(telegram_module.format_oneway_deal_alert, "flight")

    grouped_original = telegram_module.format_grouped_flight_alerts

    def grouped_wrapper(*args: Any, **kwargs: Any) -> str:
        bound = _bind(grouped_original, args, kwargs)
        destination = bound.get("destination_iata", "")
        offers = bound.get("offers") or []
        message = grouped_original(*args, **kwargs)
        additions: dict[str, str] = {}
        for offer in offers:
            departure = _parse_date(offer.get("departure_date"))
            summary = climate_summary(destination, offer.get("departure_date"), include_period=False)
            if departure and summary:
                header = f"📅 *{telegram_module._FR_MONTHS_LONG[departure.month]} {departure.year}*"
                additions.setdefault(header, summary)
        output: list[str] = []
        for line in message.splitlines():
            output.append(line)
            if line in additions:
                output.append(additions[line])
        return "\n".join(output)

    telegram_module.format_grouped_flight_alerts = grouped_wrapper

    split_original = telegram_module.format_split_ticket_alert

    def split_wrapper(*args: Any, **kwargs: Any) -> str:
        bound = _bind(split_original, args, kwargs)
        outbound, inbound = bound.get("outbound") or {}, bound.get("inbound") or {}
        summary = climate_summary(
            outbound.get("destination", ""),
            outbound.get("departure_date"),
            inbound.get("departure_date"),
        )
        return _insert(split_original(*args, **kwargs), summary, contains="✅ 2 billets vérifiés")

    telegram_module.format_split_ticket_alert = split_wrapper

    stopover_original = telegram_module.format_stopover_alert

    def stopover_wrapper(*args: Any, **kwargs: Any) -> str:
        bound = _bind(stopover_original, args, kwargs)
        leg2, leg3 = bound.get("leg2") or {}, bound.get("leg3") or {}
        summary = climate_summary(
            leg2.get("destination", ""),
            leg2.get("departure_date"),
            leg3.get("departure_date"),
        )
        return _insert(stopover_original(*args, **kwargs), summary, contains="✅ 3 billets vérifiés")

    telegram_module.format_stopover_alert = stopover_wrapper
    telegram_module._climate_cards_installed = True
