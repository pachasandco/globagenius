"""Onboarding email sequence — chantier 10 (2026-05-17).

Three emails post-signup:

  J0    welcome (already shipped via app.notifications.welcome_email)
  J+1   Telegram-not-linked reminder
  J+7   no-alert-received nudge (preferences likely too strict)

This module handles J+1 and J+7. The trigger is a daily cron
(`job_send_onboarding_emails` in scheduler/jobs.py) that:

1. Pulls users created between (now - 2d) and (now - 1d) without a
   linked Telegram → sends J+1 reminder.
2. Pulls users created between (now - 8d) and (now - 7d) WITH a
   linked Telegram but no row in sent_alerts ever → sends J+7 nudge.

Idempotence: each email type tracks "last_sent_at" in a new
`onboarding_email_log` table to avoid spamming on cron retries. If
the table doesn't exist, we fall back to log-only (no DB write) —
the email still fires once per cron run, which is acceptable for a
daily cadence.

Brevo template IDs:
  BREVO_RELANCE_TELEGRAM_TEMPLATE_ID  → J+1
  BREVO_INACTIVITY_TEMPLATE_ID        → J+7

Either set to 0 → email skipped, logged as "would-send".

The actual template content (subject, HTML body) lives in Brevo's
template editor — this module only orchestrates the trigger logic.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.db import db

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


# ── Brevo send helper ──────────────────────────────────────────────────────


async def _send_brevo_template(
    *,
    to_email: str,
    template_id: int,
    params: dict | None = None,
) -> bool:
    """POST to Brevo with the given template and params. Returns True
    on success (HTTP 2xx), False on any error (logged)."""
    if not settings.BREVO_API_KEY or not template_id:
        logger.info(
            "Brevo template skipped (BREVO_API_KEY=%s, template_id=%s) for %s",
            bool(settings.BREVO_API_KEY), template_id, to_email,
        )
        return False
    payload = {
        "to": [{"email": to_email}],
        "templateId": template_id,
        "params": params or {},
        "sender": {
            "email": settings.BREVO_SENDER_EMAIL,
            "name": settings.BREVO_SENDER_NAME,
        },
    }
    headers = {
        "api-key": settings.BREVO_API_KEY,
        "accept": "application/json",
        "content-type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(BREVO_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
        logger.info("Brevo template %s sent to %s", template_id, to_email)
        return True
    except Exception as e:
        logger.error("Brevo template %s send failed for %s: %s", template_id, to_email, e)
        return False


# ── Idempotence log ────────────────────────────────────────────────────────


def _already_sent(user_id: str, email_type: str) -> bool:
    """Check `onboarding_email_log` for a prior send of this type.

    Falls back to False (= "not sent, please send") if the table
    doesn't exist or the query fails. Worst case: a user gets the
    same email twice on a single cron retry; the cron only runs
    once a day so the risk is minor."""
    if not db:
        return False
    try:
        r = (
            db.table("onboarding_email_log")
            .select("id")
            .eq("user_id", user_id)
            .eq("email_type", email_type)
            .limit(1)
            .execute()
        )
        return bool(r.data)
    except Exception as e:
        # Table likely missing (pre-migration) — log + treat as "not sent".
        logger.debug("onboarding_email_log lookup failed (%s) — sending anyway", e)
        return False


def _mark_sent(user_id: str, email_type: str) -> None:
    if not db:
        return
    try:
        db.table("onboarding_email_log").insert({
            "user_id": user_id,
            "email_type": email_type,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.debug("onboarding_email_log insert failed (%s) — non-fatal", e)


# ── Cohort queries ─────────────────────────────────────────────────────────


def _users_unlinked_telegram_24h_to_48h() -> list[dict]:
    """Users created 24h-48h ago who haven't linked Telegram yet.

    The window is 24h wide so a daily cron catches each user exactly
    once. Edge case: a user created at exactly H-25 might be missed
    on the day H cron and caught on H+1 — acceptable for a J+1 nudge.
    """
    if not db:
        return []
    now = datetime.now(timezone.utc)
    end = (now - timedelta(hours=24)).isoformat()
    start = (now - timedelta(hours=48)).isoformat()
    try:
        u = (
            db.table("users")
            .select("id,email,created_at")
            .gte("created_at", start)
            .lt("created_at", end)
            .execute()
        )
    except Exception as e:
        logger.error("users J+1 cohort query failed: %s", e)
        return []
    users = u.data or []
    if not users:
        return []
    # Filter: only those WITHOUT telegram_chat_id
    ids = [x["id"] for x in users]
    try:
        prefs = (
            db.table("user_preferences")
            .select("user_id,telegram_chat_id")
            .in_("user_id", ids)
            .execute()
        )
    except Exception as e:
        logger.error("user_preferences J+1 lookup failed: %s", e)
        return []
    linked = {
        p["user_id"] for p in (prefs.data or [])
        if p.get("telegram_chat_id")
    }
    return [u for u in users if u["id"] not in linked]


def _users_linked_telegram_but_no_alerts_7d() -> list[dict]:
    """Users created 7-8 days ago who linked Telegram but never
    received an alert. Likely their preferences (min_discount,
    blocked destinations) are too strict, or they're in a quiet week."""
    if not db:
        return []
    now = datetime.now(timezone.utc)
    end = (now - timedelta(days=7)).isoformat()
    start = (now - timedelta(days=8)).isoformat()
    try:
        u = (
            db.table("users")
            .select("id,email,created_at")
            .gte("created_at", start)
            .lt("created_at", end)
            .execute()
        )
    except Exception as e:
        logger.error("users J+7 cohort query failed: %s", e)
        return []
    users = u.data or []
    if not users:
        return []
    ids = [x["id"] for x in users]
    # Keep only the ones who linked Telegram
    try:
        prefs = (
            db.table("user_preferences")
            .select("user_id,airport_codes,min_discount,telegram_chat_id")
            .in_("user_id", ids)
            .not_.is_("telegram_chat_id", "null")
            .execute()
        )
    except Exception as e:
        logger.error("user_preferences J+7 lookup failed: %s", e)
        return []
    linked_prefs = {p["user_id"]: p for p in (prefs.data or [])}
    if not linked_prefs:
        return []
    # Among the linked ones, exclude those who have already received any alert
    try:
        sa = (
            db.table("sent_alerts")
            .select("user_id")
            .in_("user_id", list(linked_prefs.keys()))
            .execute()
        )
    except Exception as e:
        logger.error("sent_alerts J+7 lookup failed: %s", e)
        return []
    have_received = {r["user_id"] for r in (sa.data or []) if r.get("user_id")}
    result = []
    for u_row in users:
        if u_row["id"] not in linked_prefs:
            continue
        if u_row["id"] in have_received:
            continue
        pref = linked_prefs[u_row["id"]]
        result.append({
            **u_row,
            "airport_codes": pref.get("airport_codes") or [],
            "min_discount": pref.get("min_discount"),
        })
    return result


# ── Public entry point used by the daily cron ──────────────────────────────


async def send_onboarding_emails_once() -> dict:
    """Run one pass of the J+1 and J+7 cohorts. Returns counts so the
    caller can log or send a summary to the admin chat."""
    counts = {
        "j1_relance_sent": 0,
        "j1_relance_skipped": 0,
        "j7_inactivity_sent": 0,
        "j7_inactivity_skipped": 0,
    }

    # J+1
    for user in _users_unlinked_telegram_24h_to_48h():
        uid = user["id"]
        if _already_sent(uid, "j1_relance"):
            counts["j1_relance_skipped"] += 1
            continue
        ok = await _send_brevo_template(
            to_email=user["email"],
            template_id=settings.BREVO_RELANCE_TELEGRAM_TEMPLATE_ID,
            params={
                "DEEP_LINK": "https://globegenius.app/profile",
            },
        )
        if ok:
            _mark_sent(uid, "j1_relance")
            counts["j1_relance_sent"] += 1
        else:
            counts["j1_relance_skipped"] += 1

    # J+7
    for user in _users_linked_telegram_but_no_alerts_7d():
        uid = user["id"]
        if _already_sent(uid, "j7_inactivity"):
            counts["j7_inactivity_skipped"] += 1
            continue
        airports = ", ".join(user.get("airport_codes") or []) or "CDG"
        min_disc = user.get("min_discount") or 40
        ok = await _send_brevo_template(
            to_email=user["email"],
            template_id=settings.BREVO_INACTIVITY_TEMPLATE_ID,
            params={
                "AIRPORT_CODES": airports,
                "MIN_DISCOUNT": min_disc,
                "PROFILE_LINK": "https://globegenius.app/profile",
            },
        )
        if ok:
            _mark_sent(uid, "j7_inactivity")
            counts["j7_inactivity_sent"] += 1
        else:
            counts["j7_inactivity_skipped"] += 1

    return counts
