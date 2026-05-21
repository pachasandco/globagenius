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


# Names that map to a meta-search agency / OTA, NOT to the airline that
# actually operates the flight. When the raw `airline` field on a deal
# resolves to one of these, we deliberately hide it from the user-facing
# alert — showing "Trip.com" or "Kiwi" as if it were the carrier is
# misleading.
_AGENCY_DISPLAY_NAMES: set[str] = {
    "aviasales", "kupibilet", "trip.com", "ozon travel", "travelata",
    "onlinetours", "clickavia", "kayak", "skyscanner", "kiwi",
    "kiwi.com", "kupi.com", "farera", "city.travel", "onetwotrip",
    "mego.travel", "mytrip.com", "tickets", "tickets.com",
}


def is_agency(name: str | None) -> bool:
    """True when `name` (already normalised) refers to an OTA / meta-search
    agency rather than the airline operating the flight. The Telegram
    alert formatter uses this to decide whether to surface the carrier
    or stay silent."""
    if not name:
        return False
    return name.strip().lower() in _AGENCY_DISPLAY_NAMES


# Official baggage-policy URLs per airline. Keyed by the brand name AFTER
# normalisation by normalize_airline_name(). Linked from a discreet 🎒
# icon next to the carrier in the Telegram alert so users can check
# fees / dimensions before booking — critical for LCC where the
# advertised fare excludes any cabin/hold luggage.
_BAGGAGE_URLS: dict[str, str] = {
    "Ryanair": "https://www.ryanair.com/fr/fr/utile/aide/baggages",
    "easyJet": "https://www.easyjet.com/fr/aide/bagages",
    "Vueling": "https://www.vueling.com/fr/services-vueling/avant-votre-vol/bagages",
    "Transavia": "https://www.transavia.com/fr-FR/preparer-mon-voyage/bagages/",
    "Wizz Air": "https://wizzair.com/fr-fr/informations-et-services/voyager/bagages",
    "Pegasus": "https://www.flypgs.com/fr/services-en-vol/bagages",
    "Norwegian": "https://www.norwegian.com/fr/voyage/information-de-voyage/bagages/",
    "Air France": "https://www.airfrance.fr/FR/fr/local/process/standardbooking/baggageinformation.htm",
    "KLM": "https://www.klm.fr/information/preparation-voyage/bagages",
    "Lufthansa": "https://www.lufthansa.com/fr/fr/bagages",
    "British Airways": "https://www.britishairways.com/fr-fr/information/baggage-essentials",
    "Iberia": "https://www.iberia.com/fr/bagages/",
    "TAP Portugal": "https://www.flytap.com/fr-fr/bagages",
    "Swiss": "https://www.swiss.com/fr/fr/prepare/baggage",
    "Austrian": "https://www.austrian.com/fr/fr/baggage",
    "Brussels Airlines": "https://www.brusselsairlines.com/fr-be/prepare/baggage",
    "SAS": "https://www.flysas.com/fr-fr/voyager-avec-sas/bagages/",
    "Finnair": "https://www.finnair.com/fr-fr/bagages",
    "Aegean": "https://en.aegeanair.com/travel-information/baggage/",
    "Turkish Airlines": "https://www.turkishairlines.com/fr-fr/voler-avec-nous/baggage/",
    "Royal Air Maroc": "https://www.royalairmaroc.com/fr-fr/voyage-confort/bagages",
    "Emirates": "https://www.emirates.com/fr/french/before-you-fly/baggage/",
    "Qatar Airways": "https://www.qatarairways.com/fr-fr/baggage.html",
    "Etihad": "https://www.etihad.com/fr-fr/fly-etihad/baggage",
    "Air Canada": "https://www.aircanada.com/fr-ca/travel-information/baggage",
    "WestJet": "https://www.westjet.com/fr-ca/voyage/bagages",
    "JetBlue": "https://www.jetblue.com/help/baggage",
    "American Airlines": "https://www.aa.com/i18n/travel-info/baggage/baggage.jsp",
    "Delta": "https://www.delta.com/us/en/baggage/overview",
    "United": "https://www.united.com/ual/fr/fr/fly/travel/baggage.html",
    "Iberia Express": "https://www.iberia.com/fr/bagages/",
    "Virgin Atlantic": "https://www.virginatlantic.com/gb/en/baggage.html",
}


def baggage_url(airline_name: str | None) -> str | None:
    """Look up the official baggage-policy URL for an airline. Returns
    None when the carrier is unknown OR when the input is actually an
    agency name (Trip.com, Kiwi…). Caller should not render a 🎒 link
    when this returns None."""
    if not airline_name:
        return None
    if is_agency(airline_name):
        return None
    return _BAGGAGE_URLS.get(airline_name.strip())
