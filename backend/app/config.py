import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://globegenius.app")
    # IMPORTANT: don't bake a Railway domain in here. Railway rotates
    # public domains on service moves (b887 → 1380 happened twice in
    # this codebase already, both times silently breaking webhooks).
    # Always set BACKEND_URL on Railway and keep this default empty so
    # the backend crashes loudly if it isn't.
    BACKEND_URL: str = os.getenv("BACKEND_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ADMIN_CHAT_ID: str = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    TRAVELPAYOUTS_TOKEN: str = os.getenv("TRAVELPAYOUT_API_KEY", "")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PRICE_ID: str = os.getenv("STRIPE_PRICE_ID", "price_1TN6eFDBicGh3pGqHpuZO6Ym")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_COUPON_ID: str = os.getenv("STRIPE_COUPON_ID", "")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "globegenius-dev-secret-change-in-prod")
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")
    TELEGRAM_WEBHOOK_SECRET: str = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    UNSPLASH_ACCESS_KEY: str = os.getenv("UNSPLASH_ACCESS_KEY", "")
    BREVO_WELCOME_TEMPLATE_ID: int = int(os.getenv("BREVO_WELCOME_TEMPLATE_ID", "0") or 0)
    # Onboarding follow-ups (chantier 10, 2026-05-17).
    # Defaults map to the live Brevo templates (#8 J+1 relance, #9 J+7
    # inactivity). Set to 0 to disable an email — the job then logs the
    # would-be send and skips the actual API call. Note: template #8 must
    # also be flipped to "active" on Brevo, an inactive template is
    # rejected by the transactional API.
    BREVO_RELANCE_TELEGRAM_TEMPLATE_ID: int = int(os.getenv("BREVO_RELANCE_TELEGRAM_TEMPLATE_ID", "8") or 0)
    BREVO_INACTIVITY_TEMPLATE_ID: int = int(os.getenv("BREVO_INACTIVITY_TEMPLATE_ID", "9") or 0)
    # 2026-07-14 : templates beta décommissionnés (feedback nurture J+7
    # id 10, J+14 id 11, feedback ouvert J+15 id 12, lettre de la beta
    # id 19) — flows retirés de onboarding_emails.py pour la prod.
    # Sent when an admin manually downgrades an inactive founder back to
    # the free tier ("you didn't activate, your Premium is removed, your
    # free account stays"). 0 = template not configured yet → the
    # downgrade endpoint still removes Premium but skips the email.
    BREVO_DOWNGRADE_TEMPLATE_ID: int = int(os.getenv("BREVO_DOWNGRADE_TEMPLATE_ID", "0") or 0)
    BREVO_SENDER_EMAIL: str = os.getenv("BREVO_SENDER_EMAIL", "contact@globegenius.app")
    BREVO_SENDER_NAME: str = os.getenv("BREVO_SENDER_NAME", "Globe Genius")
    SCRAPE_FLIGHTS_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_FLIGHTS_INTERVAL_HOURS", "6"))
    SCRAPE_ACCOMMODATIONS_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_ACCOMMODATIONS_INTERVAL_HOURS", "4"))
    BASELINE_RECALC_HOUR: int = int(os.getenv("BASELINE_RECALC_HOUR", "3"))
    DIGEST_HOUR: int = int(os.getenv("DIGEST_HOUR", "8"))
    MIN_DISCOUNT_PCT: int = int(os.getenv("MIN_DISCOUNT_PCT", "40"))
    MIN_SCORE_ALERT: int = int(os.getenv("MIN_SCORE_ALERT", "40"))
    MIN_SCORE_DIGEST: int = int(os.getenv("MIN_SCORE_DIGEST", "30"))
    DATA_FRESHNESS_HOURS: int = int(os.getenv("DATA_FRESHNESS_HOURS", "2"))
    MVP_AIRPORTS: list = field(default_factory=lambda: os.getenv(
        # 2026-07-26: BSL (Bâle-Mulhouse) activé en origine utilisateur.
        # Il était en PASSIVE_ORIGINS le temps de mûrir ; baselines OK
        # (78 fraîches <=21j, ~1150 A/R scrapés, 34 destinations). BSL est
        # le code retenu (historique mûr + meilleurs prix) ; MLH/EAP
        # restent passifs — mêmes vols, codes IATA alternatifs du même
        # aéroport tri-national.
        "MVP_AIRPORTS", "CDG,ORY,LYS,MRS,NCE,BOD,NTE,TLS,BVA,BSL"
    ).split(","))
    # Origins scraped for *future* expansion. Rows from these origins are
    # written to raw_flights with passive=true so the alert dispatcher
    # never touches them — we are just building 6 months of price history
    # so a Brussels / Geneva / Zurich launch ships with a mature baseline
    # from day one. The dispatcher, qualifier, baseline maturity report
    # and split-ticket detector all filter passive rows out.
    PASSIVE_ORIGINS: list = field(default_factory=lambda: [
        o for o in os.getenv(
            "PASSIVE_ORIGINS",
            # BSL/MLH/EAP are three IATA codes for the same tri-national
            # airport (Bâle-Mulhouse-Freiburg). 2026-07-26: BSL matured and
            # was promoted to MVP_AIRPORTS (user-selectable origin). MLH/EAP
            # stay passive — they are alternate codes for the same flights,
            # kept only to widen OTA coverage of the baseline; the
            # dispatcher never reads them so a user only ever sees BSL.
            "BRU,GVA,ZRH,MLH,EAP",
        ).split(",") if o.strip()
    ])
    ADMIN_EMAILS: list = field(default_factory=lambda: [
        e.strip() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
    ])
    # Origins allowed to scrape LONG-HAUL destinations (2026-06-10,
    # was a hardcoded `origin != "CDG"` in 3 call sites). Historical
    # rationale ("only French hub with direct transatlantic service")
    # undersells ORY (French Bee / Corsair / Transat: DOM-TOM, YUL…)
    # and provincial leisure long-haul. Default keeps the historical
    # behaviour; activation = env change on Railway, no deploy:
    #   LONG_HAUL_ORIGINS=CDG,ORY
    # Each added origin ≈ +15-20 long-haul routes × 12 scrapes/day on
    # Travelpayouts + matching raw_flights volume — add origins ONE at
    # a time and watch DB growth. New routes are cold-started by the
    # *-DEST wildcard baselines (CDG history) and seeded properly by
    # the daily enrichment job within a few days; the ≥5-samples and
    # 21-day-freshness gates keep them quiet until then.
    LONG_HAUL_ORIGINS: list = field(default_factory=lambda: [
        o.strip().upper() for o in os.getenv("LONG_HAUL_ORIGINS", "CDG").split(",") if o.strip()
    ])
    TRAVELPAYOUTS_MARKER: str = os.getenv("TRAVELPAYOUTS_MARKER", "")

    def __post_init__(self):
        # 2026-05-23: the guard used to fire only when APP_ENV was the
        # exact string "production". Any other value (a typo like "prod",
        # "Production", or the unchanged default "development" on a real
        # deploy) silently shipped with the public default JWT secret —
        # forgeable tokens = full account impersonation. We now treat
        # everything EXCEPT explicit local/dev/test markers as a
        # production-grade environment that must have real secrets.
        dev_envs = {"development", "dev", "local", "test", "testing", "ci"}
        is_production_grade = self.APP_ENV.strip().lower() not in dev_envs
        if is_production_grade:
            missing = []
            if (
                not self.JWT_SECRET
                or self.JWT_SECRET == "globegenius-dev-secret-change-in-prod"
            ):
                missing.append("JWT_SECRET")
            if not self.ADMIN_API_KEY:
                missing.append("ADMIN_API_KEY")
            if not self.STRIPE_WEBHOOK_SECRET:
                missing.append("STRIPE_WEBHOOK_SECRET")
            if not self.TELEGRAM_WEBHOOK_SECRET:
                missing.append("TELEGRAM_WEBHOOK_SECRET")
            if missing:
                raise RuntimeError(
                    f"Missing/insecure required env vars for a production-grade "
                    f"environment (APP_ENV={self.APP_ENV!r}): {', '.join(missing)}"
                )


# ── Stopover phase 1 (2026-06-09, pairs redesigned 2026-06-12) ─────────
# Curated (hub, final destination) pairs for stopover chains. The hub is
# a city users want to visit for 2-5 days on the way; the spoke is the
# final destination.
#
# ECONOMICS LESSON (48h audit, 2026-06-12): the original pairs were all
# ultra-low-cost European routes (BCN+PMI, MAD+Canaries…) chosen for
# data availability — and produced a structural zero. On those routes
# the direct A/R is already at the Ryanair price floor (~66€ ORY→PMI):
# three separate tickets (≥67€) can NEVER undercut it by the 30%/80€
# qualification bar. A stopover chain only beats the direct A/R where
# the direct A/R is EXPENSIVE — i.e. long-haul or poorly-served routes
# — and where the hub has cheap onward capacity (TAP via LIS, LEVEL /
# Air Europa via MAD, Pegasus via IST).
#
# Constraints per pair: the spoke must be in the priority destinations
# (its inbound spoke→origin legs come from the regular one-way scrape)
# and a direct A/R baseline origin→spoke must exist — today long-haul
# baselines only exist from CDG, so provincial chains stay quiet until
# LONG_HAUL_ORIGINS opens more origins. The stopover_detection funnel
# counters (no_leg3 / no_baseline) make any starving stage visible.
# 2026-06-14 (founder decision): the final destination (spoke) must be
# LONG-HAUL. A stopover only beats the direct A/R when the direct A/R is
# expensive — that's long-haul by definition. The phase-1 European
# spokes (PDL/FNC/JTR) were dropped: their connector legs cost scraping
# budget while their direct A/R is too cheap for a 3-ticket chain to
# ever undercut by 30%. Every spoke below is in LONG_HAUL_DESTINATIONS;
# a startup assertion (see below) enforces this so a future edit can't
# silently re-introduce a short-haul spoke.
STOPOVER_HUB_PAIRS: list[tuple[str, str]] = [
    # Transatlantic via Iberia/TAP hubs — cheap legs on LEVEL / TAP.
    ("MAD", "BOG"),   # Madrid + Bogotá
    ("MAD", "LIM"),   # Madrid + Lima
    ("LIS", "GRU"),   # Lisbonne + São Paulo
    ("LIS", "GIG"),   # Lisbonne + Rio
    ("LIS", "YUL"),   # Lisbonne + Montréal
    # Middle East via Istanbul — Pegasus/flydubai onward capacity.
    ("IST", "DXB"),   # Istanbul + Dubaï
]


IATA_TO_CITY = {
    # ── Aéroports de départ français ──
    "CDG": "Paris CDG",
    "ORY": "Paris Orly",
    "BVA": "Paris Beauvais",
    "LYS": "Lyon",
    "MRS": "Marseille",
    "NCE": "Nice",
    "BOD": "Bordeaux",
    "NTE": "Nantes",
    "TLS": "Toulouse",
    # ── Europe ──
    "LIS": "Lisbonne",
    "BCN": "Barcelone",
    "FCO": "Rome",
    "CIA": "Rome Ciampino",
    "ATH": "Athènes",
    "NAP": "Naples",
    "OPO": "Porto",
    "AMS": "Amsterdam",
    "BER": "Berlin",
    "SXF": "Berlin Schönefeld",
    "PRG": "Prague",
    "BUD": "Budapest",
    "DUB": "Dublin",
    "EDI": "Édimbourg",
    "IST": "Istanbul",
    "MAD": "Madrid",
    "MXP": "Milan Malpensa",
    "LIN": "Milan Linate",
    "BGY": "Milan Bergame",
    "VCE": "Venise",
    "TSF": "Venise Trévise",
    "VIE": "Vienne",
    "WAW": "Varsovie",
    "WMI": "Varsovie Modlin",
    "ZAG": "Zagreb",
    "CPH": "Copenhague",
    "HEL": "Helsinki",
    "OSL": "Oslo",
    "ARN": "Stockholm",
    "NYO": "Stockholm Skavsta",
    "GOT": "Göteborg",
    "AAR": "Aarhus",
    "TRD": "Trondheim",
    "TMP": "Tampere",
    "BRN": "Berne",
    "BSL": "Bâle-Mulhouse",
    # MLH and EAP are alternate IATA codes for the same tri-national
    # airport (BSL = Swiss side, MLH = French side / Mulhouse, EAP =
    # joint EuroAirport code). Different OTAs publish fares under
    # different codes, so we surface a friendly label for all three
    # to avoid raw codes leaking into Telegram alerts.
    "MLH": "Bâle-Mulhouse",
    "EAP": "Bâle-Mulhouse",
    "LUX": "Luxembourg",
    "LJU": "Ljubljana",
    "BTS": "Bratislava",
    "KSC": "Košice",
    "OTP": "Bucarest",
    "CLJ": "Cluj-Napoca",
    "SKP": "Skopje",
    "TIA": "Tirana",
    "PRN": "Pristina",
    "SJJ": "Sarajevo",
    "BEG": "Belgrade",
    "TGD": "Podgorica",
    "AGP": "Malaga",
    "PMI": "Palma de Majorque",
    "TFS": "Ténérife",
    "HER": "Héraklion",
    "SPU": "Split",
    "DBV": "Dubrovnik",
    "ACE": "Lanzarote",
    "ALC": "Alicante",
    "BLQ": "Bologne",
    "BRI": "Bari",
    "BRU": "Bruxelles",
    "CAG": "Cagliari",
    "CFU": "Corfou",
    "CTA": "Catane",
    "FAO": "Faro",
    "FNC": "Madère",
    "FUE": "Fuerteventura",
    "IBZ": "Ibiza",
    "JMK": "Mykonos",
    "JTR": "Santorin",
    "KRK": "Cracovie",
    "LPA": "Las Palmas",
    "OLB": "Olbia",
    "PDL": "Ponta Delgada",
    "RHO": "Rhodes",
    "RIX": "Riga",
    "SAW": "Istanbul Sabiha",
    "SKG": "Thessalonique",
    "SOF": "Sofia",
    "SVQ": "Séville",
    "TIV": "Tivat",
    "TLL": "Tallinn",
    "VLC": "Valence",
    "VNO": "Vilnius",
    "ZRH": "Zurich",
    # ── UK ──
    "LHR": "Londres Heathrow",
    "LGW": "Londres Gatwick",
    "STN": "Londres Stansted",
    "LTN": "Londres Luton",
    "MAN": "Manchester",
    "BHX": "Birmingham",
    "GLA": "Glasgow",
    # ── Afrique du Nord ──
    "RAK": "Marrakech",
    "CMN": "Casablanca",
    "AGA": "Agadir",
    "FEZ": "Fès",
    "NDR": "Nador",
    "TNG": "Tanger",
    "ESU": "Essaouira",
    "TUN": "Tunis",
    "MIR": "Monastir",
    "DJE": "Djerba",
    "ALG": "Alger",
    "ORN": "Oran",
    "CZL": "Constantine",
    "TLM": "Tlemcen",
    "AAE": "Annaba",
    "BJA": "Béjaïa",
    # ── Moyen-Orient / Afrique ──
    "CAI": "Le Caire",
    "TLV": "Tel Aviv",
    "HRG": "Hurghada",
    "SSH": "Charm el-Cheikh",
    "DXB": "Dubaï",
    "CPT": "Le Cap",
    "JNB": "Johannesburg",
    "ZNZ": "Zanzibar",
    # ── Long-courrier ──
    "JFK": "New York",
    "EWR": "New York Newark",
    "YUL": "Montréal",
    "MIA": "Miami",
    "LAX": "Los Angeles",
    "SFO": "San Francisco",
    "CUN": "Cancún",
    "PUJ": "Punta Cana",
    "BOG": "Bogotá",
    "GIG": "Rio de Janeiro",
    "EZE": "Buenos Aires",
    "LIM": "Lima",
    "SCL": "Santiago",
    "BKK": "Bangkok",
    "SIN": "Singapour",
    "KUL": "Kuala Lumpur",
    "NRT": "Tokyo Narita",
    "HND": "Tokyo Haneda",
    "ICN": "Séoul",
    "HKG": "Hong Kong",
    "BOM": "Mumbai",
    "DEL": "Delhi",
    "MLE": "Malé",
    "MRU": "Maurice",
    "RUN": "La Réunion",
    "PPT": "Papeete",
    "GVA": "Genève",
    "SYD": "Sydney",
    # ── Long-courrier — pack complété 2026-05-19 pour ne plus afficher
    # de code IATA brut dans les alertes Telegram. Lorsqu'un IATA absent
    # se retrouve dans une alerte split_ticket / oneway, l'utilisateur
    # voit "YVR" au lieu de "Vancouver" — pour éviter ça, on enrichit
    # ici dès qu'on découvre un trou (cf. sent_alerts table).
    "YVR": "Vancouver",
    "YYZ": "Toronto",
    "YOW": "Ottawa",
    "ATL": "Atlanta",
    "ORD": "Chicago",
    "DFW": "Dallas",
    "SEA": "Seattle",
    "BOS": "Boston",
    "IAD": "Washington",
    "ANC": "Anchorage",
    "DPS": "Bali",
    "HKT": "Phuket",
    "CMB": "Colombo",
    "MNL": "Manille",
    "ADD": "Addis-Abeba",
    "NBO": "Nairobi",
    "AUH": "Abu Dhabi",
    "DOH": "Doha",
    "AMM": "Amman",
    "BEY": "Beyrouth",
    "RUH": "Riyad",
    "JED": "Djeddah",
    "LOS": "Lagos",
    "ABV": "Abuja",
    "GRU": "São Paulo",
}


def iata_label(code: str) -> str:
    """Return 'Ville (CODE)' for display in alerts and UI. Falls back to code alone."""
    city = IATA_TO_CITY.get(code)
    if city:
        return f"{city} ({code})"
    return code


DESTINATION_POPULARITY = {
    "BCN": 95, "LIS": 90, "FCO": 88, "ATH": 85, "AMS": 87,
    "MAD": 86, "IST": 82, "PRG": 80, "BUD": 78, "RAK": 83,
    "NAP": 75, "OPO": 72, "MXP": 77, "VCE": 74, "DUB": 70,
    "BER": 76, "VIE": 73, "CPH": 68, "EDI": 65, "HEL": 60,
    "OSL": 58, "ARN": 62, "WAW": 55, "ZAG": 50, "TUN": 52,
    "CMN": 56, "CAI": 64, "TLV": 66, "AGP": 79, "PMI": 81,
    "TFS": 77, "HER": 71, "SPU": 69, "DBV": 73,
    "ACE": 71, "ALC": 72, "BLQ": 65, "BRI": 63, "BRU": 64,
    "CAG": 66, "CFU": 69, "CTA": 68, "FAO": 74, "FNC": 70,
    "FUE": 72, "HRG": 67, "IBZ": 85, "JMK": 82, "JTR": 86,
    "KRK": 71, "LPA": 73, "OLB": 67, "PDL": 62, "RHO": 76,
    "RIX": 58, "SAW": 72, "SKG": 60, "SOF": 56, "SSH": 69,
    "SVQ": 74, "TIV": 61, "TLL": 59, "VLC": 76, "VNO": 54,
    "ZRH": 68,
    # Long-courrier
    "JFK": 92, "YUL": 70, "CUN": 78, "PUJ": 76, "BKK": 88,
    "NRT": 85, "DXB": 90, "MLE": 82, "MRU": 80, "RUN": 72,
    "PPT": 65, "GIG": 74, "SYD": 78, "MIA": 86, "LAX": 84,
    "BOG": 64, "BOM": 72, "CPT": 78, "DEL": 75, "EZE": 80,
    "HKG": 79, "HND": 88, "ICN": 77, "JNB": 70, "KUL": 71,
    "LIM": 68, "SCL": 73, "SIN": 86, "ZNZ": 74,
}

settings = Settings()
