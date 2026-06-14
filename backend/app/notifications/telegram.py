import logging
import secrets
from datetime import datetime
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TimedOut
from app.config import settings

logger = logging.getLogger(__name__)

_FR_MONTHS_SHORT = ["", "janv", "févr", "mars", "avr", "mai", "juin",
                    "juil", "août", "sept", "oct", "nov", "déc"]

_FR_MONTHS_LONG = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                   "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def _apply_aviasales_locale(url: str) -> str:
    """Force EUR + French locale on Aviasales links.

    Aviasales defaults to USD + English on www.aviasales.com when the
    visitor has no prior session cookie — so French users landing from
    a Telegram click saw their fare in dollars. Append `currency=eur`
    and `locale=fr` (the documented Travelpayouts query params) so the
    booking page renders in the right currency and language regardless
    of geo / cookie state. Non-Aviasales URLs pass through unchanged.
    """
    if not url or url == "N/A":
        return url
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if "aviasales" not in host:
        return url
    existing = parse_qs(parsed.query, keep_blank_values=True)
    # Don't clobber an explicit value already set upstream.
    existing.setdefault("currency", ["eur"])
    existing.setdefault("locale", ["fr"])
    new_query = urlencode({k: v[0] for k, v in existing.items()})
    return urlunparse(parsed._replace(query=new_query))


def _add_utms(url: str, origin: str, dest: str) -> str:
    """Append UTM parameters to a URL without clobbering existing query params.
    Also forces EUR + French locale on Aviasales links so prices never
    render in dollars."""
    if not url or url == "N/A":
        return url
    url = _apply_aviasales_locale(url)
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
    # Bake the EUR + locale params into the stored URL so the 302 from
    # /r/{token} lands the user on the right-currency booking page
    # without an extra hop.
    url = _apply_aviasales_locale(url)
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
    """Vol + hôtel package alert.

    Harmonised 2026-06-10 with the other deal templates: same badge
    ladder (_deal_badge), Markdown bold price + "-XX %" always present,
    strike-through baseline, FR dates, per-item CTA links. The internal
    score and the "GLOBE GENIUS" banner are gone — no other alert type
    exposes them. AI-enriched fields (description / reason / tip) keep
    their slots when present.
    """
    from app.config import iata_label
    origin_label = iata_label(package["origin"])
    dest_label = iata_label(package["destination"])

    disc = int(round(package.get("discount_pct") or 0))
    total = int(round(package.get("total_price") or 0))
    badge = _deal_badge(disc)
    dep_str = _fmt_date_fr(str(package.get("departure_date") or "")[:10])
    ret_str = _fmt_date_fr(str(package.get("return_date") or "")[:10])

    lines = [
        f"*{badge} · 🏝 Vol + hôtel*",
        "",
        f"🛫 *{origin_label} → {dest_label}*",
        "",
        f"💰 *{total} € · -{disc} %*",
        f"📅 {dep_str} – {ret_str}",
    ]
    baseline_total = package.get("baseline_total")
    if baseline_total:
        lines.append(f"   Prix habituel : ~{int(round(baseline_total))} €~")

    ai_desc = package.get("ai_description")
    if ai_desc:
        lines += ["", ai_desc]
    ai_reason = package.get("ai_reason")
    if ai_reason:
        lines.append(f"📊 {ai_reason}")
    ai_tip = package.get("ai_tip")
    if ai_tip:
        lines += ["", f"💡 {ai_tip}"]

    lines += [
        "",
        f"🏨 {accommodation['name']} ⭐ {accommodation.get('rating', 'N/A')}/5",
    ]
    flight_url = flight.get("source_url") or ""
    if flight_url and flight_url != "N/A":
        lines.append(f"👉 [Voir le vol]({flight_url})")
    hotel_url = accommodation.get("source_url") or ""
    if hotel_url and hotel_url != "N/A":
        lines.append(f"👉 [Voir l'hôtel]({hotel_url})")

    return "\n".join(lines)


# Per-deal-subtype prefix for the digest lines — mirrors the headers of
# the dedicated alert templates so the digest reads as a summary of the
# same products, not a different one.
_DIGEST_SUBTYPE_PREFIX = {
    "roundtrip": "🛫",
    "oneway_exceptional": "➡️ Aller simple ·",
    "split_ticket": "💡 Combo malin ·",
    "stopover": "🧳 Stopover ·",
}


def format_digest(packages: list[dict]) -> str:
    """Daily digest — top deals of the day, all subtypes mixed.

    Harmonised 2026-06-10 with the alert templates: Markdown, city
    labels via iata_label, FR dates, always a discount %, no internal
    score. Each entry needs: origin, destination, price (or legacy
    total_price), discount_pct, departure_date; optional: return_date,
    deal_subtype, metadata (stopover entries carry hub /
    final_destination there).
    """
    from app.config import iata_label

    today = datetime.now().strftime("%d/%m/%Y")
    lines = [f"📬 *Le digest GlobeGenius — {today}*", ""]
    for i, pkg in enumerate(packages, 1):
        subtype = pkg.get("deal_subtype") or "roundtrip"
        prefix = _DIGEST_SUBTYPE_PREFIX.get(subtype, "🛫")
        price = int(round(pkg.get("price") or pkg.get("total_price") or 0))
        disc = int(round(pkg.get("discount_pct") or 0))

        origin_label = iata_label(pkg.get("origin") or "")
        dest_label = iata_label(pkg.get("destination") or "")
        # Stopover chains show the full 2-destination routing — the hub
        # is the selling point, not an implementation detail.
        metadata = pkg.get("metadata") or {}
        if subtype == "stopover" and metadata.get("hub"):
            hub_label = iata_label(metadata["hub"])
            final_label = iata_label(metadata.get("final_destination") or "")
            route = f"{origin_label} → {hub_label} → {final_label or dest_label}"
        else:
            route = f"{origin_label} → {dest_label}"

        dep = _fmt_date_fr((pkg.get("departure_date") or "")[:10])
        ret = _fmt_date_fr((pkg.get("return_date") or "")[:10]) if pkg.get("return_date") else ""
        dates = f"{dep} – {ret}" if ret else dep

        lines.append(f"{i}. {prefix} *{route}*")
        lines.append(f"   💰 *{price} € · -{disc} %* · 📅 {dates}")
    lines += ["", f"👉 [Toutes les offres]({settings.FRONTEND_URL}/home)"]
    return "\n".join(lines)


def format_admin_report(stats: dict) -> str:
    today = datetime.now().strftime("%d/%m/%Y")

    def _breakdown(d: dict) -> str:
        if not d:
            return ""
        # e.g. "280 A/R · 23 split · 10 OW"
        label = {"flight": "A/R", "round_trip": "A/R", "one_way": "OW",
                 "split_ticket": "split", "stopover": "stopover"}
        parts = [f"{n} {label.get(k, k)}" for k, n in sorted(d.items(), key=lambda x: -x[1])]
        return " · ".join(parts)

    qi_bd = _breakdown(stats.get("qualified_by_type", {}))
    sa_bd = _breakdown(stats.get("alerts_by_type", {}))
    lines = [
        f"📊 GLOBE GENIUS — Rapport {today}\n",
        f"Scrapes : {stats['flight_scrapes']} runs · {stats['total_flights']} vols collectés",
        f"Erreurs : {stats['errors']}",
        f"Deals qualifiés : {stats.get('qualified', 0)}" + (f"  ({qi_bd})" if qi_bd else ""),
        f"Alertes envoyées : {stats['alerts_sent']}" + (f"  ({sa_bd})" if sa_bd else ""),
        f"Users touchés : {stats.get('users_reached', 0)}",
        f"Baselines actives : {stats['active_baselines']} routes",
    ]

    warnings = []
    # Real red flag: scraping ran but nothing reached users.
    if stats["flight_scrapes"] > 0 and stats["alerts_sent"] == 0:
        warnings.append("🚨 0 alerte envoyée alors que le scraping tourne — dispatch à vérifier")
    if stats["errors"] > 30:
        warnings.append(f"⚠️ {stats['errors']} erreurs (au-delà du bruit de queue habituel)")

    if warnings:
        lines.append("")
        lines.extend(warnings)

    return "\n".join(lines)


_YOUNG_BASELINE_SAMPLE_THRESHOLD = 15


def _deal_badge(
    discount_pct: float,
    sources: set[str] | None = None,
    min_sample_count: int | None = None,
) -> str:
    """Return the deal-tier badge shown at the top of an alert.

    `sources` is the set of raw_flights.source values backing the offer.
    When all backing rows come from a single Tier 1 leadprice source
    (`vueling_direct`, `ryanair_direct`), we cap the badge at "Deal rare"
    even past the 60% threshold — those endpoints expose one-way
    leadprices, and their A/R extrapolation is approximate. The
    "Erreur de prix" label is reserved for deals confirmed by at least
    two independent sources (Travelpayouts + at least one direct
    endpoint), or by Travelpayouts alone (which scrapes real A/R).

    `min_sample_count`: smallest baseline.sample_count across the
    offers backing the alert. When the baseline corpus is young
    (< _YOUNG_BASELINE_SAMPLE_THRESHOLD observations), a -65% discount
    can be a statistical artefact rather than a true bargain. We cap
    the badge at "Promo flash" in that regime so the alert doesn't
    promise more than the data can support. Once the baseline matures
    (more historical scrapes accumulate), this branch stops firing
    automatically.
    """
    leadprice_only_sources = {"vueling_direct", "ryanair_direct"}
    is_leadprice_only = bool(sources) and sources.issubset(leadprice_only_sources)
    # Young-baseline cap fires only when we have positive evidence that the
    # baseline is small — i.e. min_sample_count is set AND > 0 AND below
    # the threshold. A value of None / 0 means "unknown" (no data plumbed
    # through) and we keep the original badge ladder. This avoids
    # accidentally degrading every alert in scenarios where the offer dict
    # didn't carry the sample_count metadata.
    is_young_baseline = (
        min_sample_count is not None
        and 0 < min_sample_count < _YOUNG_BASELINE_SAMPLE_THRESHOLD
    )

    if is_young_baseline and discount_pct >= 30:
        # Young baselines: keep the wording credible regardless of the
        # raw discount. A -67% claim with 6 observations isn't honest;
        # "Promo flash" sells the deal without staking credibility on a
        # specific savings figure.
        return "🟡 Promo flash"

    if discount_pct >= 60 and not is_leadprice_only:
        return "🔴 Erreur de prix"
    if discount_pct >= 45 or (discount_pct >= 60 and is_leadprice_only):
        return "🟠 Deal rare"
    if discount_pct >= 30:
        return "🟡 Promo flash"
    return "🟢 Bon deal"


def _price_verification_line(
    price_confidences: set[str], any_young_baseline: bool
) -> str:
    """Build the price-confidence line shown under each offer.

    Replaces the previous blanket "✅ Vol vérifié" with a copy that
    matches the actual evidence. Three regimes:

    - Two sources agreed (Tier 1 direct + Travelpayouts cross-check, or
      pure Travelpayouts) → "✅ Prix Aviasales confirmé". This is what
      the user will actually see when they click; we can stand behind
      it.
    - Single-source confirmation (direct endpoint only, TP had no data
      for these dates) OR young baseline (low historical confidence in
      the baseline used to compute the discount) → "🔍 Prix indicatif
      — peut varier sur Aviasales". Honest hedge: the alert is still
      useful, but we don't promise a number we can't guarantee.
    - No confidence flag at all (legacy callers / tests) → fall back to
      the previous "✅ Vol vérifié" copy so existing call sites keep
      working unchanged.
    """
    if not price_confidences:
        return "✅ Vol vérifié"
    if "single_source" in price_confidences or any_young_baseline:
        return "🔍 Prix indicatif — peut varier sur Aviasales"
    return "✅ Prix Aviasales confirmé"


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

    # 2026-05-21: surface the operating carrier on one-way alerts too,
    # with a 🎒 link to its baggage policy. Hidden when the source name
    # is actually an OTA / meta-search agency rather than the airline.
    from app.notifications.airlines import (
        normalize_airline_name as _norm_air,
        is_agency as _is_agency,
        baggage_url as _baggage_url,
    )
    carrier = _norm_air(flight.get("airline"))
    carrier_line: str | None = None
    if carrier and not _is_agency(carrier):
        bag = _baggage_url(carrier)
        carrier_line = (
            f"✈️ {carrier} · [🎒]({bag})" if bag else f"✈️ {carrier}"
        )

    lines = [
        f"*{badge}*",
        "",
        route_line,
        "",
        f"💰 *{price} € · {direction_label} · -{disc} %*",
        f"📅 {dep_str}",
    ]
    if carrier_line:
        lines.append(carrier_line)
    lines.append(f"Prix habituel : ~{baseline} €~")
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
    from app.notifications.airlines import (
        normalize_airline_name,
        is_agency,
        baggage_url,
    )

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

    # 2026-05-21: hide agency names (Trip.com, Kiwi) — they're not the
    # operating carrier. Append a 🎒 link to the airline's baggage
    # policy when we know it; LCC fares often exclude any luggage so
    # this is critical info before booking.
    def _carrier_label(raw: str | None) -> str:
        name = normalize_airline_name(raw)
        if not name or is_agency(name):
            return "—"
        bag = baggage_url(name)
        if bag:
            return f"{name} · [🎒]({bag})"
        return name

    out_carrier = _carrier_label(outbound.get("airline"))
    in_carrier = _carrier_label(inbound.get("airline"))
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


def format_stopover_alert(
    leg1: dict,
    leg2: dict,
    leg3: dict,
    roundtrip_baseline: float,
    user_id: str | None = None,
    alert_key: str | None = None,
    has_guide: bool = False,
) -> str:
    """Stopover phase 1: format a 3-leg two-destination chain alert.

    leg1 = origin → hub, leg2 = hub → final destination, leg3 = final
    destination → origin. Visually aligned with format_split_ticket_alert
    (same badge ladder, strike-through baseline, per-leg deal links).

    All legs must include origin, destination, departure_date, price;
    airline and source_url are optional (Aviasales fallback link built
    per leg when missing).
    """
    from app.config import iata_label
    from app.notifications.airlines import (
        normalize_airline_name,
        is_agency,
        baggage_url,
    )
    from app.notifications.aviasales import build_aviasales_oneway_url

    origin = leg1["origin"]
    hub = leg1["destination"]
    dest = leg2["destination"]
    origin_label = iata_label(origin)
    hub_label = iata_label(hub)
    dest_label = iata_label(dest)

    total = int(round(leg1["price"] + leg2["price"] + leg3["price"]))
    rt_baseline = int(round(roundtrip_baseline))
    savings = max(0, rt_baseline - total)
    saving_pct = int(round((savings / rt_baseline) * 100)) if rt_baseline > 0 else 0
    badge = _deal_badge(saving_pct)

    def _carrier_label(raw: str | None) -> str:
        name = normalize_airline_name(raw)
        if not name or is_agency(name):
            return "—"
        bag = baggage_url(name)
        if bag:
            return f"{name} · [🎒]({bag})"
        return name

    def _leg_url(leg: dict) -> str:
        url = leg.get("source_url") or ""
        if not url or url == "N/A":
            try:
                url = build_aviasales_oneway_url(
                    leg["origin"], leg["destination"],
                    leg.get("departure_date", ""),
                    marker=settings.TRAVELPAYOUTS_MARKER or None,
                )
            except Exception:
                url = ""
        return url

    def _wrap(url: str) -> str:
        # All legs share the same alert_key — a click on any leg counts
        # as engagement on the chain (same product decision as combos).
        if user_id and alert_key:
            return _make_redirect_token(
                user_id, alert_key, origin, dest, url,
                trip_type="stopover",
                qualification_method="stopover_chain",
            )
        return _add_utms(url, origin, dest)

    lines = [
        f"*{badge} · 🧳 Stopover malin — 2 destinations*",
        "",
        f"🗺️ *{origin_label} → {hub_label} → {dest_label} → {origin_label}*",
        "",
        f"💰 *{total} € total · -{saving_pct} %*",
        f"   Prix habituel A/R direct {origin_label} → {dest_label} : ~{rt_baseline} €~",
        f"   Économie : {savings} € — et vous visitez {hub_label} en bonus",
        "   ✅ 3 billets vérifiés",
        "",
    ]
    for label, leg in (
        (f"Étape 1 — {origin_label} → {hub_label}", leg1),
        (f"Étape 2 — {hub_label} → {dest_label}", leg2),
        (f"Retour — {dest_label} → {origin_label}", leg3),
    ):
        carrier = _carrier_label(leg.get("airline"))
        price = int(round(leg["price"]))
        dep = _fmt_date_fr(leg.get("departure_date", ""))
        lines.append(f"✈️ *{label}*")
        lines.append(f"   {carrier} · {price} € · {dep}")
        url = _leg_url(leg)
        if url and url != "N/A":
            lines.append(f"   👉 [Voir le billet]({_wrap(url)})")
        lines.append("")

    lines.append("⚠️ 3 billets séparés : bagages et annulation gérés indépendamment.")
    if has_guide:
        lines += ["", f"📖 [Le guide complet de {dest_label}]({settings.FRONTEND_URL}/destination/{dest.lower()})"]
    return "\n".join(lines)


async def send_stopover_alert(
    chat_id: int,
    leg1: dict,
    leg2: dict,
    leg3: dict,
    roundtrip_baseline: float,
    user_id: str | None = None,
    alert_key: str | None = None,
    has_guide: bool = False,
    message_id: str | None = None,
) -> bool:
    """Stopover phase 1: send a Telegram alert for a 3-leg stopover chain.

    Same tracking/feedback contract as send_split_ticket_alert: a click
    on any leg counts as engagement; message_id (when set) enables the
    [👍/👎/⏱️] feedback row.
    """
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping stopover alert")
        return False
    msg = format_stopover_alert(
        leg1, leg2, leg3, roundtrip_baseline,
        user_id=user_id, alert_key=alert_key, has_guide=has_guide,
    )
    # Chain destination = the FINAL destination (leg2's arrival) — the
    # hub is a bonus stop, the user's travel intent is the spoke city.
    dest_iata = leg2.get("destination", "")
    reply_markup = _build_alert_keyboard(
        user_id=user_id,
        destination_iata=dest_iata,
        dest_label=_city_for_iata(dest_iata),
        message_id=message_id,
    )
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        return True
    except TimedOut:
        # See send_grouped_flight_alerts: a read-timeout after dispatch
        # almost always means delivered — record it so dedup holds.
        logger.warning(f"Stopover send to {chat_id} timed out post-dispatch — assuming delivered")
        return True
    except Exception as e:
        logger.error(f"Failed to send stopover alert to {chat_id}: {e}")
        return False


async def send_oneway_deal_alert(
    chat_id: int,
    flight: dict,
    discount_pct: float,
    baseline_price: float,
    return_estimate: float | None = None,
    user_id: str | None = None,
    alert_key: str | None = None,
    has_guide: bool = False,
    message_id: str | None = None,
) -> bool:
    """V5: send a Telegram alert for a one-way flight deal.

    When user_id+alert_key are provided, the booking link is wrapped in a
    /r/:token redirect for per-user click tracking. Otherwise UTMs only.
    message_id (when set) enables the [👍/👎/⏱️] feedback row, shared with
    the grouped + split-ticket flows.
    """
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping one-way alert")
        return False
    msg = format_oneway_deal_alert(
        flight, discount_pct, baseline_price, return_estimate,
        user_id=user_id, alert_key=alert_key, has_guide=has_guide,
    )
    reply_markup = _build_alert_keyboard(
        user_id=user_id,
        destination_iata=flight.get("destination", ""),
        dest_label=_city_for_iata(flight.get("destination", "")),
        message_id=message_id,
    )
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        return True
    except TimedOut:
        logger.warning(f"One-way send to {chat_id} timed out post-dispatch — assuming delivered")
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
    message_id: str | None = None,
) -> bool:
    """V5: send a Telegram alert for a 2x one-way (split-ticket) combo.

    user_id+alert_key enable /r/:token tracking on both legs (clicks on
    either leg count as engagement on the combo, per product decision).
    message_id (when set) enables the [👍/👎/⏱️] feedback row, shared with
    the grouped + one-way flows.
    """
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping split-ticket alert")
        return False
    msg = format_split_ticket_alert(
        outbound, inbound, roundtrip_baseline,
        user_id=user_id, alert_key=alert_key, has_guide=has_guide,
    )
    # Combo destination = outbound destination (where the user actually
    # ends up — the inbound is just the way back).
    dest_iata = outbound.get("destination", "")
    reply_markup = _build_alert_keyboard(
        user_id=user_id,
        destination_iata=dest_iata,
        dest_label=_city_for_iata(dest_iata),
        message_id=message_id,
    )
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        return True
    except TimedOut:
        logger.warning(f"Split-ticket send to {chat_id} timed out post-dispatch — assuming delivered")
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
    # Aggregate confidence signals across the offers. The badge ladder
    # caps at "Promo flash" when the smallest baseline behind any offer
    # is young, and the per-offer verification line switches to
    # "🔍 Prix indicatif" the moment any single offer comes from a
    # single-source confirmation or sits on a young baseline.
    sample_counts = [
        int(o.get("baseline_sample_count") or 0) for o in shown
    ]
    # `min_sample_count` is None when the offer dict doesn't carry the
    # baseline metadata at all (legacy callers, tests). When at least one
    # offer has positive evidence, we use the smallest positive sample
    # count — that's the worst-case confidence among shown offers.
    positive_samples = [s for s in sample_counts if s > 0]
    min_sample_count = min(positive_samples) if positive_samples else None
    price_confidences = {
        o.get("price_confidence") for o in shown if o.get("price_confidence")
    }
    any_young_baseline = any(
        0 < s < _YOUNG_BASELINE_SAMPLE_THRESHOLD for s in sample_counts
    )
    badge = _deal_badge(
        max_discount,
        sources=sources_in_offer,
        min_sample_count=min_sample_count if sample_counts else None,
    )
    verification_line = _price_verification_line(
        price_confidences, any_young_baseline
    )
    # 2026-06-10 (homogénéité): the discount % is now ALWAYS shown —
    # users flagged that some alerts carried "-XX %" and others didn't,
    # which read as two different products. The young-baseline honesty
    # safeguard (2026-05) survives as a "≈" prefix + the softer "Prix
    # observé récemment" framing instead of dropping the number: with
    # very few observations the figure is an estimate, and we say so,
    # but the presentation stays uniform across every alert type.
    approx_discount = any_young_baseline

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

        from app.notifications.airlines import (
            normalize_airline_name as _norm_air,
            is_agency as _is_agency,
            baggage_url as _baggage_url,
        )

        for o in month_offers:
            dep = datetime.strptime(o["departure_date"], "%Y-%m-%d")
            ret = datetime.strptime(o["return_date"], "%Y-%m-%d")
            duration = (ret - dep).days
            dep_str = f"{dep.day} {_FR_MONTHS_SHORT[dep.month]}"
            ret_str = f"{ret.day} {_FR_MONTHS_SHORT[ret.month]}"
            price = int(round(o["price"]))
            disc = int(round(o.get("discount_pct", 0)))

            baseline = o.get("baseline_price")
            # Soft framing when the baseline is young: "Prix observé
            # récemment" instead of "Prix habituel" — we have evidence
            # the price was seen, but not enough history to call it
            # "habituel".
            baseline_label = (
                "Prix observé récemment" if any_young_baseline else "Prix habituel"
            )
            baseline_str = (
                f"\n   {baseline_label} : ~{int(round(baseline))} €~"
                if baseline and baseline > price else ""
            )

            # V8.2: when the alert mixes several origin airports, tag the
            # specific origin on each offer line so the user knows which
            # airport this particular fare flies from.
            origin_tag = ""
            if multi_origin and o.get("origin"):
                origin_tag = f"  ·  via {o['origin']}"

            # 2026-06-10: the "-XX %" claim is always present. When the
            # baseline behind this alert is young the figure rests on
            # few observations, so it's framed as an estimate ("≈")
            # rather than dropped — see approx_discount above.
            price_line = (
                f"\n💰 *{price} € A/R · ≈ -{disc} %*{origin_tag}"
                if approx_discount
                else f"\n💰 *{price} € A/R · -{disc} %*{origin_tag}"
            )

            # 2026-05-21: surface the operating carrier + a 🎒 link to
            # its baggage policy. We deliberately hide names that
            # resolve to OTA / meta-search agencies (Trip.com, Kiwi…)
            # because they're not the airline operating the flight —
            # see app.notifications.airlines.is_agency().
            carrier = _norm_air(o.get("airline"))
            carrier_line = ""
            if carrier and not _is_agency(carrier):
                bag = _baggage_url(carrier)
                if bag:
                    carrier_line = f"\n   ✈️ {carrier} · [🎒]({bag})"
                else:
                    carrier_line = f"\n   ✈️ {carrier}"

            lines.append(
                f"{price_line}\n"
                f"   {dep_str} – {ret_str} · {duration} jours"
                f"{carrier_line}"
                f"{baseline_str}\n"
                f"   {verification_line}"
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
    # 2026-06-10: the catalogue link goes through /r/:token like the
    # deal links. It was the only untracked click path in the alert —
    # testers who browsed deals via /home registered ZERO "openings",
    # which made half the 👍 feedback look like "liked without opening"
    # and contradicted the survey ("j'ai déjà cliqué, si si !" at 57%).
    catalogue_url = f"{settings.FRONTEND_URL}/home?dest={destination_iata}"
    if user_id and alert_key:
        catalogue_url = _make_redirect_token(
            user_id, alert_key, origin_iata or "", destination_iata, catalogue_url,
            trip_type="catalogue",
            qualification_method=None,
        )
    msg_parts.append(f"👉 [Toutes les offres {destination_iata}]({catalogue_url})")

    msg = "\n".join(msg_parts)

    if tier == "free":
        msg += (
            "\n\n💎 Réservation directe réservée aux abonnés premium. "
            "Passez à la version premium pour débloquer les meilleurs deals."
        )
    return msg


# Threshold below which a user is considered "new" and shown feedback
# buttons in place of the Pause menu.
#
# Temporarily raised to 5000 during the beta phase (2026-05-18): we want
# ALL founders to see the feedback row so the operator gets continuous
# signal to calibrate seuils, not just the freshest 5 inscrits. Counting
# rows (not messages) — 1 grouped alert = N rows, so 5000 ≈ 1000-1500
# real Telegram messages, which covers every current founder.
#
# Once we've collected ~50 feedback clicks across the cohort, lower
# this back to 30 so newly onboarded users keep the calibration window
# but stabilised users get Pause back.
FEEDBACK_ONBOARDING_ALERT_LIMIT = 5000


def _build_alert_keyboard(
    *,
    user_id: str | None,
    destination_iata: str,
    dest_label: str | None,
    message_id: str | None,
) -> InlineKeyboardMarkup | None:
    """Shared inline-keyboard builder for all alert types (grouped flight,
    one-way, split-ticket combo). Three responsibilities:

      1. "Masquer <destination>" — one-tap dismiss for the destination.
      2. Feedback row [👍][👎][⏱️] for the first FEEDBACK_ONBOARDING_ALERT_LIMIT
         alerts of a user's lifetime, when message_id is set. The callback
         handler writes to sent_alerts.feedback (last click wins).
      3. Otherwise, the Pause-menu button.

    Returns None when user_id is missing — alerts sent in test contexts
    (no DB user) skip the buttons entirely.
    """
    if not user_id:
        return None
    short_dest = (dest_label or destination_iata)[:18]
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(
            f"🚫 Masquer {short_dest}",
            callback_data=f"block:{user_id}:{destination_iata}",
        )],
    ]
    show_feedback = (
        message_id is not None
        and _count_alerts_lifetime(user_id) < FEEDBACK_ONBOARDING_ALERT_LIMIT
    )
    if show_feedback:
        rows.append([
            InlineKeyboardButton("👍 Bon", callback_data=f"feedback:good:{message_id}"),
            InlineKeyboardButton("👎 Faux", callback_data=f"feedback:bad:{message_id}"),
            InlineKeyboardButton("⏱️ Trop tard", callback_data=f"feedback:late:{message_id}"),
        ])
    else:
        rows.append([
            InlineKeyboardButton("⏸ Pause les alertes", callback_data=f"pause_menu:{user_id}"),
        ])
    return InlineKeyboardMarkup(rows)


def _count_alerts_lifetime(user_id: str) -> int:
    """How many sent_alerts rows exist for this user, ever. Used by
    send_grouped_flight_alerts to decide whether to show feedback
    buttons or the standard Pause menu. Fails open (returns a high
    number) on DB error → fall back to Pause menu, which is the
    safer default (we never strand the user without a way to pause).
    """
    from app.db import db
    if not db or not user_id:
        return 9999
    try:
        r = (
            db.table("sent_alerts")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return r.count or 0
    except Exception as e:
        logger.warning(f"_count_alerts_lifetime failed for {user_id}: {e}")
        return 9999


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
    message_id: str | None = None,
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

    reply_markup = _build_alert_keyboard(
        user_id=user_id,
        destination_iata=destination_iata,
        dest_label=dest_city,
        message_id=message_id,
    )

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        return True
    except TimedOut:
        # PTB read-timeout AFTER Telegram processed the send: the message
        # is almost always delivered, only our HTTP response was slow.
        # Returning False here is what caused the 2026-06-12 duplicate
        # storm (same AGP alert delivered 5× in 100 min to two users):
        # the caller skipped the sent_alerts persist, so every following
        # cycle re-sent a message the user already had. Treat as
        # delivered: worst case (genuinely dropped send) is one missed
        # alert, vs a guaranteed duplicate every 20 min otherwise.
        logger.warning(
            f"Telegram send to {chat_id} timed out AFTER dispatch — "
            f"assuming delivered (returning True so dedup records it)"
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
        # parse_mode added 2026-06-10 — the harmonised template uses the
        # same Markdown (bold price, ~strike~ baseline) as every other
        # alert type.
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram alert to {chat_id}: {e}")
        return False


async def send_digest(chat_id: int, packages: list[dict]) -> bool:
    bot = _get_bot()
    if not bot:
        return False
    try:
        msg = format_digest(packages)
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        return True
    except Exception as e:
        # Formatting errors are caught too — a malformed deal row must
        # not crash the whole digest loop for every subscriber.
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


async def send_admin_text(message: str) -> bool:
    """Send a plain-text admin message without Markdown parsing.
    Use this when the message body may contain characters Markdown
    would mis-interpret (e.g. raw `*` from wildcard route keys, `_`
    in identifiers, `[` from log lines)."""
    bot = _get_bot()
    if not bot or not settings.TELEGRAM_ADMIN_CHAT_ID:
        return False
    try:
        await bot.send_message(
            chat_id=int(settings.TELEGRAM_ADMIN_CHAT_ID),
            text=message,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send admin text: {e}")
        return False


async def send_user_text(chat_id: int, message: str) -> bool:
    """Send a plain-text message to a single user's chat. No Markdown
    parsing, so the body can contain any characters safely. Returns
    True on success."""
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping user message")
        return False
    try:
        await bot.send_message(chat_id=chat_id, text=message)
        return True
    except Exception as e:
        logger.error(f"Failed to send user message to {chat_id}: {e}")
        return False


async def send_broadcast(message: str, chat_ids: list[int]) -> tuple[int, int]:
    """Send a plain-text broadcast to a list of chat_ids. Returns
    (delivered, failed). Sequential with a small delay to stay well
    under Telegram's ~30 msg/s global limit and avoid a bot ban; at
    beta scale (tens of recipients) this is plenty fast.

    Plain text (no parse_mode) so the operator's message can't break
    on stray Markdown characters mid-send."""
    import asyncio as _asyncio
    bot = _get_bot()
    if not bot:
        return 0, len(chat_ids)
    delivered = 0
    failed = 0
    for cid in chat_ids:
        try:
            await bot.send_message(chat_id=cid, text=message)
            delivered += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Broadcast send failed for chat {cid}: {e}")
        await _asyncio.sleep(0.05)  # ~20 msg/s, safely under the limit
    return delivered, failed


async def send_survey(
    message: str,
    options: list[tuple[str, str]],
    survey_key: str,
    chat_ids: list[int],
) -> tuple[int, int]:
    """Send a survey message with inline-button options to each chat.

    `options` is a list of (choice_code, label) — one button per row so
    long French labels render fully. callback_data is
    "survey:<survey_key>:<choice>", handled in bot_handler._record_survey.
    Returns (delivered, failed). Throttled like send_broadcast."""
    import asyncio as _asyncio
    bot = _get_bot()
    if not bot:
        return 0, len(chat_ids)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"survey:{survey_key}:{code}")]
        for code, label in options
    ])
    delivered = 0
    failed = 0
    for cid in chat_ids:
        try:
            await bot.send_message(chat_id=cid, text=message, reply_markup=keyboard)
            delivered += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Survey send failed for chat {cid}: {e}")
        await _asyncio.sleep(0.05)
    return delivered, failed


async def send_admin_markdown(message: str) -> bool:
    bot = _get_bot()
    if not bot or not settings.TELEGRAM_ADMIN_CHAT_ID:
        return False
    try:
        await bot.send_message(
            chat_id=int(settings.TELEGRAM_ADMIN_CHAT_ID),
            text=message,
            parse_mode="Markdown",
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send admin markdown: {e}")
        return False
