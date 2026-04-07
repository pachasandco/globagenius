import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ADMIN_CHAT_ID: str = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    SCRAPE_FLIGHTS_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_FLIGHTS_INTERVAL_HOURS", "2"))
    SCRAPE_ACCOMMODATIONS_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_ACCOMMODATIONS_INTERVAL_HOURS", "4"))
    BASELINE_RECALC_HOUR: int = int(os.getenv("BASELINE_RECALC_HOUR", "3"))
    DIGEST_HOUR: int = int(os.getenv("DIGEST_HOUR", "8"))
    MIN_DISCOUNT_PCT: int = int(os.getenv("MIN_DISCOUNT_PCT", "40"))
    MIN_SCORE_ALERT: int = int(os.getenv("MIN_SCORE_ALERT", "70"))
    MIN_SCORE_DIGEST: int = int(os.getenv("MIN_SCORE_DIGEST", "50"))
    DATA_FRESHNESS_HOURS: int = int(os.getenv("DATA_FRESHNESS_HOURS", "2"))
    MVP_AIRPORTS: list = field(default_factory=lambda: os.getenv(
        "MVP_AIRPORTS", "CDG,ORY,LYS,MRS,NCE,BOD,NTE,TLS"
    ).split(","))


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
}

DESTINATION_POPULARITY = {
    "BCN": 95, "LIS": 90, "FCO": 88, "ATH": 85, "AMS": 87,
    "MAD": 86, "IST": 82, "PRG": 80, "BUD": 78, "RAK": 83,
    "NAP": 75, "OPO": 72, "MXP": 77, "VCE": 74, "DUB": 70,
    "BER": 76, "VIE": 73, "CPH": 68, "EDI": 65, "HEL": 60,
    "OSL": 58, "ARN": 62, "WAW": 55, "ZAG": 50, "TUN": 52,
    "CMN": 56, "CAI": 64, "TLV": 66, "AGP": 79, "PMI": 81,
    "TFS": 77, "HER": 71, "SPU": 69, "DBV": 73,
    # Long-courrier
    "JFK": 92, "YUL": 70, "CUN": 78, "PUJ": 76, "BKK": 88,
    "NRT": 85, "DXB": 90, "MLE": 82, "MRU": 80, "RUN": 72,
    "PPT": 65, "GIG": 74,
}

settings = Settings()
