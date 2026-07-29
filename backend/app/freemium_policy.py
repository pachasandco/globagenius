"""Runtime policy for GlobeGenius Freemium, Premium trials and OG access.

This module deliberately sits outside the deal detection pipeline. The existing
scheduler still ranks candidates; this policy is the final entitlement gate
before a Telegram message is sent.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import db
from app.notifications.telegram import (
    _get_bot,
    send_grouped_flight_alerts as _send_grouped_flight_alerts,
)

logger = logging.getLogger(__name__)

PREMIUM_TRIAL_DAYS = 7
FREEMIUM_REGULAR_ALERTS_PER_WEEK = 2
FREEMIUM_EXCEPTIONAL_ALERTS_PER_MONTH = 1
FREEMIUM_MONTHLY_UNLOCKS = 1
FREEMIUM_EXCEPTIONAL_MIN_DISCOUNT_PCT = 50

# Existing beta accounts must move to Freemium unless they own the OG badge.
# Only accounts created after the public-model cutover may start a new trial.
PUBLIC_TRIAL_ELIGIBILITY_START = datetime(2026, 7, 29, 20, 30, tzinfo=timezone.utc)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _active_grant(row: dict[str, Any] | None) -> bool:
    if not row or row.get("revoked"):
        return False
    expiry = _parse_dt(row.get("expires_at"))
    return expiry is None or expiry > datetime.now(timezone.utc)


def _count_alerts(user_id: str, prefix: str, since: datetime) -> int:
    if not db:
        return 0
    response = (
        db.table("sent_alerts")
        .select("alert_key", count="exact")
        .eq("user_id", user_id)
        .like("alert_key", f"{prefix}:%")
        .gte("created_at", since.isoformat())
        .execute()
    )
    return response.count or 0


def _primary_airport(user_id: str) -> str | None:
    if not db:
        return None
    response = (
        db.table("user_preferences")
        .select("airport_codes")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    airports = response.data[0].get("airport_codes") or []
    return airports[0] if airports else None


async def guarded_send_grouped_flight_alerts(
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
    """Apply the Freemium entitlement policy before the Telegram send.

    Premium, active trial and OG users reach this function with tier=premium and
    remain untouched. A free user gets one departure airport, two complete
    regular A/R alerts per rolling seven days and one exceptional A/R alert per
    rolling thirty days. The scheduler already excludes one-way and split-ticket
    full alerts for free users.
    """
    if tier == "free" and user_id:
        try:
            primary = await asyncio.to_thread(_primary_airport, user_id)
            if primary and origin_iata and origin_iata != primary:
                logger.info(
                    "Freemium airport gate: blocked %s for %s (primary=%s)",
                    origin_iata,
                    user_id,
                    primary,
                )
                return False

            best_discount = max(
                (float(offer.get("discount_pct") or 0) for offer in offers),
                default=0.0,
            )
            now = datetime.now(timezone.utc)
            if best_discount >= FREEMIUM_EXCEPTIONAL_MIN_DISCOUNT_PCT:
                used = await asyncio.to_thread(
                    _count_alerts,
                    user_id,
                    "fwk",
                    now - timedelta(days=30),
                )
                if used >= FREEMIUM_EXCEPTIONAL_ALERTS_PER_MONTH:
                    logger.info("Freemium monthly exceptional quota reached for %s", user_id)
                    return False
            else:
                used = await asyncio.to_thread(
                    _count_alerts,
                    user_id,
                    "fday",
                    now - timedelta(days=7),
                )
                if used >= FREEMIUM_REGULAR_ALERTS_PER_WEEK:
                    logger.info("Freemium weekly regular quota reached for %s", user_id)
                    return False
        except Exception as exc:
            # Fail closed for free entitlements: an unavailable quota check must
            # never accidentally unlock unlimited alerts.
            logger.warning("Freemium entitlement check failed for %s: %s", user_id, exc)
            return False

    return await _send_grouped_flight_alerts(
        chat_id=chat_id,
        origin_city=origin_city,
        dest_city=dest_city,
        destination_iata=destination_iata,
        offers=offers,
        tier=tier,
        user_id=user_id,
        alert_key=alert_key,
        origin_iata=origin_iata,
        has_guide=has_guide,
        message_id=message_id,
    )


def reconcile_legacy_access() -> dict[str, int]:
    """Keep Premium for OG badges and downgrade legacy non-OG founders.

    Paid Stripe access, manual grants and active discovery trials are not
    touched. The operation is idempotent and safe to run on every deployment.
    """
    stats = {"og_kept": 0, "non_og_downgraded": 0, "grants_revoked": 0}
    if not db:
        return stats

    users = db.table("users").select("id,badge,tier").execute().data or []
    grants = db.table("premium_grants").select(
        "user_id,granted_by,reason,revoked,expires_at"
    ).execute().data or []
    grants_by_user = {row.get("user_id"): row for row in grants}
    now = datetime.now(timezone.utc).isoformat()

    for user in users:
        user_id = user.get("id")
        if not user_id:
            continue
        badge = bool(user.get("badge"))
        grant = grants_by_user.get(user_id)

        if badge:
            db.table("premium_grants").upsert(
                {
                    "user_id": user_id,
                    "granted_by": "og_badge",
                    "expires_at": None,
                    "reason": "OG badge — Premium lifetime",
                    "revoked": False,
                    "revoked_at": None,
                },
                on_conflict="user_id",
            ).execute()
            if user.get("tier") != "premium_grandfathered":
                db.table("users").update({"tier": "premium_grandfathered"}).eq(
                    "id", user_id
                ).execute()
            stats["og_kept"] += 1
            continue

        is_founder_grant = bool(
            grant
            and (
                grant.get("granted_by") == "auto_founder_beta"
                or "founder_beta" in str(grant.get("reason") or "")
            )
        )
        if is_founder_grant and not grant.get("revoked"):
            db.table("premium_grants").update(
                {"revoked": True, "revoked_at": now}
            ).eq("user_id", user_id).execute()
            stats["grants_revoked"] += 1

        if user.get("tier") == "premium_grandfathered":
            db.table("users").update({"tier": "free"}).eq("id", user_id).execute()
            stats["non_og_downgraded"] += 1

    logger.info("Freemium access reconciliation complete: %s", stats)
    return stats


def _grant_trial_if_eligible(user_id: str) -> tuple[bool, datetime | None]:
    """Start a one-time seven-day trial for a new public account."""
    if not db:
        return False, None

    user_response = (
        db.table("users")
        .select("badge,created_at")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not user_response.data:
        return False, None
    user = user_response.data[0]
    if user.get("badge"):
        return False, None

    created_at = _parse_dt(user.get("created_at"))
    if not created_at or created_at < PUBLIC_TRIAL_ELIGIBILITY_START:
        return False, None

    grant_response = (
        db.table("premium_grants")
        .select("granted_by,expires_at,revoked")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    existing = grant_response.data[0] if grant_response.data else None
    if existing and existing.get("granted_by") == "auto_premium_trial":
        return False, _parse_dt(existing.get("expires_at"))
    if _active_grant(existing):
        return False, _parse_dt(existing.get("expires_at"))

    expires_at = datetime.now(timezone.utc) + timedelta(days=PREMIUM_TRIAL_DAYS)
    db.table("premium_grants").upsert(
        {
            "user_id": user_id,
            "granted_by": "auto_premium_trial",
            "expires_at": expires_at.isoformat(),
            "reason": "Premium Découverte — 7 jours",
            "revoked": False,
            "revoked_at": None,
        },
        on_conflict="user_id",
    ).execute()
    return True, expires_at


async def link_account_with_trial(chat_id: int, token: str, chat: dict) -> None:
    """Link Telegram and start Premium Découverte for eligible new accounts."""
    bot = _get_bot()
    if not bot or not db:
        return

    prefs = (
        db.table("user_preferences")
        .select("user_id,airport_codes")
        .eq("telegram_connect_token", token)
        .limit(1)
        .execute()
    )
    if not prefs.data:
        await send_unlinked_welcome(chat_id)
        return

    user_id = prefs.data[0]["user_id"]
    airports = prefs.data[0].get("airport_codes") or ["CDG"]
    primary_airport = airports[0] if airports else "CDG"

    db.table("user_preferences").update(
        {
            "telegram_chat_id": chat_id,
            "telegram_connected": True,
            "telegram_connect_token": None,
        }
    ).eq("user_id", user_id).execute()
    db.table("telegram_subscribers").upsert(
        {"chat_id": chat_id, "airport_code": primary_airport, "user_id": user_id},
        on_conflict="chat_id",
    ).execute()

    trial_started, trial_expires = await asyncio.to_thread(
        _grant_trial_if_eligible, user_id
    )
    user_row = (
        db.table("users").select("badge").eq("id", user_id).limit(1).execute()
    )
    is_og = bool(user_row.data and user_row.data[0].get("badge"))

    name = chat.get("first_name", "")
    if is_og:
        plan_text = (
            "🏅 Ton badge OG maintient ton accès Premium sans limite de durée."
        )
    elif trial_started or (trial_expires and trial_expires > datetime.now(timezone.utc)):
        expiry_text = trial_expires.astimezone(timezone.utc).strftime("%d/%m/%Y") if trial_expires else ""
        plan_text = (
            "🎁 Tes 7 jours de Premium Découverte commencent maintenant, "
            f"sans carte bancaire. Fin prévue le {expiry_text}."
        )
    else:
        plan_text = (
            "🆓 Ton compte Freemium comprend 2 alertes complètes par semaine, "
            "1 pépite exceptionnelle par mois et 1 joker mensuel."
        )

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"✅ Compte lié !\n\nSalut {name} 👋\n\n{plan_text}\n\n"
            "Les alertes sont envoyées dès qu’un prix réellement anormal est "
            "confirmé — sans retard artificiel.\n\n"
            "📋 Commandes utiles :\n"
            "/pause — suspendre les alertes\n"
            "/destinations — masquer des destinations\n"
            "/status — état du service\n"
            "/help — aide\n\n"
            "Bon voyage ✈️"
        ),
    )


async def send_unlinked_welcome(chat_id: int) -> None:
    """Welcome copy for a Telegram user who has not linked an account yet."""
    bot = _get_bot()
    if not bot:
        return
    await bot.send_message(
        chat_id=chat_id,
        text=(
            "✈️ Bienvenue sur GlobeGenius\n\n"
            "Nous surveillons les prix depuis les principaux aéroports français "
            "et envoyons uniquement les baisses réellement intéressantes.\n\n"
            "Pour activer vos alertes :\n"
            "1️⃣ Créez votre compte sur https://globegenius.app\n"
            "2️⃣ Choisissez votre aéroport de départ\n"
            "3️⃣ Reliez Telegram depuis votre espace\n\n"
            "🎁 Les nouveaux comptes bénéficient de 7 jours de Premium Découverte, "
            "sans carte bancaire."
        ),
    )
