import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request
from app.db import db
from app.config import settings

logger = logging.getLogger(__name__)

bot_router = APIRouter()


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

    if data.startswith("pause:"):
        user_id = data[len("pause:"):]
        await _pause_alerts(bot, callback_id, chat_id, user_id)

    elif data.startswith("unsub:"):
        user_id = data[len("unsub:"):]
        await _unsubscribe(bot, callback_id, chat_id, user_id)

    else:
        # Unknown callback — just ack it silently
        try:
            await bot.answer_callback_query(callback_query_id=callback_id)
        except Exception:
            pass


async def _pause_alerts(bot, callback_id: str, chat_id: int, user_id: str):
    """Mute alerts for 24h and confirm to the user."""
    pause_until = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    try:
        db.table("user_preferences").update({
            "alerts_paused_until": pause_until,
        }).eq("user_id", user_id).execute()
        await bot.answer_callback_query(
            callback_query_id=callback_id,
            text="Alertes mises en pause pour 24h ⏸",
            show_alert=False,
        )
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "⏸ Alertes mises en pause pour 24h.\n\n"
                "Tu recevras à nouveau des deals demain. "
                f"Pour réactiver maintenant, va dans ton profil : "
                f"{settings.FRONTEND_URL}/profile"
            ),
        )
    except Exception as e:
        logger.warning(f"Failed to pause alerts for {user_id}: {e}")
        try:
            await bot.answer_callback_query(callback_query_id=callback_id, text="Erreur, réessaie.")
        except Exception:
            pass


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
