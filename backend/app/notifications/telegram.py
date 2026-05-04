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
    trip_type: str | None = None,
    qualification_method: str | None = None,
) -> str:
    """Persist a short opaque token → URL mapping and return the tracking URL.

    `trip_type` and `qualification_method` are optional analytics tags so
    /api/admin/ctr can break clicks down by round_trip vs one_way vs
    split_ticket and by zscore_* vs fallback_discount vs oneway_discount.
    Falls back to UTM-tagged URL on insert failure to never block the alert.
    """
    from app.db import db
    token = f"{dest}-{secrets.token_urlsafe(6)}"
    if db:
        row = {
            "token": token,
            "user_id": user_id,
            "alert_key": alert_key,
            "origin": origin,
            "destination": dest,
            "url": url,
        }
        if trip_type is not None:
            row["trip_type"] = trip_type
        if qualification_method is not None:
            row["qualification_method"] = qualification_method
        try:
            db.table("alert_redirect_tokens").insert(row).execute()
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


def _deal_badge(discount_pct: float, sources: set[str] | None = None) -> str:
    """Return the deal-tier badge shown at the top of an alert.

    `sources` is the set of raw_flights.source values backing the offer.
    When all backing rows come from a single Tier 1 leadprice source
    (`vueling_direct`, `ryanair_direct`), we cap the badge at "Deal rare"
    even past the 60% threshold — those endpoints expose one-way
    leadprices, and their A/R extrapolation is approximate. The
    "Erreur de prix" label is reserved for deals confirmed by at least
    two independent sources (Travelpayouts + at least one direct
    endpoint), or by Travelpayouts alone (which scrapes real A/R).
    """
    leadprice_only_sources = {"vueling_direct", "ryanair_direct"}
    is_leadprice_only = bool(sources) and sources.issubset(leadprice_only_sources)

    if discount_pct >= 60 and not is_leadprice_only:
        return "🔴 Erreur de prix"
    if discount_pct >= 45 or (discount_pct >= 60 and is_leadprice_only):
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


def _city_for_iata(iata: str) -> str:
    """City-only label, no airport-specifier and no IATA code.

    Used by V8.2 multi-origin alerts where we want a single 'Paris' header
    even when the underlying offers come from CDG / ORY / BVA. Strips the
    second word from IATA_TO_CITY entries like 'Paris CDG' / 'Paris Orly'.
    Fallbacks: if the IATA isn't known, returns the code unchanged.
    """
    from app.config import IATA_TO_CITY
    label = IATA_TO_CITY.get(iata)
    if not label:
        return iata
    # 'Paris CDG' → 'Paris'; 'Bordeaux' → 'Bordeaux'; 'Bâle-Mulhouse' → 'Bâle-Mulhouse'.
    # We split on space only, so multi-word city names with hyphens stay intact.
    head = label.split(" ")[0]
    return head


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
        f"🛫 *{origin_label} → {dest_label}*",
        f"🛬 *{dest_label} → {origin_label}*",
        "",
        f"💰 *{price} € A/R · -{disc} %*",
        f"📅 {dep_str} – {ret_str}{duration_str}",
        f"Prix habituel : ~{baseline} €~",
        "✅ Vol vérifié",
    ]
    if url and url != "N/A":
        lines += ["", f"👉 [Voir le deal]({url})"]

    return "\n".join(lines)


def format_oneway_deal_alert(
    flight: dict,
    discount_pct: float,
    baseline_price: float,
    return_estimate: float | None = None,
    user_id: str | None = None,
    alert_key: str | None = None,
    has_guide: bool = False,
) -> str:
    """V5: format an alert for a one-way flight deal (no return leg).

    `flight` must include origin, destination, departure_date, price, source_url,
    direction ('outbound' | 'inbound'). `return_estimate` is the typical price for
    the reverse leg if known — surfaced as a hint to defuse the "is this really
    a deal?" doubt mentioned in V5 design notes."""
    origin = flight["origin"]
    dest = flight["destination"]
    direction = flight.get("direction") or "outbound"

    dep_str = _fmt_date_fr(flight["departure_date"])
    price = int(round(flight["price"]))
    disc = int(round(discount_pct))
    baseline = int(round(baseline_price))
    badge = _deal_badge(discount_pct)
    # V9: defensive fallback — historic one-way rows in DB had source_url
    # null because the scraper didn't build it. Without a source_url the
    # alert ended at "✅ Vol vérifié" with no booking link, leaving the
    # user with no way to act on the deal. Build the Aviasales one-way
    # deep link on the fly when missing so every alert has a link.
    url = flight.get("source_url") or ""
    if not url or url == "N/A":
        try:
            from app.notifications.aviasales import build_aviasales_oneway_url
            url = build_aviasales_oneway_url(
                origin, dest, flight.get("departure_date", ""),
                marker=settings.TRAVELPAYOUTS_MARKER or None,
            )
        except Exception:
            url = ""

    from app.config import iata_label
    origin_label = iata_label(origin)
    dest_label = iata_label(dest)

    # One-way alert: the user's home airport is the origin for outbound,
    # the destination for inbound. Tell them in their own perspective:
    #   outbound → 🛫 départ de Paris (CDG) → Tokyo (NRT)
    #   inbound  → 🛬 retour de Tokyo (NRT) → Paris (CDG)
    if direction == "outbound":
        route_line = f"🛫 *Départ de {origin_label} → {dest_label}*"
        direction_label = "Aller simple"
    else:
        route_line = f"🛬 *Retour de {origin_label} → {dest_label}*"
        direction_label = "Retour simple"

    lines = [
        f"*{badge}*",
        "",
        route_line,
        "",
        f"💰 *{price} € · {direction_label} · -{disc} %*",
        f"📅 {dep_str}",
        f"Prix habituel : ~{baseline} €~",
    ]
    if return_estimate is not None:
        lines.append(f"↩️ Retour estimé : ~{int(round(return_estimate))} €")
    lines.append("✅ Vol vérifié")
    if url and url != "N/A":
        # When called with a user_id + alert_key, route through /r/:token so
        # the click is attributable to the user. Otherwise fall back to UTMs.
        if user_id and alert_key:
            tracked_url = _make_redirect_token(
                user_id, alert_key, origin, dest, url,
                trip_type="one_way",
                qualification_method="oneway_discount",
            )
        else:
            tracked_url = _add_utms(url, origin, dest)
        lines += ["", f"👉 [Voir le deal]({tracked_url})"]

    if has_guide:
        article_iata = dest if direction == "outbound" else origin
        article_label = iata_label(article_iata)
        lines += ["", f"📖 [Le guide complet de {article_label}]({settings.FRONTEND_URL}/destination/{article_iata.lower()})"]

    return "\n".join(lines)


def format_split_ticket_alert(
    outbound: dict,
    inbound: dict,
    roundtrip_baseline: float,
    user_id: str | None = None,
    alert_key: str | None = None,
    has_guide: bool = False,
) -> str:
    """V5: format a 'combo malin' 2x one-way alert when buying two separate
    one-way tickets is cheaper than the round-trip baseline on the same route.

    V9 redesign: aligned visually with format_grouped_flight_alerts so a
    user reading their feed doesn't see "two different products". Same
    badge, same header, same ~price~ strike-through baseline, same ✅
    Vol vérifié footer line, same per-leg "Voir le deal" link styling.
    Carrier names are normalised via normalize_airline_name() so we
    never expose Cyrillic agency strings in the user-facing message.

    Both `outbound` and `inbound` must include origin, destination,
    departure_date, price, source_url, airline.
    """
    from app.config import iata_label
    from app.notifications.airlines import normalize_airline_name

    origin = outbound["origin"]
    dest = outbound["destination"]
    origin_label = iata_label(origin)
    dest_label = iata_label(dest)

    total = int(round(outbound["price"] + inbound["price"]))
    rt_baseline = int(round(roundtrip_baseline))
    savings = max(0, rt_baseline - total)
    saving_pct = int(round((savings / rt_baseline) * 100)) if rt_baseline > 0 else 0

    out_dep = _fmt_date_fr(outbound["departure_date"])
    in_dep = _fmt_date_fr(inbound["departure_date"])

    out_carrier = normalize_airline_name(outbound.get("airline")) or "—"
    in_carrier = normalize_airline_name(inbound.get("airline")) or "—"
    out_price = int(round(outbound["price"]))
    in_price = int(round(inbound["price"]))

    # Reuse the same badge ladder as the round-trip grouped formatter
    # so visual hierarchy is consistent across alert types.
    badge = _deal_badge(saving_pct)

    # V9: same defensive fallback as the one-way alert. A leg with a null
    # source_url falls back to a freshly built Aviasales one-way deep link
    # so the user always lands on a bookable page for each leg.
    from app.notifications.aviasales import build_aviasales_oneway_url
    out_url = outbound.get("source_url") or ""
    if not out_url or out_url == "N/A":
        try:
            out_url = build_aviasales_oneway_url(
                outbound["origin"], outbound["destination"],
                outbound.get("departure_date", ""),
                marker=settings.TRAVELPAYOUTS_MARKER or None,
            )
        except Exception:
            out_url = ""
    in_url = inbound.get("source_url") or ""
    if not in_url or in_url == "N/A":
        try:
            in_url = build_aviasales_oneway_url(
                inbound["origin"], inbound["destination"],
                inbound.get("departure_date", ""),
                marker=settings.TRAVELPAYOUTS_MARKER or None,
            )
        except Exception:
            in_url = ""

    def _wrap(url: str) -> str:
        # Both legs share the same alert_key — a click on either counts
        # as engagement on the combo (per V5+ P1 product decision).
        if user_id and alert_key:
            return _make_redirect_token(
                user_id, alert_key, origin, dest, url,
                trip_type="split_ticket",
                qualification_method="oneway_discount",
            )
        return _add_utms(url, origin, dest)

    lines = [
        f"*{badge} · 💡 Combo malin*",
        "",
        f"🛫 *{origin_label} → {dest_label}*",
        f"🛬 *{dest_label} → {origin_label}*",
        "",
        f"💰 *{total} € total · -{saving_pct} %*",
        f"   Prix habituel A/R : ~{rt_baseline} €~",
        f"   Économie : {savings} €",
        "   ✅ 2 billets vérifiés",
        "",
        # Outbound leg
        f"✈️ *Aller* — {out_carrier} · {out_price} € · {out_dep}",
    ]
    if out_url and out_url != "N/A":
        lines.append(f"   👉 [Voir le deal aller]({_wrap(out_url)})")
    lines.append("")
    # Inbound leg
    lines.append(f"✈️ *Retour* — {in_carrier} · {in_price} € · {in_dep}")
    if in_url and in_url != "N/A":
        lines.append(f"   👉 [Voir le deal retour]({_wrap(in_url)})")

    lines += [
        "",
        "⚠️ Bagages et annulation gérés séparément pour chaque billet.",
    ]
    if has_guide:
        lines += ["", f"📖 [Le guide complet de {dest_label}]({settings.FRONTEND_URL}/destination/{dest.lower()})"]
    return "\n".join(lines)


async def send_oneway_deal_alert(
    chat_id: int,
    flight: dict,
    discount_pct: float,
    baseline_price: float,
    return_estimate: float | None = None,
    user_id: str | None = None,
    alert_key: str | None = None,
    has_guide: bool = False,
) -> bool:
    """V5: send a Telegram alert for a one-way flight deal.

    When user_id+alert_key are provided, the booking link is wrapped in a
    /r/:token redirect for per-user click tracking. Otherwise UTMs only.
    """
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping one-way alert")
        return False
    msg = format_oneway_deal_alert(
        flight, discount_pct, baseline_price, return_estimate,
        user_id=user_id, alert_key=alert_key, has_guide=has_guide,
    )
    try:
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        return True
    except Exception as e:
        logger.error(f"Failed to send one-way alert to {chat_id}: {e}")
        return False


async def send_split_ticket_alert(
    chat_id: int,
    outbound: dict,
    inbound: dict,
    roundtrip_baseline: float,
    user_id: str | None = None,
    alert_key: str | None = None,
    has_guide: bool = False,
) -> bool:
    """V5: send a Telegram alert for a 2x one-way (split-ticket) combo.

    user_id+alert_key enable /r/:token tracking on both legs (clicks on
    either leg count as engagement on the combo, per product decision).
    """
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping split-ticket alert")
        return False
    msg = format_split_ticket_alert(
        outbound, inbound, roundtrip_baseline,
        user_id=user_id, alert_key=alert_key, has_guide=has_guide,
    )
    try:
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        return True
    except Exception as e:
        logger.error(f"Failed to send split-ticket alert to {chat_id}: {e}")
        return False


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
    has_guide: bool = False,
) -> str:
    """Format a grouped Telegram alert for multiple flight offers to one destination.

    REDESIGNED for better information hierarchy:
    - Destination + count at top (scannable)
    - Price isolated and prominent in each offer line
    - Deal qualification tags (EXCELLENT/BON/CLASSIQUE)
    - Single CTA per offer (Voir le deal)
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

    total = len(offers)
    sorted_by_discount = sorted(offers, key=lambda o: o.get("discount_pct", 0), reverse=True)
    shown = sorted_by_discount[:10]
    remaining = total - len(shown)

    max_discount = max(o.get("discount_pct", 0) for o in shown)
    # Pass the underlying sources so leadprice-only Tier 1 deals don't
    # get the "Erreur de prix" label (they're one-way prices doubled,
    # which can diverge from the real A/R Aviasales shows on click).
    sources_in_offer = {o.get("source", "") for o in shown if o.get("source")}
    badge = _deal_badge(max_discount, sources=sources_in_offer)

    from app.config import iata_label

    # V8.2: detect multi-origin alerts (e.g. user tracks CDG + ORY + BVA
    # and the same destination has deals from several Paris airports).
    # When that happens, the header drops the IATA-specific label and
    # uses a city-level one ("Paris" instead of "Paris CDG"), and each
    # offer line gets its own origin-IATA tag.
    origin_iatas_in_offers = {o.get("origin") for o in offers if o.get("origin")}
    multi_origin = len(origin_iatas_in_offers) > 1

    origin_display = origin_iata or (offers[0].get("origin") if offers else "")
    origin_label = iata_label(origin_display) if not multi_origin else _city_for_iata(origin_display)
    dest_label = iata_label(destination_iata)
    noun = "offre disponible" if total == 1 else "offres disponibles"

    header = (
        f"*{badge}*\n"
        f"\n"
        f"🛫 *{origin_label} → {dest_label}*\n"
        f"🛬 *{dest_label} → {origin_label}*\n"
        f"\n"
        f"🗓 {total} {noun}"
    )
    if multi_origin:
        header += f"  · *{len(origin_iatas_in_offers)} aéroports*"

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

            # V8.2: when the alert mixes several origin airports, tag the
            # specific origin on each offer line so the user knows which
            # airport this particular fare flies from.
            origin_tag = ""
            if multi_origin and o.get("origin"):
                origin_tag = f"  ·  via {o['origin']}"

            lines.append(
                f"\n💰 *{price} € A/R · -{disc} %*{origin_tag}\n"
                f"   {dep_str} – {ret_str} · {duration} jours"
                f"{baseline_str}\n"
                f"   ✅ Vol vérifié"
            )

            booking_url = o.get("booking_url", "").strip()
            if booking_url:
                if user_id and alert_key and origin_iata:
                    tracked = _make_redirect_token(
                        user_id, alert_key, origin_iata, destination_iata, booking_url,
                        trip_type="round_trip",
                        qualification_method=o.get("qualification_method"),
                    )
                else:
                    tracked = _add_utms(booking_url, origin_iata or "", destination_iata)
                lines.append(f"   👉 [Voir le deal]({tracked})")

            # Hotel CTA removed: it cluttered alerts and the Booking
            # affiliation revenue was negligible vs the noise it added
            # to the message.

            lines.append("")

    msg_parts = [header] + lines

    if remaining > 0:
        msg_parts.append(f"_+ {remaining} autres dates disponibles_")

    if has_guide:
        msg_parts.append("")
        msg_parts.append(
            f"📖 [Le guide complet de {dest_label}]({settings.FRONTEND_URL}/destination/{destination_iata.lower()})"
        )

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
    has_guide: bool = False,
) -> bool:
    """Send a grouped Telegram alert containing multiple flight offers for one destination."""
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping grouped flight alert")
        return False
    msg = format_grouped_flight_alerts(
        origin_city, dest_city, destination_iata, offers, tier,
        user_id=user_id, alert_key=alert_key, origin_iata=origin_iata,
        has_guide=has_guide,
    )

    # Inline keyboard — quick actions without leaving Telegram:
    #  - "Masquer <destination>": one-tap to hide future alerts for this
    #    specific destination (most-asked feature: users skim notifs and
    #    want to dismiss the city they're not interested in).
    #  - "Pause": opens a sub-menu (7d / 30d / indefinite) on click; the
    #    callback handler swaps in the duration buttons.
    # 'Se désabonner' is intentionally absent — full opt-out is too easy
    # to fat-finger; users can disconnect from /profile if they really
    # want out.
    reply_markup = None
    if user_id:
        # Truncate the destination label to keep the button text short on
        # narrow screens (Telegram clips long button labels mid-word).
        short_dest = (dest_city or destination_iata)[:18]
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"🚫 Masquer {short_dest}",
                callback_data=f"block:{user_id}:{destination_iata}",
            )],
            [InlineKeyboardButton("⏸ Pause les alertes", callback_data=f"pause_menu:{user_id}")],
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
