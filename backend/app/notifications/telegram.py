import logging
from datetime import datetime
from telegram import Bot
from app.config import settings

logger = logging.getLogger(__name__)

_FR_MONTHS_SHORT = ["", "janv", "févr", "mars", "avr", "mai", "juin",
                    "juil", "août", "sept", "oct", "nov", "déc"]

_FR_MONTHS_LONG = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                   "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def _get_bot() -> Bot | None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)


def format_deal_alert(package: dict, flight: dict, accommodation: dict) -> str:
    from app.config import IATA_TO_CITY
    origin_city = IATA_TO_CITY.get(package["origin"], package["origin"])
    dest_city = IATA_TO_CITY.get(package["destination"], package["destination"])

    # Alert level badge
    alert_level = package.get("ai_alert_level", "good_deal")
    if alert_level == "fare_mistake":
        alert_badge = "🔴 ERREUR DE PRIX"
    elif alert_level == "flash_promo":
        alert_badge = "🟠 PROMO FLASH"
    else:
        alert_badge = "🟡 BON DEAL"

    # Check if AI-enriched
    ai_desc = package.get("ai_description")
    ai_reason = package.get("ai_reason")
    ai_tip = package.get("ai_tip")
    ai_tags = package.get("ai_tags")

    if ai_desc:
        # Enriched format
        tags_str = " ".join(ai_tags) if ai_tags else ""
        return (
            f"✈️ GLOBE GENIUS — {alert_badge}\n\n"
            f"🌍 {origin_city} → {dest_city}\n"
            f"📅 {package['departure_date']} – {package['return_date']}\n\n"
            f"{ai_desc}\n\n"
            f"💰 {package['total_price']}€ au lieu de {package['baseline_total']}€ · -{package['discount_pct']}%\n"
            f"📊 {ai_reason}\n\n"
            f"💡 {ai_tip}\n\n"
            f"🎯 Score : {package['score']}/100\n"
            f"{tags_str}\n\n"
            f"👉 Vol : {flight.get('source_url', 'N/A')}\n"
            f"👉 Hotel : {accommodation.get('source_url', 'N/A')}"
        )
    else:
        # Basic format (fallback)
        return (
            f"✈️ GLOBE GENIUS — {alert_badge}\n\n"
            f"🌍 {origin_city} → {dest_city}\n"
            f"📅 {package['departure_date']} – {package['return_date']}\n"
            f"🏨 {accommodation['name']} ⭐ {accommodation.get('rating', 'N/A')}/5\n"
            f"💰 {package['total_price']}€  |  🔥 -{package['discount_pct']}% vs marche\n"
            f"🎯 Score : {package['score']}/100\n\n"
            f"👉 Vol : {flight.get('source_url', 'N/A')}\n"
            f"👉 Hotel : {accommodation.get('source_url', 'N/A')}"
        )


def format_digest(packages: list[dict]) -> str:
    today = datetime.now().strftime("%d/%m/%Y")
    lines = [f"📬 GLOBE GENIUS DIGEST — {today}\n"]
    lines.append(f"Top {len(packages)} deals du jour :\n")
    for i, pkg in enumerate(packages, 1):
        lines.append(
            f"{i}. {pkg['origin']} → {pkg['destination']} | "
            f"{pkg['total_price']}€ (-{pkg['discount_pct']}%) | "
            f"Score {pkg['score']}/100 | "
            f"{pkg['departure_date']} → {pkg['return_date']}"
        )
    return "\n".join(lines)


def format_admin_report(stats: dict) -> str:
    today = datetime.now().strftime("%d/%m/%Y")
    lines = [
        f"📊 GLOBE GENIUS — Rapport {today}\n",
        f"Scrapes : {stats['flight_scrapes']} vols ✅ | {stats['accommodation_scrapes']} hebergements ✅",
        f"Donnees : {stats['total_flights']} vols | {stats['total_accommodations']} hebergements",
        f"Erreurs : {stats['errors']}",
        f"Packages qualifies : {stats['packages_qualified']} (taux : {stats['qualification_rate']}%)",
        f"Alertes envoyees : {stats['alerts_sent']}",
        f"Baselines actives : {stats['active_baselines']} routes",
    ]

    warnings = []
    if stats["qualification_rate"] < 5:
        warnings.append("⚠️ Taux qualification < 5% — surveiller les baselines")
    if stats["errors"] > 0:
        warnings.append(f"⚠️ {stats['errors']} erreurs detectees")

    if warnings:
        lines.append("")
        lines.extend(warnings)

    return "\n".join(lines)


def format_flight_deal_alert(flight: dict, discount_pct: float, baseline_price: float) -> str:
    """Format an alert message for a flight-only deal (no hotel package).

    `flight` is expected to contain: origin, destination, departure_date,
    return_date, price, airline, source_url, trip_duration_days (optional)."""
    from app.config import IATA_TO_CITY
    origin_city = IATA_TO_CITY.get(flight["origin"], flight["origin"])
    dest_city = IATA_TO_CITY.get(flight["destination"], flight["destination"])

    if discount_pct >= 60:
        alert_badge = "🔴 ERREUR DE PRIX"
    elif discount_pct >= 40:
        alert_badge = "🟠 PROMO FLASH"
    else:
        alert_badge = "🟡 BON DEAL"

    duration = flight.get("trip_duration_days")
    duration_line = f"🗓 {duration} jours sur place\n" if duration else ""

    return (
        f"{alert_badge}\n\n"
        f"🌍 {origin_city} → {dest_city}\n"
        f"📅 {flight['departure_date']} – {flight['return_date']}\n"
        f"{duration_line}"
        f"✈️ {flight.get('airline', 'Compagnie')}\n\n"
        f"💰 {flight['price']}€ au lieu de ~{round(baseline_price)}€  ·  🔥 -{round(discount_pct)}%\n\n"
        f"👉 Réservation : {flight.get('source_url', 'N/A')}"
    )


async def send_flight_deal_alert(
    chat_id: int,
    flight: dict,
    discount_pct: float,
    baseline_price: float,
    tier: str = "premium",
) -> bool:
    """Send a Telegram alert for a flight-only deal."""
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping flight alert")
        return False
    msg = format_flight_deal_alert(flight, discount_pct, baseline_price)
    if tier == "free":
        msg += (
            "\n\n💎 Réservation directe réservée aux abonnés premium. "
            "Créez un compte premium pour débloquer les meilleurs deals."
        )
    try:
        await bot.send_message(chat_id=chat_id, text=msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send flight alert to {chat_id}: {e}")
        return False


def format_grouped_flight_alerts(
    origin_city: str,
    dest_city: str,
    destination_iata: str,
    offers: list[dict],
    tier: str = "premium",
) -> str:
    """Format a grouped Telegram alert for multiple flight offers to one destination.

    offers: list of dicts with keys:
      - departure_date (YYYY-MM-DD, required)
      - return_date (YYYY-MM-DD, required)
      - price (required)
      - discount_pct (required)
      - score (optional, default 0)
      - airline (optional, default empty string)
      - booking_url (optional, default empty string → no 👉 line)
    """
    from app.config import settings
    from app.notifications.booking import build_booking_url

    total = len(offers)
    sorted_by_discount = sorted(offers, key=lambda o: o.get("discount_pct", 0), reverse=True)
    shown = sorted_by_discount[:10]
    remaining = total - len(shown)

    max_discount = max(o.get("discount_pct", 0) for o in shown)
    if max_discount >= 60:
        badge = "🔴"
    elif max_discount >= 30:
        badge = "🟠"
    else:
        badge = "🟡"

    noun = "offre" if total == 1 else "offres"
    header = f"{badge} {dest_city.upper()} — {total} {noun} à saisir"
    route = f"✈️ {origin_city} → {dest_city}"

    # Group by (year, month) chronologically
    by_month: dict[tuple[int, int], list[dict]] = {}
    for o in shown:
        d = datetime.strptime(o["departure_date"], "%Y-%m-%d")
        key = (d.year, d.month)
        by_month.setdefault(key, []).append(o)

    lines: list[str] = []
    for (year, month) in sorted(by_month.keys()):
        month_offers = sorted(by_month[(year, month)], key=lambda o: o.get("price", 0))
        lines.append("")
        lines.append(f"📅 {_FR_MONTHS_LONG[month]} {year} ({len(month_offers)})")
        for o in month_offers:
            dep = datetime.strptime(o["departure_date"], "%Y-%m-%d")
            ret = datetime.strptime(o["return_date"], "%Y-%m-%d")
            duration = (ret - dep).days
            dep_str = f"{dep.day:02d} {_FR_MONTHS_SHORT[dep.month]}"
            ret_str = f"{ret.day:02d} {_FR_MONTHS_SHORT[ret.month]}"
            price = int(round(o["price"]))
            disc = int(round(o.get("discount_pct", 0)))
            airline = o.get("airline", "").strip()
            airline_suffix = f" · {airline}" if airline else ""

            # Color code by discount level
            if disc >= 60:
                color_badge = "🔴"
            elif disc >= 40:
                color_badge = "🟠"
            elif disc >= 20:
                color_badge = "🟡"
            else:
                color_badge = "⚪"

            lines.append(f"{color_badge} {dep_str} - {ret_str} · {duration}j · {price}€ (-{disc}%){airline_suffix}")
            booking_url = o.get("booking_url", "").strip()
            if booking_url:
                lines.append(f"👉 [Consulter le deal]({booking_url})")
            if disc >= 50:
                hotel_url = build_booking_url(
                    dest_city,
                    o["departure_date"],
                    o["return_date"],
                    marker=settings.TRAVELPAYOUTS_MARKER or None,
                )
                lines.append(f"🏨 Hôtels {dest_city} : {hotel_url}")

    msg_parts = [header, "", route] + lines
    if remaining > 0:
        msg_parts.append("")
        msg_parts.append(f"+ {remaining} autres")

    link = f"👉 Toutes les offres : {settings.FRONTEND_URL}/home?dest={destination_iata}"
    msg_parts += ["", link]

    msg = "\n".join(msg_parts)

    if tier == "free":
        msg += (
            "\n\n💎 Réservation directe réservée aux abonnés premium. "
            "Créez un compte premium pour débloquer les meilleurs deals."
        )
    return msg


async def send_grouped_flight_alerts(
    chat_id: int,
    origin_city: str,
    dest_city: str,
    destination_iata: str,
    offers: list[dict],
    tier: str = "premium",
) -> bool:
    """Send a grouped Telegram alert containing multiple flight offers for one destination."""
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping grouped flight alert")
        return False
    msg = format_grouped_flight_alerts(origin_city, dest_city, destination_iata, offers, tier)
    try:
        await bot.send_message(chat_id=chat_id, text=msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send grouped flight alert to {chat_id}: {e}")
        return False


async def send_deal_alert(chat_id: int, package: dict, flight: dict, accommodation: dict, tier: str = "premium") -> bool:
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping alert")
        return False
    msg = format_deal_alert(package, flight, accommodation)
    if tier == "free":
        msg += (
            "\n\n💎 Réservation réservée aux abonnés premium. "
            "Créez un compte premium pour débloquer ce deal."
        )
    try:
        await bot.send_message(chat_id=chat_id, text=msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram alert to {chat_id}: {e}")
        return False


async def send_digest(chat_id: int, packages: list[dict]) -> bool:
    bot = _get_bot()
    if not bot:
        return False
    msg = format_digest(packages)
    try:
        await bot.send_message(chat_id=chat_id, text=msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send digest to {chat_id}: {e}")
        return False


async def send_admin_report(stats: dict) -> bool:
    bot = _get_bot()
    if not bot or not settings.TELEGRAM_ADMIN_CHAT_ID:
        return False
    msg = format_admin_report(stats)
    try:
        await bot.send_message(chat_id=int(settings.TELEGRAM_ADMIN_CHAT_ID), text=msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send admin report: {e}")
        return False


async def send_admin_alert(message: str) -> bool:
    bot = _get_bot()
    if not bot or not settings.TELEGRAM_ADMIN_CHAT_ID:
        return False
    try:
        await bot.send_message(chat_id=int(settings.TELEGRAM_ADMIN_CHAT_ID), text=f"🚨 {message}")
        return True
    except Exception as e:
        logger.error(f"Failed to send admin alert: {e}")
        return False
