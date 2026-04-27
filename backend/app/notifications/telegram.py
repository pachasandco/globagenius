import logging
import secrets
from datetime import datetime
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from app.config import settings

logger = logging.getLogger(__name__)

_FR_MONTHS_SHORT = ["", "janv", "févr", "mars", "avr", "mai", "juin",
                    "juil", "août", "sept", "oct", "nov", "déc"]

_FR_MONTHS_LONG = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                   "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def _add_utms(url: str, origin: str, dest: str) -> str:
    """Append UTM parameters to a URL without clobbering existing query params."""
    if not url or url == "N/A":
        return url
    parsed = urlparse(url)
    existing = parse_qs(parsed.query, keep_blank_values=True)
    existing.update({
        "utm_source": ["telegram"],
        "utm_medium": ["alert"],
        "utm_campaign": ["deal"],
        "utm_content": [f"{origin}-{dest}"],
    })
    new_query = urlencode({k: v[0] for k, v in existing.items()})
    return urlunparse(parsed._replace(query=new_query))


def _make_redirect_token(
    user_id: str | None,
    alert_key: str,
    origin: str,
    dest: str,
    url: str,
) -> str:
    """Persist a short opaque token → URL mapping and return the tracking URL."""
    from app.db import db
    token = f"{dest}-{secrets.token_urlsafe(6)}"
    if db:
        try:
            db.table("alert_redirect_tokens").insert({
                "token": token,
                "user_id": user_id,
                "alert_key": alert_key,
                "origin": origin,
                "destination": dest,
                "url": url,
            }).execute()
        except Exception:
            return _add_utms(url, origin, dest)
    return f"{settings.FRONTEND_URL}/r/{token}"


def _get_bot() -> Bot | None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)


def format_deal_alert(package: dict, flight: dict, accommodation: dict) -> str:
    from app.config import iata_label
    origin_city = iata_label(package["origin"])
    dest_city = iata_label(package["destination"])

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


def _deal_badge(discount_pct: float) -> str:
    if discount_pct >= 60:
        return "🔴 Erreur de prix"
    if discount_pct >= 45:
        return "🟠 Deal rare"
    if discount_pct >= 30:
        return "🟡 Promo flash"
    return "🟢 Bon deal"


def _fmt_date_fr(date_str: str) -> str:
    """'2025-05-29' → '29 mai'"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{d.day} {_FR_MONTHS_SHORT[d.month]}"
    except Exception:
        return date_str


def format_flight_deal_alert(flight: dict, discount_pct: float, baseline_price: float) -> str:
    """Format an alert message for a flight-only deal (no hotel package)."""
    origin = flight["origin"]
    dest = flight["destination"]

    dep_str = _fmt_date_fr(flight["departure_date"])
    ret_str = _fmt_date_fr(flight["return_date"])
    try:
        dep_dt = datetime.strptime(flight["departure_date"], "%Y-%m-%d")
        ret_dt = datetime.strptime(flight["return_date"], "%Y-%m-%d")
        duration = (ret_dt - dep_dt).days
    except Exception:
        duration = flight.get("trip_duration_days")
    duration_str = f" · {duration} jours" if duration else ""

    price = int(round(flight["price"]))
    disc = int(round(discount_pct))
    baseline = int(round(baseline_price))
    badge = _deal_badge(discount_pct)
    url = flight.get("source_url", "")

    from app.config import iata_label
    origin_label = iata_label(origin)
    dest_label = iata_label(dest)

    lines = [
        f"*{badge}*",
        "",
        f"✈️ *{origin_label} ({origin}) → {dest_label} ({dest})*",
        f"💰 *{price} € A/R · -{disc} %*",
        f"📅 {dep_str} – {ret_str}{duration_str}",
        f"Prix habituel : ~{baseline} €~",
        "✅ Vol vérifié",
    ]
    if url and url != "N/A":
        lines += ["", f"👉 [Voir le deal]({url})"]

    return "\n".join(lines)


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
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
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
    user_id: str | None = None,
    alert_key: str | None = None,
    origin_iata: str | None = None,
) -> str:
    """Format a grouped Telegram alert for multiple flight offers to one destination.

    REDESIGNED for better information hierarchy:
    - Destination + count at top (scannable)
    - Price isolated and prominent in each offer line
    - Deal qualification tags (EXCELLENT/BON/CLASSIQUE)
    - Simplified CTAs (Voir le vol, Voir les hôtels)
    - Urgency signals (scarcity, frequency)

    offers: list of dicts with keys:
      - departure_date (YYYY-MM-DD, required)
      - return_date (YYYY-MM-DD, required)
      - price (required)
      - discount_pct (required)
      - score (optional, default 0)
      - airline (optional, default empty string)
      - booking_url (optional, default empty string → no CTA line)
    """
    from app.config import settings
    from app.notifications.booking import build_booking_url

    total = len(offers)
    sorted_by_discount = sorted(offers, key=lambda o: o.get("discount_pct", 0), reverse=True)
    shown = sorted_by_discount[:10]
    remaining = total - len(shown)

    max_discount = max(o.get("discount_pct", 0) for o in shown)
    badge = _deal_badge(max_discount)

    from app.config import iata_label
    origin_display = origin_iata or (offers[0].get("origin") if offers else "")
    origin_label = iata_label(origin_display)
    dest_label = iata_label(destination_iata)
    noun = "offre" if total == 1 else "offres"

    header = (
        f"*{badge}*\n"
        f"\n"
        f"✈️ *{origin_label} ({origin_display}) → {dest_label} ({destination_iata})*\n"
        f"🗓 {total} {noun} disponibles"
    )

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
        lines.append(f"📅 *{_FR_MONTHS_LONG[month]} {year}*")

        for o in month_offers:
            dep = datetime.strptime(o["departure_date"], "%Y-%m-%d")
            ret = datetime.strptime(o["return_date"], "%Y-%m-%d")
            duration = (ret - dep).days
            dep_str = f"{dep.day} {_FR_MONTHS_SHORT[dep.month]}"
            ret_str = f"{ret.day} {_FR_MONTHS_SHORT[ret.month]}"
            price = int(round(o["price"]))
            disc = int(round(o.get("discount_pct", 0)))

            baseline = o.get("baseline_price")
            baseline_str = f"\n   Prix habituel : ~{int(round(baseline))} €~" if baseline and baseline > price else ""

            lines.append(
                f"\n💰 *{price} € A/R · -{disc} %*\n"
                f"   {dep_str} – {ret_str} · {duration} jours"
                f"{baseline_str}\n"
                f"   ✅ Vol vérifié"
            )

            booking_url = o.get("booking_url", "").strip()
            if booking_url:
                if user_id and alert_key and origin_iata:
                    tracked = _make_redirect_token(
                        user_id, alert_key, origin_iata, destination_iata, booking_url
                    )
                else:
                    tracked = _add_utms(booking_url, origin_iata or "", destination_iata)
                lines.append(f"   👉 [Voir le deal]({tracked})")

            # Hotel CTA for high-value deals
            if disc >= 40:
                hotel_url = build_booking_url(
                    dest_city,
                    o["departure_date"],
                    o["return_date"],
                    marker=settings.TRAVELPAYOUTS_MARKER or None,
                )
                hotel_tracked = _add_utms(hotel_url, origin_iata or "", destination_iata)
                lines.append(f"   🏨 [Voir les hôtels]({hotel_tracked})")

            lines.append("")

    msg_parts = [header] + lines

    if remaining > 0:
        msg_parts.append(f"_+ {remaining} autres dates disponibles_")

    msg_parts.append("")
    msg_parts.append(f"👉 [Toutes les offres {destination_iata}]({settings.FRONTEND_URL}/home?dest={destination_iata})")

    msg = "\n".join(msg_parts)

    if tier == "free":
        msg += (
            "\n\n💎 Réservation directe réservée aux abonnés premium. "
            "Passez à la version premium pour débloquer les meilleurs deals."
        )
    return msg


async def send_grouped_flight_alerts(
    chat_id: int,
    origin_city: str,
    dest_city: str,
    destination_iata: str,
    offers: list[dict],
    tier: str = "premium",
    user_id: str | None = None,
    alert_key: str | None = None,
    origin_iata: str | None = None,
) -> bool:
    """Send a grouped Telegram alert containing multiple flight offers for one destination."""
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping grouped flight alert")
        return False
    msg = format_grouped_flight_alerts(
        origin_city, dest_city, destination_iata, offers, tier,
        user_id=user_id, alert_key=alert_key, origin_iata=origin_iata,
    )

    # Inline keyboard — quick actions without leaving Telegram
    reply_markup = None
    if user_id:
        reply_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏸ Pause", callback_data=f"pause:{user_id}"),
                InlineKeyboardButton("🔕 Se désabonner", callback_data=f"unsub:{user_id}"),
            ]
        ])

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
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
