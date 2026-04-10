import logging
from datetime import datetime
from telegram import Bot
from app.config import settings

logger = logging.getLogger(__name__)


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


async def send_deal_alert(chat_id: int, package: dict, flight: dict, accommodation: dict) -> bool:
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping alert")
        return False
    msg = format_deal_alert(package, flight, accommodation)
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
