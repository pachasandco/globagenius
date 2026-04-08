import asyncio
import secrets
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import bcrypt
from app.db import db
from app.config import settings
from app.notifications.welcome_email import send_welcome_email as _send_welcome_email

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_AIRPORTS = settings.MVP_AIRPORTS
VALID_OFFER_TYPES = ["package", "flight", "accommodation"]


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


class SignupRequest(BaseModel):
    email: str
    password: str


class PreferencesRequest(BaseModel):
    airport_codes: list[str]
    offer_types: list[str]
    min_discount: int = 40
    max_budget: int | None = None
    preferred_destinations: list[str] | None = None


class TelegramConnectRequest(BaseModel):
    user_id: str


@router.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/api/status")
def status():
    if not db:
        return {"status": "no_database"}

    logs = (
        db.table("scrape_logs")
        .select("*")
        .order("started_at", desc=True)
        .limit(10)
        .execute()
    )

    active_packages = db.table("packages").select("id", count="exact").eq("status", "active").execute()
    active_baselines = db.table("price_baselines").select("id", count="exact").execute()

    return {
        "status": "ok",
        "recent_scrapes": logs.data or [],
        "active_packages": active_packages.count or 0,
        "active_baselines": active_baselines.count or 0,
    }


@router.get("/api/packages")
def list_packages(min_score: int = 0, limit: int = 20, plan: str = "free"):
    """List packages. plan=free returns 20-39% deals, plan=premium returns 40%+ deals."""
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    query = db.table("packages").select("*").eq("status", "active").gte("score", min_score)

    if plan == "free":
        query = query.gte("discount_pct", 20).lt("discount_pct", 40)
    else:
        query = query.gte("discount_pct", 40)

    resp = query.order("score", desc=True).limit(limit).execute()
    return {"packages": resp.data or [], "plan": plan}


@router.get("/api/packages/{package_id}")
def get_package(package_id: str):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    resp = db.table("packages").select("*").eq("id", package_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Package not found")
    return resp.data[0]


@router.get("/api/qualified-items")
def list_qualified_items(type_filter: str = "", limit: int = 20):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    query = db.table("qualified_items").select("*").eq("status", "active")
    if type_filter:
        query = query.eq("type", type_filter)
    resp = query.order("score", desc=True).limit(limit).execute()
    return {"items": resp.data or []}


@router.post("/api/trigger/{job_name}")
async def trigger_job(job_name: str):
    from app.scheduler.jobs import (
        job_scrape_flights,
        job_scrape_accommodations,
        job_recalculate_baselines,
        job_expire_stale_data,
    )

    jobs = {
        "scrape_flights": job_scrape_flights,
        "scrape_accommodations": job_scrape_accommodations,
        "recalculate_baselines": job_recalculate_baselines,
        "expire_stale_data": job_expire_stale_data,
    }

    if job_name not in jobs:
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_name}")

    asyncio.create_task(jobs[job_name]())
    return {"status": "triggered", "job": job_name}


# ─── AUTH ───

@router.post("/api/auth/signup")
async def signup(req: SignupRequest):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 6 caracteres")

    existing = db.table("users").select("id").eq("email", req.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Cet email est deja utilise")

    user = db.table("users").insert({
        "email": req.email,
        "password_hash": _hash_password(req.password),
    }).execute()
    if not user.data:
        raise HTTPException(status_code=500, detail="Erreur lors de la creation du compte")

    user_id = user.data[0]["id"]

    db.table("user_preferences").insert({
        "user_id": user_id,
        "airport_codes": ["CDG"],
        "offer_types": ["package", "flight", "accommodation"],
    }).execute()

    # Send welcome email (fire and forget)
    try:
        await _send_welcome_email(req.email)
    except Exception as e:
        logger.warning(f"Failed to send welcome email: {e}")

    return {"user_id": user_id, "email": req.email}


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/api/auth/login")
def login(req: LoginRequest):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    user = db.table("users").select("*").eq("email", req.email).execute()
    if not user.data:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    if not _verify_password(req.password, user.data[0]["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    return {"user_id": user.data[0]["id"], "email": user.data[0]["email"]}


# ─── PREFERENCES ───

@router.get("/api/users/{user_id}/preferences")
def get_preferences(user_id: str):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    prefs = db.table("user_preferences").select("*").eq("user_id", user_id).execute()
    if not prefs.data:
        raise HTTPException(status_code=404, detail="Preferences not found")

    return prefs.data[0]


@router.put("/api/users/{user_id}/preferences")
def update_preferences(user_id: str, req: PreferencesRequest):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    for ac in req.airport_codes:
        if ac not in VALID_AIRPORTS:
            raise HTTPException(status_code=400, detail=f"Invalid airport '{ac}'. Valid: {VALID_AIRPORTS}")

    for ot in req.offer_types:
        if ot not in VALID_OFFER_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid offer type. Valid: {VALID_OFFER_TYPES}")

    update_data = {
        "airport_codes": req.airport_codes,
        "offer_types": req.offer_types,
        "min_discount": req.min_discount,
        "max_budget": req.max_budget,
        "preferred_destinations": req.preferred_destinations or [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    resp = db.table("user_preferences").update(update_data).eq("user_id", user_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    return resp.data[0]


# ─── TELEGRAM CONNECT ───

@router.post("/api/users/{user_id}/telegram/generate-link")
def generate_telegram_link(user_id: str):
    """Generate a unique link for user to connect their Telegram."""
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    token = secrets.token_urlsafe(16)

    # Store token temporarily in preferences
    db.table("user_preferences").update({
        "telegram_connect_token": token,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", user_id).execute()

    bot_username = "Globegenius_bot"
    # Update webhook URL to use custom domain
    webhook_url = "https://api.globegenius.app/api/telegram/webhook"
    deep_link = f"https://t.me/{bot_username}?start={token}"

    return {"link": deep_link, "token": token}


@router.post("/api/telegram/setup-webhook")
async def setup_telegram_webhook():
    """Set Telegram webhook to point to our API."""
    import httpx
    webhook_url = "https://api.globegenius.app/api/telegram/webhook"
    telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"

    async with httpx.AsyncClient() as client:
        resp = await client.post(telegram_url, json={"url": webhook_url})
        return resp.json()


@router.get("/api/users/{user_id}/telegram/status")
def telegram_status(user_id: str):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    prefs = db.table("user_preferences").select("telegram_connected, telegram_chat_id").eq("user_id", user_id).execute()
    if not prefs.data:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "connected": prefs.data[0].get("telegram_connected", False),
        "chat_id": prefs.data[0].get("telegram_chat_id"),
    }


# ─── ARTICLES ───

@router.get("/api/articles")
def list_articles():
    """List all generated destination articles."""
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    resp = db.table("articles").select("*").order("created_at", desc=True).execute()
    return {"articles": resp.data or []}


@router.get("/api/articles/{slug}")
def get_article(slug: str):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    resp = db.table("articles").select("*").eq("slug", slug).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Article not found")
    return resp.data[0]


@router.post("/api/articles/generate")
async def generate_article_endpoint(destination: str, country: str):
    """Generate a new destination article via AI."""
    from app.agents.article_writer import generate_article

    article = generate_article(destination, country)
    if not article:
        raise HTTPException(status_code=500, detail="Failed to generate article")

    slug = destination.lower().replace(" ", "-").replace("'", "")
    article["slug"] = slug

    if db:
        db.table("articles").upsert(article, on_conflict="slug").execute()

    return article


# ─── TRAVEL PLANNER ───

class PlannerMessage(BaseModel):
    message: str


@router.post("/api/planner/{user_id}/chat")
async def planner_chat(user_id: str, req: PlannerMessage):
    """Chat with the travel planner agent."""
    from app.agents.travel_planner import get_or_create_session
    session = get_or_create_session(user_id)
    response = session.chat(req.message)
    return response or {"type": "error", "message": "Pas de reponse"}


@router.post("/api/planner/{user_id}/reset")
async def planner_reset(user_id: str):
    """Reset the planner conversation."""
    from app.agents.travel_planner import reset_session
    reset_session(user_id)
    return {"status": "reset"}
