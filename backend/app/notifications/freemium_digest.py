"""Programme d'emails freemium — boucle de conversion permanente (2026-07-30).

Principe : « GlobeGenius a continué à chercher pour vous. Voici ce que
vous avez reçu, ce que vous avez manqué, et ce que Premium aurait
débloqué. » Trois emails, tous adossés au produit RÉEL (bande quotidienne
20-40% + gros deal >=40% hebdo + 3 déblocages homepage — PAS le quota
théorique « 2/semaine ») :

  1. Digest hebdomadaire   (cron dimanche)   — freemium_digest_YYYY_WW
  2. Quota atteint          (event dispatcher) — freemium_quota_YYYY_WW
  3. Bilan mensuel          (cron le 1er)      — freemium_monthly_YYYY_MM

Garde-fous :
  - CNIL : uniquement users.marketing_consent = true (collecté au signup,
    case décochée par défaut ; décision fondateur : pas d'opt-in rétroactif
    forcé pour les anciens). Les Premium/OG sont exclus (rien à convertir).
  - Idempotence + plafond de fréquence par onboarding_email_log avec une
    clé périodique dans email_type (migration 063). Un type par période
    = jamais deux envois du même email dans la même semaine/mois.
  - Les économies affichées viennent des prix réellement observés
    (baseline_price - price) — jamais de montant inventé.
  - Template Brevo à 0 → skip silencieux (déploiement sûr avant que les
    templates existent).

Variables template Brevo (params transactionnels) :
  ALERTS_RECEIVED, MATCHING_DEALS, MISSED_DEALS, BEST_MISSED_DESTINATION,
  BEST_MISSED_DISCOUNT, BEST_MISSED_SAVINGS, PRIMARY_AIRPORT, UPGRADE_URL
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db import db
from app.notifications.onboarding_emails import (
    _already_sent,
    _mark_sent,
    _send_brevo_template,
)
from app.thresholds import FREE_TIER_DAILY_BAND_MIN_PCT

logger = logging.getLogger(__name__)

UPGRADE_URL = "https://globegenius.app/home?upgrade=1&utm_source=email&utm_medium=freemium_loop"

# Ville lisible pour les codes IATA les plus fréquents du digest. Un code
# absent s'affiche tel quel — jamais bloquant.
_IATA_LABEL = {
    "BCN": "Barcelone", "LIS": "Lisbonne", "FCO": "Rome", "RAK": "Marrakech",
    "MAD": "Madrid", "OPO": "Porto", "ATH": "Athènes", "NRT": "Tokyo",
    "HND": "Tokyo", "BKK": "Bangkok", "JFK": "New York", "DXB": "Dubaï",
    "SAW": "Istanbul", "TUN": "Tunis", "AGP": "Malaga", "PMI": "Palma",
}


def week_key(now: datetime) -> str:
    iso = now.isocalendar()
    return f"{iso[0]}_{iso[1]:02d}"


def month_key(now: datetime) -> str:
    return now.strftime("%Y_%m")


# ── Calcul pur ─────────────────────────────────────────────────────────────


def summarize_matching_deals(
    deals: list[dict],
    sent_full_alerts: list[dict],
    prefs: dict,
) -> dict:
    """Compte les deals de la fenêtre qui matchent le profil du user, ceux
    réellement reçus en alerte complète, et le meilleur deal manqué.

    `deals` : origin, destination, discount_pct, price, baseline_price,
    departure_date, trip_type. `sent_full_alerts` : destination,
    departure_date. Pure — aucune I/O."""
    airports = set(prefs.get("airport_codes") or [])
    blocked = set(prefs.get("blocked_destinations") or [])
    trip_types = set(prefs.get("flight_trip_types") or ["round_trip", "one_way"])

    matching = []
    for d in deals:
        if d.get("origin") not in airports:
            continue
        if d.get("destination") in blocked:
            continue
        if (d.get("trip_type") or "round_trip") not in trip_types:
            continue
        # Plancher de visibilité free : sous 20%, le produit n'alerte
        # jamais — un deal invisible n'est pas « manqué ».
        if (d.get("discount_pct") or 0) < FREE_TIER_DAILY_BAND_MIN_PCT:
            continue
        matching.append(d)

    sent_keys = {
        (a.get("destination"), (a.get("departure_date") or "")[:10])
        for a in sent_full_alerts
    }
    received = [
        d for d in matching
        if (d["destination"], (d.get("departure_date") or "")[:10]) in sent_keys
    ]
    missed = [
        d for d in matching
        if (d["destination"], (d.get("departure_date") or "")[:10]) not in sent_keys
    ]

    best = None
    if missed:
        top = max(missed, key=lambda d: d.get("discount_pct") or 0)
        baseline = top.get("baseline_price")
        price = top.get("price")
        savings = None
        if baseline and price and baseline > price:
            savings = round(baseline - price)
        best = {
            "destination": top["destination"],
            "discount_pct": top.get("discount_pct"),
            "price": price,
            "baseline_price": baseline,
            "savings": savings,
        }

    return {
        "matching": len(matching),
        "received_full": len(received),
        "missed": len(missed),
        "best_missed": best,
    }


# ── Fetch ──────────────────────────────────────────────────────────────────


def _fetch_window_deals(days: int) -> list[dict]:
    """Deals flight qualifiés sur la fenêtre, joints à raw_flights pour
    origin/destination. Paginé ; la jointure se fait par lots d'ids."""
    if not db:
        return []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    qis: list[dict] = []
    offset = 0
    while True:
        page = (
            db.table("qualified_items")
            .select("item_id, price, baseline_price, discount_pct, trip_type, created_at")
            .eq("type", "flight")
            .gte("created_at", cutoff)
            .range(offset, offset + 999)
            .execute()
            .data
            or []
        )
        qis.extend(page)
        if len(page) < 1000:
            break
        offset += 1000
    if not qis:
        return []

    flights: dict[str, dict] = {}
    ids = [q["item_id"] for q in qis if q.get("item_id")]
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        rows = (
            db.table("raw_flights")
            .select("id, origin, destination, departure_date")
            .in_("id", batch)
            .execute()
            .data
            or []
        )
        for r in rows:
            flights[r["id"]] = r

    out = []
    for q in qis:
        f = flights.get(q.get("item_id"))
        if not f:
            continue  # raw_flight purgé — deal non reconstituable
        out.append({
            "origin": f["origin"],
            "destination": f["destination"],
            "departure_date": f.get("departure_date"),
            "discount_pct": q.get("discount_pct"),
            "price": q.get("price"),
            "baseline_price": q.get("baseline_price"),
            "trip_type": q.get("trip_type") or "round_trip",
        })
    return out


def _fetch_sent_full_alerts(days: int) -> dict[str, list[dict]]:
    """sent_alerts complètes (hors teasers) de la fenêtre, groupées par
    user_id."""
    if not db:
        return {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    by_user: dict[str, list[dict]] = {}
    offset = 0
    while True:
        page = (
            db.table("sent_alerts")
            .select("user_id, destination, departure_date, alert_type")
            .gte("sent_at", cutoff)
            .range(offset, offset + 999)
            .execute()
            .data
            or []
        )
        for r in page:
            uid = r.get("user_id")
            if not uid or r.get("alert_type") == "locked_teaser":
                continue
            by_user.setdefault(uid, []).append(r)
        if len(page) < 1000:
            break
        offset += 1000
    return by_user


def _free_consented_recipients() -> list[dict]:
    """Users free (pas de grant premium actif) avec marketing_consent.

    Retourne id, email, primary_airport + prefs nécessaires au matching."""
    if not db:
        return []
    users = (
        db.table("users")
        .select("id, email, marketing_consent")
        .eq("marketing_consent", True)
        .execute()
        .data
        or []
    )
    if not users:
        return []
    ids = [u["id"] for u in users]
    now = datetime.now(timezone.utc).isoformat()
    grants = (
        db.table("premium_grants")
        .select("user_id, expires_at, revoked")
        .in_("user_id", ids)
        .eq("revoked", False)
        .execute()
        .data
        or []
    )
    premium_ids = {
        g["user_id"] for g in grants
        if not g.get("expires_at") or g["expires_at"] > now
    }
    prefs_rows = (
        db.table("user_preferences")
        .select("user_id, airport_codes, blocked_destinations, flight_trip_types")
        .in_("user_id", ids)
        .execute()
        .data
        or []
    )
    prefs_by_user = {p["user_id"]: p for p in prefs_rows}
    out = []
    for u in users:
        if u["id"] in premium_ids:
            continue  # Premium/OG : exclus de la boucle de conversion
        p = prefs_by_user.get(u["id"]) or {}
        out.append({
            "id": u["id"],
            "email": u["email"],
            "prefs": {
                "airport_codes": p.get("airport_codes") or ["CDG"],
                "blocked_destinations": p.get("blocked_destinations") or [],
                "flight_trip_types": p.get("flight_trip_types") or ["round_trip", "one_way"],
            },
        })
    return out


# ── Envois ─────────────────────────────────────────────────────────────────


def _digest_params(user: dict, stats: dict) -> dict:
    best = stats.get("best_missed") or {}
    dest = best.get("destination") or ""
    return {
        "ALERTS_RECEIVED": stats["received_full"],
        "MATCHING_DEALS": stats["matching"],
        "MISSED_DEALS": stats["missed"],
        "BEST_MISSED_DESTINATION": _IATA_LABEL.get(dest, dest),
        "BEST_MISSED_DISCOUNT": round(best.get("discount_pct") or 0),
        "BEST_MISSED_SAVINGS": best.get("savings") or 0,
        "PRIMARY_AIRPORT": (user["prefs"]["airport_codes"] or ["CDG"])[0],
        "UPGRADE_URL": UPGRADE_URL,
    }


async def _run_periodic_email(
    *, template_id: int, email_type: str, window_days: int, min_matching: int
) -> dict:
    """Boucle commune digest hebdo / bilan mensuel : calcule les stats de
    la fenêtre pour chaque destinataire free consentant et envoie via le
    template. Skips: template=0, déjà envoyé sur la période, ou fenêtre
    vide (< min_matching deals matchés — un email vide dévalorise)."""
    counts = {"sent": 0, "skipped": 0}
    if not template_id:
        logger.info("freemium %s: template non configuré — skip", email_type)
        return counts
    recipients = _free_consented_recipients()
    if not recipients:
        return counts
    deals = _fetch_window_deals(window_days)
    sent_by_user = _fetch_sent_full_alerts(window_days)
    for user in recipients:
        if _already_sent(user["id"], email_type):
            counts["skipped"] += 1
            continue
        stats = summarize_matching_deals(
            deals, sent_by_user.get(user["id"], []), user["prefs"]
        )
        if stats["matching"] < min_matching:
            counts["skipped"] += 1
            continue
        ok = await _send_brevo_template(
            to_email=user["email"],
            template_id=template_id,
            params=_digest_params(user, stats),
        )
        if ok:
            _mark_sent(user["id"], email_type)
            counts["sent"] += 1
        else:
            counts["skipped"] += 1
    return counts


async def send_freemium_digest_once() -> dict:
    """Digest hebdomadaire — « ce que vous avez reçu / manqué cette semaine »."""
    now = datetime.now(timezone.utc)
    return await _run_periodic_email(
        template_id=settings.BREVO_FREEMIUM_DIGEST_TEMPLATE_ID,
        email_type=f"freemium_digest_{week_key(now)}",
        window_days=7,
        min_matching=1,
    )


async def send_freemium_monthly_once() -> dict:
    """Bilan mensuel — le « relevé GlobeGenius » cumulé sur 30 jours."""
    now = datetime.now(timezone.utc)
    return await _run_periodic_email(
        template_id=settings.BREVO_FREEMIUM_MONTHLY_TEMPLATE_ID,
        email_type=f"freemium_monthly_{month_key(now)}",
        window_days=30,
        min_matching=1,
    )


async def send_quota_reached_emails(user_ids: set[str]) -> dict:
    """Event dispatcher : des deals ont été retenus faute de place dans
    les couloirs free (free_no_room). Max 1 email / user / semaine ISO
    via la clé périodique. Best-effort — ne doit jamais casser le
    dispatch."""
    counts = {"sent": 0, "skipped": 0}
    template_id = settings.BREVO_FREEMIUM_QUOTA_TEMPLATE_ID
    if not template_id or not user_ids or not db:
        return counts
    now = datetime.now(timezone.utc)
    email_type = f"freemium_quota_{week_key(now)}"
    try:
        recipients = {u["id"]: u for u in _free_consented_recipients()}
    except Exception as e:
        logger.warning("freemium quota: fetch recipients failed: %s", e)
        return counts
    deals = None
    sent_by_user = None
    for uid in user_ids:
        user = recipients.get(uid)
        if not user:
            counts["skipped"] += 1
            continue
        if _already_sent(uid, email_type):
            counts["skipped"] += 1
            continue
        # Fetch paresseux : uniquement si au moins un envoi est possible.
        if deals is None:
            deals = _fetch_window_deals(7)
            sent_by_user = _fetch_sent_full_alerts(7)
        stats = summarize_matching_deals(deals, sent_by_user.get(uid, []), user["prefs"])
        ok = await _send_brevo_template(
            to_email=user["email"],
            template_id=template_id,
            params=_digest_params(user, stats),
        )
        if ok:
            _mark_sent(uid, email_type)
            counts["sent"] += 1
        else:
            counts["skipped"] += 1
    return counts
