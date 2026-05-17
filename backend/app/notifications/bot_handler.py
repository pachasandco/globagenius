import logging
import unicodedata
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request
from app.db import db
from app.config import settings

PAUSE_SENTINEL = "2099-01-01T00:00:00+00:00"  # far-future = paused indefinitely

logger = logging.getLogger(__name__)

bot_router = APIRouter()


# ─── Destination helpers ───
#
# Source of truth for the IATA → human name mapping is the `articles`
# table (every guide we've generated has an iata + destination column).
# That gives us ~80+ destinations and avoids duplicating a static list
# in the backend. Cached in-process for the lifetime of the worker since
# it changes only when a new guide is published (not hot data).

_destinations_cache: list[dict] | None = None
_destinations_cache_at: datetime | None = None
_DESTINATIONS_TTL = timedelta(minutes=15)


def _load_destinations() -> list[dict]:
    """Return [{iata, name}] for all destinations with a guide. Cached 15min."""
    global _destinations_cache, _destinations_cache_at
    now = datetime.now(timezone.utc)
    if (
        _destinations_cache is not None
        and _destinations_cache_at is not None
        and now - _destinations_cache_at < _DESTINATIONS_TTL
    ):
        return _destinations_cache

    try:
        r = (
            db.table("articles")
            .select("iata,destination")
            .not_.is_("iata", "null")
            .execute()
        )
        rows = r.data or []
        # Dedup by iata (some legacy rows may overlap).
        seen: set[str] = set()
        out: list[dict] = []
        for row in rows:
            iata = (row.get("iata") or "").upper().strip()
            name = (row.get("destination") or "").strip()
            if not iata or iata in seen or not name:
                continue
            seen.add(iata)
            out.append({"iata": iata, "name": name})
        out.sort(key=lambda d: d["name"])
        _destinations_cache = out
        _destinations_cache_at = now
        return out
    except Exception as e:
        logger.warning(f"Failed to load destinations: {e}")
        return _destinations_cache or []


def _normalize(text: str) -> str:
    """Lowercase and strip accents so 'Lisbonne' matches 'lisbonne' or 'lisbone'."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def _search_destinations(query: str, limit: int = 5) -> list[dict]:
    """Substring + accent-insensitive search over destinations."""
    q = _normalize(query)
    if not q or len(q) < 2:
        return []
    results: list[tuple[int, dict]] = []
    for d in _load_destinations():
        name_norm = _normalize(d["name"])
        iata_norm = d["iata"].lower()
        # Rank: exact IATA > startswith name > substring
        if iata_norm == q:
            results.append((0, d))
        elif name_norm.startswith(q):
            results.append((1, d))
        elif q in name_norm:
            results.append((2, d))
    results.sort(key=lambda r: (r[0], r[1]["name"]))
    return [d for _, d in results[:limit]]


def _iata_to_name(iata: str) -> str:
    """Best-effort reverse lookup. Falls back to the IATA code itself."""
    iata_up = (iata or "").upper().strip()
    for d in _load_destinations():
        if d["iata"] == iata_up:
            return d["name"]
    return iata_up


def _user_id_from_chat(chat_id: int) -> str | None:
    """Find the linked user_id for a Telegram chat. None if not linked."""
    try:
        r = (
            db.table("user_preferences")
            .select("user_id")
            .eq("telegram_chat_id", chat_id)
            .limit(1)
            .execute()
        )
        return r.data[0]["user_id"] if r.data else None
    except Exception as e:
        logger.warning(f"Failed to look up user_id for chat {chat_id}: {e}")
        return None


@bot_router.post("/api/telegram/webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram messages (webhook mode)."""
    from app.config import settings
    if settings.TELEGRAM_WEBHOOK_SECRET:
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if header_secret != settings.TELEGRAM_WEBHOOK_SECRET:
            return {"ok": False, "error": "unauthorized"}

    if not db:
        return {"ok": True}

    data = await request.json()

    # Inline-button callback
    callback = data.get("callback_query")
    if callback:
        await _handle_callback(callback)
        return {"ok": True}

    message = data.get("message", {})
    text = message.get("text", "")
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return {"ok": True}

    # Handle /start command
    if text.startswith("/start"):
        parts = text.split(" ", 1)
        token = parts[1] if len(parts) > 1 else None

        if token:
            await _link_account(chat_id, token, chat)
        else:
            await _send_welcome(chat_id)

    elif text == "/help":
        await _send_help(chat_id)

    elif text == "/status":
        await _send_status(chat_id)

    elif text.startswith("/destinations") or text.startswith("/destination"):
        await _send_destinations_menu(chat_id)

    elif text.startswith("/pause"):
        await _send_pause_menu(chat_id)

    elif text and not text.startswith("/"):
        # Free-text search: the user typed a destination name (e.g.
        # "lisbonne", "rome"). We treat this as a destination lookup
        # and reply with toggle buttons.
        await _send_search_results(chat_id, text)

    return {"ok": True}


async def _handle_callback(callback: dict):
    """Dispatch inline-keyboard button presses."""
    from app.notifications.telegram import _get_bot

    bot = _get_bot()
    callback_id = callback.get("id")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    data = callback.get("data", "")

    if not bot or not callback_id or not chat_id:
        return

    # Legacy (pre-v10) — kept for in-flight notifications still showing
    # the old "pause:" button. Treat it as the new "pause_menu:" entry
    # point so users see the same sub-menu.
    if data.startswith("pause:"):
        user_id = data[len("pause:"):]
        await _open_pause_menu(bot, callback_id, chat_id, user_id)

    elif data.startswith("pause_menu:"):
        user_id = data[len("pause_menu:"):]
        await _open_pause_menu(bot, callback_id, chat_id, user_id)

    elif data.startswith("pause_7:"):
        user_id = data[len("pause_7:"):]
        await _set_pause(bot, callback_id, chat_id, user_id, days=7)

    elif data.startswith("pause_30:"):
        user_id = data[len("pause_30:"):]
        await _set_pause(bot, callback_id, chat_id, user_id, days=30)

    elif data.startswith("pause_inf:"):
        user_id = data[len("pause_inf:"):]
        await _set_pause(bot, callback_id, chat_id, user_id, days=None)

    elif data.startswith("resume:"):
        user_id = data[len("resume:"):]
        await _resume_alerts(bot, callback_id, chat_id, user_id)

    elif data.startswith("block:"):
        # Format: block:{user_id}:{iata}
        rest = data[len("block:"):]
        parts = rest.split(":", 1)
        if len(parts) == 2:
            await _block_destination(bot, callback_id, chat_id, parts[0], parts[1])

    elif data.startswith("unblock:"):
        rest = data[len("unblock:"):]
        parts = rest.split(":", 1)
        if len(parts) == 2:
            await _unblock_destination(bot, callback_id, chat_id, parts[0], parts[1])

    elif data.startswith("unblock_all:"):
        user_id = data[len("unblock_all:"):]
        await _unblock_all(bot, callback_id, chat_id, user_id)

    elif data.startswith("unsub:"):
        user_id = data[len("unsub:"):]
        await _unsubscribe(bot, callback_id, chat_id, user_id)

    elif data.startswith("feedback:"):
        # Format: feedback:{good|bad|late}:{message_id}
        rest = data[len("feedback:"):]
        parts = rest.split(":", 1)
        if len(parts) == 2:
            await _record_feedback(bot, callback_id, chat_id, parts[0], parts[1])

    else:
        # Unknown callback — just ack it silently
        try:
            await bot.answer_callback_query(callback_query_id=callback_id)
        except Exception:
            pass


def _is_currently_paused(user_id: str) -> bool:
    """Read alerts_paused_until from DB and decide if it is in the future."""
    try:
        row = db.table("user_preferences").select("alerts_paused_until").eq("user_id", user_id).execute()
        current = (row.data[0].get("alerts_paused_until") if row.data else None)
        if not current:
            return False
        exp = datetime.fromisoformat(current.replace("Z", "+00:00"))
        return exp > datetime.now(timezone.utc)
    except Exception:
        return False


async def _open_pause_menu(bot, callback_id: str, chat_id: int, user_id: str):
    """Show the pause sub-menu (7d / 30d / indefinite / cancel) — or
    the resume button if alerts are already paused."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    try:
        await bot.answer_callback_query(callback_query_id=callback_id)
    except Exception:
        pass

    if _is_currently_paused(user_id):
        await bot.send_message(
            chat_id=chat_id,
            text="⏸ Tes alertes sont actuellement en pause.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("▶️ Reprendre les alertes", callback_data=f"resume:{user_id}"),
            ]]),
        )
        return

    await bot.send_message(
        chat_id=chat_id,
        text="⏸ Pour combien de temps mettre les alertes en pause ?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏸ Pause 7 jours", callback_data=f"pause_7:{user_id}")],
            [InlineKeyboardButton("⏸ Pause 30 jours", callback_data=f"pause_30:{user_id}")],
            [InlineKeyboardButton("🛑 Tout arrêter (indéfini)", callback_data=f"pause_inf:{user_id}")],
        ]),
    )


async def _set_pause(bot, callback_id: str, chat_id: int, user_id: str, days: int | None):
    """Pause alerts for the given number of days, or indefinitely if days is None."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    if days is None:
        until_iso = PAUSE_SENTINEL
        label_user = "indéfiniment"
        label_short = "indéfinie"
    else:
        until_iso = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        label_user = f"pendant {days} jours"
        label_short = f"{days} jours"

    try:
        db.table("user_preferences").update({
            "alerts_paused_until": until_iso,
        }).eq("user_id", user_id).execute()
        try:
            await bot.answer_callback_query(
                callback_query_id=callback_id,
                text=f"Pause {label_short} ⏸",
            )
        except Exception:
            pass
        await bot.send_message(
            chat_id=chat_id,
            text=f"⏸ Alertes mises en pause {label_user}. Tu peux les réactiver d'un clic ci-dessous.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("▶️ Reprendre les alertes", callback_data=f"resume:{user_id}"),
            ]]),
        )
    except Exception as e:
        logger.warning(f"Failed to set pause for {user_id}: {e}")
        try:
            await bot.answer_callback_query(callback_query_id=callback_id, text="Erreur, réessaie.")
        except Exception:
            pass


async def _resume_alerts(bot, callback_id: str, chat_id: int, user_id: str):
    """Cancel any active pause."""
    try:
        db.table("user_preferences").update({
            "alerts_paused_until": None,
        }).eq("user_id", user_id).execute()
        try:
            await bot.answer_callback_query(
                callback_query_id=callback_id,
                text="Alertes réactivées ▶️",
            )
        except Exception:
            pass
        await bot.send_message(
            chat_id=chat_id,
            text="▶️ Alertes réactivées. Tu recevras à nouveau les prochains deals.",
        )
    except Exception as e:
        logger.warning(f"Failed to resume alerts for {user_id}: {e}")
        try:
            await bot.answer_callback_query(callback_query_id=callback_id, text="Erreur, réessaie.")
        except Exception:
            pass


# ─── Destination block / unblock ───

def _get_blocked(user_id: str) -> list[str]:
    """Return the list of blocked IATA codes for this user, uppercased."""
    try:
        r = (
            db.table("user_preferences")
            .select("blocked_destinations")
            .eq("user_id", user_id)
            .execute()
        )
        raw = r.data[0].get("blocked_destinations") if r.data else None
        if not raw:
            return []
        return [str(c).upper().strip() for c in raw if c]
    except Exception as e:
        logger.warning(f"Failed to read blocked_destinations for {user_id}: {e}")
        return []


def _save_blocked(user_id: str, codes: list[str]) -> None:
    """Overwrite blocked_destinations with a deduped, uppercase list."""
    deduped = sorted({c.upper().strip() for c in codes if c})
    db.table("user_preferences").update({
        "blocked_destinations": deduped,
    }).eq("user_id", user_id).execute()


async def _block_destination(bot, callback_id: str, chat_id: int, user_id: str, iata: str):
    """Add an IATA code to blocked_destinations. Idempotent."""
    iata_up = (iata or "").upper().strip()
    name = _iata_to_name(iata_up)
    try:
        blocked = _get_blocked(user_id)
        if iata_up in blocked:
            try:
                await bot.answer_callback_query(
                    callback_query_id=callback_id,
                    text=f"{name} est déjà masquée",
                )
            except Exception:
                pass
            return
        blocked.append(iata_up)
        _save_blocked(user_id, blocked)
        try:
            await bot.answer_callback_query(
                callback_query_id=callback_id,
                text=f"🚫 {name} masquée",
            )
        except Exception:
            pass
        # No follow-up message: the toast is enough and avoids spamming the chat.
    except Exception as e:
        logger.warning(f"Failed to block {iata_up} for {user_id}: {e}")
        try:
            await bot.answer_callback_query(callback_query_id=callback_id, text="Erreur, réessaie.")
        except Exception:
            pass


async def _unblock_destination(bot, callback_id: str, chat_id: int, user_id: str, iata: str):
    """Remove an IATA code from blocked_destinations."""
    iata_up = (iata or "").upper().strip()
    name = _iata_to_name(iata_up)
    try:
        blocked = [c for c in _get_blocked(user_id) if c != iata_up]
        _save_blocked(user_id, blocked)
        try:
            await bot.answer_callback_query(
                callback_query_id=callback_id,
                text=f"✓ {name} réactivée",
            )
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Failed to unblock {iata_up} for {user_id}: {e}")
        try:
            await bot.answer_callback_query(callback_query_id=callback_id, text="Erreur, réessaie.")
        except Exception:
            pass


async def _unblock_all(bot, callback_id: str, chat_id: int, user_id: str):
    """Clear the entire blocked_destinations list."""
    try:
        _save_blocked(user_id, [])
        try:
            await bot.answer_callback_query(
                callback_query_id=callback_id,
                text="Toutes les destinations réactivées ✓",
            )
        except Exception:
            pass
        await bot.send_message(
            chat_id=chat_id,
            text="✓ Toutes tes destinations sont à nouveau actives.",
        )
    except Exception as e:
        logger.warning(f"Failed to unblock_all for {user_id}: {e}")
        try:
            await bot.answer_callback_query(callback_query_id=callback_id, text="Erreur, réessaie.")
        except Exception:
            pass


# ─── /destinations menu + free-text search ───

async def _send_destinations_menu(chat_id: int):
    """Reply to /destinations with the list of blocked destinations and
    a prompt to search for one to block/unblock."""
    from app.notifications.telegram import _get_bot
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    bot = _get_bot()
    if not bot:
        return

    user_id = _user_id_from_chat(chat_id)
    if not user_id:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "Tu n'es pas encore connecté à un compte Globe Genius.\n"
                f"Lie ton compte depuis : {settings.FRONTEND_URL}/profile"
            ),
        )
        return

    blocked_codes = _get_blocked(user_id)

    if blocked_codes:
        # One toggle button per blocked destination + a "clear all" shortcut.
        rows: list[list] = [
            [InlineKeyboardButton(f"🚫 {_iata_to_name(c)} — débloquer", callback_data=f"unblock:{user_id}:{c}")]
            for c in blocked_codes[:20]  # safety cap; Telegram allows up to 100
        ]
        if len(blocked_codes) > 1:
            rows.append([InlineKeyboardButton("🔄 Tout débloquer", callback_data=f"unblock_all:{user_id}")])
        text = (
            f"🌍 *Tes destinations bloquées* ({len(blocked_codes)})\n\n"
            "Clique sur une destination ci-dessous pour la réactiver.\n\n"
            "Pour bloquer une autre destination, *tape simplement son nom* "
            "(ex : `lisbonne`, `rome`, `tokyo`)."
        )
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(rows),
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🌍 *Tes destinations*\n\n"
                "Aucune destination bloquée. Tu reçois les alertes pour toutes les destinations.\n\n"
                "Pour en bloquer une, *tape son nom* (ex : `lisbonne`, `rome`, `tokyo`)."
            ),
            parse_mode="Markdown",
        )


async def _send_pause_menu(chat_id: int):
    """Reply to the /pause command with the same sub-menu as the inline button."""
    from app.notifications.telegram import _get_bot
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    bot = _get_bot()
    if not bot:
        return

    user_id = _user_id_from_chat(chat_id)
    if not user_id:
        await bot.send_message(
            chat_id=chat_id,
            text=f"Compte Telegram non lié. Connecte-toi sur {settings.FRONTEND_URL}/profile.",
        )
        return

    if _is_currently_paused(user_id):
        await bot.send_message(
            chat_id=chat_id,
            text="⏸ Tes alertes sont actuellement en pause.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("▶️ Reprendre les alertes", callback_data=f"resume:{user_id}"),
            ]]),
        )
        return

    await bot.send_message(
        chat_id=chat_id,
        text="⏸ Pour combien de temps mettre les alertes en pause ?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏸ Pause 7 jours", callback_data=f"pause_7:{user_id}")],
            [InlineKeyboardButton("⏸ Pause 30 jours", callback_data=f"pause_30:{user_id}")],
            [InlineKeyboardButton("🛑 Tout arrêter (indéfini)", callback_data=f"pause_inf:{user_id}")],
        ]),
    )


async def _send_search_results(chat_id: int, query: str):
    """When the user types free text (not a command), treat it as a
    destination search and reply with toggle buttons for each match.
    Silently ignored for users who aren't linked yet — typing random
    text shouldn't ping unlinked users."""
    from app.notifications.telegram import _get_bot
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    bot = _get_bot()
    if not bot:
        return

    user_id = _user_id_from_chat(chat_id)
    if not user_id:
        return

    matches = _search_destinations(query, limit=6)
    if not matches:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"🔍 Aucune destination trouvée pour « {query[:40]} ».\n\n"
                "Essaie avec un autre nom (ex : `lisbonne`, `rome`, `tokyo`) "
                "ou tape /destinations pour voir tes blocages."
            ),
            parse_mode="Markdown",
        )
        return

    blocked = set(_get_blocked(user_id))
    rows: list[list] = []
    for d in matches:
        iata = d["iata"]
        name = d["name"]
        if iata in blocked:
            rows.append([InlineKeyboardButton(
                f"🚫 {name} — débloquer", callback_data=f"unblock:{user_id}:{iata}",
            )])
        else:
            rows.append([InlineKeyboardButton(
                f"✓ {name} — bloquer", callback_data=f"block:{user_id}:{iata}",
            )])

    await bot.send_message(
        chat_id=chat_id,
        text=f"🔍 Résultats pour « {query[:40]} » — clique pour bloquer/débloquer :",
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def _unsubscribe(bot, callback_id: str, chat_id: int, user_id: str):
    """Disconnect Telegram for this user and confirm."""
    try:
        db.table("user_preferences").update({
            "telegram_connected": False,
            "telegram_chat_id": None,
            "alerts_paused_until": None,
        }).eq("user_id", user_id).execute()
        await bot.answer_callback_query(
            callback_query_id=callback_id,
            text="Désabonnement effectué 🔕",
            show_alert=False,
        )
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🔕 Tu ne recevras plus d'alertes GlobeGenius.\n\n"
                "Pour te réabonner à tout moment, reconnecte ton compte depuis : "
                f"{settings.FRONTEND_URL}/profile"
            ),
        )
    except Exception as e:
        logger.warning(f"Failed to unsubscribe {user_id}: {e}")
        try:
            await bot.answer_callback_query(callback_query_id=callback_id, text="Erreur, réessaie.")
        except Exception:
            pass


# Map the short callback codes back to the DB enum values that the
# sent_alerts.feedback CHECK constraint enforces (migration 043).
_FEEDBACK_CODES = {"good": "good", "bad": "bad", "late": "too_late"}

# Toast confirmations — keep them short (≤ 50 chars for compact
# rendering). Acknowledge the feedback without over-promising
# behaviour change ("on resserre les seuils") — that's a separate
# tuning decision the operator makes after looking at the data.
_FEEDBACK_TOASTS = {
    "good": "✓ Merci, ça nous aide à affiner !",
    "bad": "✓ Note prise, retour utile.",
    "late": "✓ Bien noté, on accélère.",
}


async def _record_feedback(
    bot,
    callback_id: str,
    chat_id: int,
    feedback_code: str,
    message_id: str,
):
    """Persist a feedback click into sent_alerts.feedback for every
    row of the message identified by message_id. Last click wins —
    the column UPDATEs in place, so a user can change their mind
    (click 👍 then 👎) and the most recent verdict is kept.

    Fails silently with a generic toast if anything goes wrong —
    we never want a Telegram callback to surface a stack trace."""
    db_code = _FEEDBACK_CODES.get(feedback_code)
    if not db_code:
        try:
            await bot.answer_callback_query(callback_query_id=callback_id)
        except Exception:
            pass
        return
    try:
        db.table("sent_alerts").update({
            "feedback": db_code,
            "feedback_at": datetime.now(timezone.utc).isoformat(),
        }).eq("message_id", message_id).execute()
        await bot.answer_callback_query(
            callback_query_id=callback_id,
            text=_FEEDBACK_TOASTS.get(feedback_code, "✓ Merci."),
            show_alert=False,
        )
    except Exception as e:
        logger.warning(f"Feedback record failed for message_id={message_id} code={feedback_code}: {e}")
        try:
            await bot.answer_callback_query(callback_query_id=callback_id, text="Erreur, réessaie.")
        except Exception:
            pass


async def _link_account(chat_id: int, token: str, chat: dict):
    """Link Telegram chat to user account via token."""
    from app.notifications.telegram import _get_bot

    bot = _get_bot()
    if not bot:
        return

    # Find user by token
    prefs = (
        db.table("user_preferences")
        .select("user_id")
        .eq("telegram_connect_token", token)
        .execute()
    )

    if prefs.data:
        user_id = prefs.data[0]["user_id"]

        # Update preferences with Telegram info
        db.table("user_preferences").update({
            "telegram_chat_id": chat_id,
            "telegram_connected": True,
            "telegram_connect_token": None,
        }).eq("user_id", user_id).execute()

        # Also add to telegram_subscribers
        try:
            # Get airport codes
            user_prefs = db.table("user_preferences").select("airport_codes").eq("user_id", user_id).execute()
            airport = user_prefs.data[0]["airport_codes"][0] if user_prefs.data else "CDG"

            db.table("telegram_subscribers").upsert({
                "chat_id": chat_id,
                "airport_code": airport,
                "user_id": user_id,
            }, on_conflict="chat_id").execute()
        except Exception as e:
            logger.warning(f"Failed to upsert telegram_subscriber: {e}")

        name = chat.get("first_name", "")
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"✅ Compte lie avec succes !\n\n"
                f"Bonjour {name} ! Votre compte Globe Genius est maintenant connecte.\n\n"
                f"Vous recevrez ici :\n"
                f"🔥 Les alertes de deals (score ≥ 70) en temps reel\n"
                f"📬 Un digest quotidien des meilleurs deals a 8h\n\n"
                f"Commandes disponibles :\n"
                f"/status — Voir l'etat du pipeline\n"
                f"/help — Aide\n\n"
                f"Bon voyage ! ✈️"
            ),
        )
    else:
        await _send_welcome(chat_id)


async def _send_welcome(chat_id: int):
    from app.notifications.telegram import _get_bot

    bot = _get_bot()
    if not bot:
        return

    await bot.send_message(
        chat_id=chat_id,
        text=(
            "✈️ Bienvenue sur Globe Genius !\n\n"
            "Je detecte les packages voyage a prix casses "
            "(-40% minimum sur le marche).\n\n"
            "Pour recevoir des alertes personnalisees :\n"
            "1. Inscrivez-vous sur globegenius.com\n"
            "2. Configurez vos preferences (aeroports, destinations)\n"
            "3. Connectez votre compte Telegram depuis l'onboarding\n\n"
            "Commandes :\n"
            "/status — Etat du pipeline\n"
            "/help — Aide"
        ),
    )


async def _send_help(chat_id: int):
    from app.notifications.telegram import _get_bot

    bot = _get_bot()
    if not bot:
        return

    await bot.send_message(
        chat_id=chat_id,
        text=(
            "🆘 Aide Globe Genius\n\n"
            "/start — Demarrer / lier votre compte\n"
            "/status — Voir les stats du pipeline\n"
            "/help — Cette aide\n\n"
            "Les alertes sont envoyees automatiquement :\n"
            "🔥 Instantane si score ≥ 70\n"
            "📬 Digest quotidien a 8h si score ≥ 50\n\n"
            "Questions ? Contactez-nous sur globegenius.com"
        ),
    )


async def _send_status(chat_id: int):
    from app.notifications.telegram import _get_bot

    bot = _get_bot()
    if not bot:
        return

    # Get pipeline stats
    packages = db.table("packages").select("id", count="exact").eq("status", "active").execute()
    baselines = db.table("price_baselines").select("id", count="exact").execute()

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"📊 Etat du pipeline Globe Genius\n\n"
            f"📦 Packages actifs : {packages.count or 0}\n"
            f"📈 Baselines actives : {baselines.count or 0}\n\n"
            f"Le pipeline scrape les vols toutes les 2h "
            f"et les hebergements toutes les 4h."
        ),
    )
