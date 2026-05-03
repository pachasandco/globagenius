"""Carrier / agency name normalisation for user-facing alerts.

Travelpayouts hands us names from many sources — sometimes a 2-letter
IATA carrier code (FR, AF), sometimes a French/English brand
(Air France, Ryanair), sometimes the Russian or Cyrillic transliteration
of the meta-search agency that surfaced the fare (Авиасейлс, Купибилет).

The Cyrillic strings end up directly in the Telegram alert and look
broken to a French reader. We map known cases to a clean Latin-script
label, and pass anything we don't recognise through unchanged.
"""

# Cyrillic / non-Latin agency names → readable equivalents.
# Matched case-insensitively and after stripping whitespace.
_AGENCY_FIXUPS: dict[str, str] = {
    # Russian transliterations of meta-search agencies surfaced by
    # Travelpayouts. Direct rendering in Telegram = unreadable, so we
    # ship a Latin-script version of the same brand.
    "авиасейлс": "Aviasales",
    "купибилет": "Kupibilet",
    "трип": "Trip.com",
    "озон трэвел": "Ozon Travel",
    "тревелата": "Travelata",
    "онлайнтурс": "OnlineTours",
    "клиавиа": "Clickavia",
    "clickavia": "Clickavia",
    "kayak": "Kayak",
    "skyscanner": "Skyscanner",
    "kiwi.com": "Kiwi",
}

# IATA 2-letter carrier codes → human-friendly French label.
# Only the most common carriers we actually see in qualifications.
_IATA_FIXUPS: dict[str, str] = {
    "AF": "Air France",
    "U2": "easyJet",
    "FR": "Ryanair",
    "VY": "Vueling",
    "TO": "Transavia",
    "HV": "Transavia",
    "IB": "Iberia",
    "BA": "British Airways",
    "LH": "Lufthansa",
    "KL": "KLM",
    "OS": "Austrian",
    "LX": "Swiss",
    "SK": "SAS",
    "DY": "Norwegian",
    "AY": "Finnair",
    "TP": "TAP Portugal",
    "SU": "Aeroflot",
    "TK": "Turkish Airlines",
    "AT": "Royal Air Maroc",
    "EK": "Emirates",
    "QR": "Qatar Airways",
    "EY": "Etihad",
    "SQ": "Singapore Airlines",
    "JL": "JAL",
    "NH": "ANA",
    "CX": "Cathay Pacific",
    "KE": "Korean Air",
    "OZ": "Asiana",
    "AA": "American Airlines",
    "DL": "Delta",
    "UA": "United",
    "AC": "Air Canada",
    "WS": "WestJet",
    "B6": "JetBlue",
    "AS": "Alaska Airlines",
    "VS": "Virgin Atlantic",
    "JU": "Air Serbia",
    "OK": "Czech Airlines",
    "RO": "Tarom",
    "A3": "Aegean",
    "PC": "Pegasus",
    "WG": "Wizz Air",
    "W6": "Wizz Air",
    "PS": "Ukraine Airlines",
    "MS": "EgyptAir",
    "ET": "Ethiopian",
    "LX2": "Swiss",
}


def normalize_airline_name(raw: str | None) -> str:
    """Return a clean human-readable label for a carrier / agency.

    - 2-letter IATA codes are resolved to a brand name (FR → Ryanair).
    - Cyrillic agency names are mapped to their Latin-script form
      (Авиасейлс → Aviasales).
    - Anything else passes through unchanged so we don't accidentally
      mangle a perfectly fine name we hadn't anticipated.
    """
    if not raw:
        return ""
    cleaned = raw.strip()
    # IATA codes are exactly two characters and uppercase
    upper = cleaned.upper()
    if len(cleaned) == 2 and upper in _IATA_FIXUPS:
        return _IATA_FIXUPS[upper]
    # Agency / brand match — case-insensitive lookup
    lower = cleaned.lower()
    if lower in _AGENCY_FIXUPS:
        return _AGENCY_FIXUPS[lower]
    return cleaned
