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
    return (
        f"✈️ GLOBE GENIUS DEAL ALERT\n\n"
        f"🌍 {package['origin']} → {package['destination']}\n"
        f"📅 Depart : {package['departure_date']} | Retour : {package['return_date']}\n"
        f"🏨 {accommodation['name']} ⭐ {accommodation.get('rating', 'N/A')}/5\n"
        f"💰 Total : {package['total_price']}€  |  🔥 -{package['discount_pct']}% vs marche\n"
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
