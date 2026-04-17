import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://globegenius.app")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ADMIN_CHAT_ID: str = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    TRAVELPAYOUTS_TOKEN: str = os.getenv("TRAVELPAYOUT_API_KEY", "")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PRICE_ID: str = os.getenv("STRIPE_PRICE_ID", "price_1TKhmOD7eB0iNRMdzxmxjRJa")
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
    SCRAPE_FLIGHTS_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_FLIGHTS_INTERVAL_HOURS", "6"))
    SCRAPE_ACCOMMODATIONS_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_ACCOMMODATIONS_INTERVAL_HOURS", "4"))
    BASELINE_RECALC_HOUR: int = int(os.getenv("BASELINE_RECALC_HOUR", "3"))
    DIGEST_HOUR: int = int(os.getenv("DIGEST_HOUR", "8"))
    MIN_DISCOUNT_PCT: int = int(os.getenv("MIN_DISCOUNT_PCT", "40"))
    MIN_SCORE_ALERT: int = int(os.getenv("MIN_SCORE_ALERT", "40"))
    MIN_SCORE_DIGEST: int = int(os.getenv("MIN_SCORE_DIGEST", "30"))
    DATA_FRESHNESS_HOURS: int = int(os.getenv("DATA_FRESHNESS_HOURS", "2"))
    MVP_AIRPORTS: list = field(default_factory=lambda: os.getenv(
        "MVP_AIRPORTS", "CDG,ORY,LYS,MRS,NCE,BOD,NTE,TLS"
    ).split(","))
    ADMIN_EMAILS: list = field(default_factory=lambda: [
        e.strip() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
    ])
    TRAVELPAYOUTS_MARKER: str = os.getenv("TRAVELPAYOUTS_MARKER", "")


IATA_TO_CITY = {
    "LIS": "Lisbon",
    "BCN": "Barcelona",
    "FCO": "Rome",
    "ATH": "Athens",
    "NAP": "Naples",
    "OPO": "Porto",
    "AMS": "Amsterdam",
    "BER": "Berlin",
    "PRG": "Prague",
    "BUD": "Budapest",
    "DUB": "Dublin",
    "EDI": "Edinburgh",
    "IST": "Istanbul",
    "MAD": "Madrid",
    "MXP": "Milan",
    "VCE": "Venice",
    "VIE": "Vienna",
    "WAW": "Warsaw",
    "ZAG": "Zagreb",
    "CPH": "Copenhagen",
    "HEL": "Helsinki",
    "OSL": "Oslo",
    "ARN": "Stockholm",
    "RAK": "Marrakech",
    "TUN": "Tunis",
    "CMN": "Casablanca",
    "CAI": "Cairo",
    "TLV": "Tel Aviv",
    "AGP": "Malaga",
    "PMI": "Palma de Mallorca",
    "TFS": "Tenerife",
    "HER": "Heraklion",
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
    "FNC": "Madere",
    "FUE": "Fuerteventura",
    "HRG": "Hurghada",
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
    "SSH": "Charm el-Cheikh",
    "SVQ": "Seville",
    "TIV": "Tivat",
    "TLL": "Tallinn",
    "VLC": "Valence",
    "VNO": "Vilnius",
    "ZRH": "Zurich",
    # Long-courrier
    "JFK": "New York",
    "YUL": "Montreal",
    "CUN": "Cancun",
    "PUJ": "Punta Cana",
    "BKK": "Bangkok",
    "NRT": "Tokyo",
    "DXB": "Dubai",
    "MLE": "Male",
    "MRU": "Mauritius",
    "RUN": "Saint-Denis",
    "PPT": "Papeete",
    "GIG": "Rio de Janeiro",
    "GVA": "Geneva",
    "HKG": "Hong Kong",
    "MIA": "Miami",
    "LAX": "Los Angeles",
    "SFO": "San Francisco",
    "EWR": "Newark",
    "SYD": "Sydney",
    "BOG": "Bogota",
    "BOM": "Mumbai",
    "CPT": "Le Cap",
    "DEL": "Delhi",
    "EZE": "Buenos Aires",
    "HND": "Tokyo Haneda",
    "ICN": "Seoul",
    "JNB": "Johannesburg",
    "KUL": "Kuala Lumpur",
    "LIM": "Lima",
    "SCL": "Santiago",
    "SIN": "Singapour",
    "ZNZ": "Zanzibar",
}

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
