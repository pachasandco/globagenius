import asyncio
import json
import re
import secrets
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
import bcrypt
import jwt
from app.db import db
from app.config import settings
from app.notifications.welcome_email import send_welcome_email as _send_welcome_email

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)

VALID_AIRPORTS = settings.MVP_AIRPORTS
VALID_OFFER_TYPES = ["package", "flight", "accommodation"]
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Simple in-memory rate limiter
_rate_limits: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10  # max requests per window


def _check_rate_limit(key: str):
    now = datetime.now(timezone.utc).timestamp()
    if key not in _rate_limits:
        _rate_limits[key] = []
    _rate_limits[key] = [t for t in _rate_limits[key] if t > now - RATE_LIMIT_WINDOW]
    if len(_rate_limits[key]) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Trop de requetes. Reessayez dans une minute.")
    _rate_limits[key].append(now)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _create_jwt(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def _verify_jwt(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expire")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Extract and verify JWT from Authorization header."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentification requise")
    payload = _verify_jwt(credentials.credentials)
    return payload


def _require_admin(request: Request):
    """Check admin API key in X-Admin-Key header."""
    admin_key = request.headers.get("X-Admin-Key", "")
    if not settings.ADMIN_API_KEY:
        return  # No admin key configured = dev mode, allow all
    if admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Acces admin requis")


class SignupRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not EMAIL_REGEX.match(v):
            raise ValueError("Format email invalide")
        return v.lower().strip()


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


@router.get("/api/debug/data")
def debug_data(request: Request):
    """Debug endpoint: show sample data from each table. Admin only."""
    _require_admin(request)
    if not db:
        return {"error": "no db"}

    flights = db.table("raw_flights").select("origin, destination, departure_date, return_date, price, source").order("scraped_at", desc=True).limit(5).execute()
    accommodations = db.table("raw_accommodations").select("city, name, total_price, rating, check_in, check_out, source").order("scraped_at", desc=True).limit(5).execute()
    baselines = db.table("price_baselines").select("route_key, type, avg_price, std_dev, sample_count").limit(10).execute()

    # Check if any flight prices are below baseline
    diagnosis = []
    for f in (flights.data or []):
        route_key_1m = f"{f['origin']}-{f['destination']}-1m"
        route_key_3m = f"{f['origin']}-{f['destination']}-3m"
        bl = db.table("price_baselines").select("*").eq("route_key", route_key_1m).execute()
        if not bl.data:
            bl = db.table("price_baselines").select("*").eq("route_key", route_key_3m).execute()
        if bl.data:
            avg = bl.data[0]["avg_price"]
            std = bl.data[0]["std_dev"]
            price = f["price"]
            discount = round((avg - price) / avg * 100, 1) if avg > 0 else 0
            z = round((avg - price) / std, 2) if std > 0 else 0
            diagnosis.append({
                "route": f"{f['origin']}→{f['destination']}",
                "price": price,
                "baseline_avg": avg,
                "baseline_std": std,
                "discount_pct": discount,
                "z_score": z,
                "would_qualify": discount >= 20 and z >= 1.0,
            })

    # Check date matching between flights and accommodations
    flight_dates = set()
    for f in (flights.data or []):
        flight_dates.add((f["destination"], f["departure_date"], f["return_date"]))

    acc_dates = set()
    for a in (accommodations.data or []):
        acc_dates.add((a["city"], a["check_in"], a["check_out"]))

    return {
        "flights_sample": flights.data or [],
        "accommodations_sample": accommodations.data or [],
        "baselines_sample": baselines.data or [],
        "price_diagnosis": diagnosis,
        "flight_date_keys": [f"{d[0]} {d[1]}→{d[2]}" for d in list(flight_dates)[:10]],
        "accommodation_date_keys": [f"{d[0]} {d[1]}→{d[2]}" for d in list(acc_dates)[:10]],
    }


@router.get("/api/packages")
def list_packages(min_score: int = 0, limit: int = 20, plan: str = "free"):
    """List deals. free=vols seuls 20-39%, premium=packages vol+hotel (vol -40%+, hotel -20%+)."""
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    if plan == "premium":
        # Packages (vol+hotel) — premium only
        resp = (
            db.table("packages").select("*")
            .eq("status", "active")
            .gte("score", min_score)
            .order("score", desc=True)
            .limit(limit)
            .execute()
        )
        return {"packages": resp.data or [], "plan": plan}
    else:
        # Vols seuls (-20 a -39%) — free plan
        resp = (
            db.table("qualified_items").select("*")
            .eq("status", "active")
            .eq("type", "flight")
            .gte("discount_pct", 20)
            .lt("discount_pct", 40)
            .order("score", desc=True)
            .limit(limit)
            .execute()
        )
        return {"items": resp.data or [], "plan": plan}


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
async def trigger_job(job_name: str, request: Request):
    _require_admin(request)
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
async def signup(req: SignupRequest, request: Request):
    _check_rate_limit(f"signup:{request.client.host if request.client else 'unknown'}")
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

    token = _create_jwt(user_id, req.email)
    return {"user_id": user_id, "email": req.email, "token": token}


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/api/auth/login")
def login(req: LoginRequest, request: Request):
    _check_rate_limit(f"login:{request.client.host if request.client else 'unknown'}")
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    user = db.table("users").select("*").eq("email", req.email.lower().strip()).execute()
    if not user.data:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    if not _verify_password(req.password, user.data[0]["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    user_id = user.data[0]["id"]
    email = user.data[0]["email"]
    token = _create_jwt(user_id, email)
    return {"user_id": user_id, "email": email, "token": token}


# ─── PREFERENCES ───

@router.get("/api/users/{user_id}/preferences")
def get_preferences(user_id: str, user: dict = Depends(get_current_user)):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    prefs = db.table("user_preferences").select("*").eq("user_id", user_id).execute()
    if not prefs.data:
        raise HTTPException(status_code=404, detail="Preferences not found")

    return prefs.data[0]


@router.put("/api/users/{user_id}/preferences")
def update_preferences(user_id: str, req: PreferencesRequest, user: dict = Depends(get_current_user)):
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
def generate_telegram_link(user_id: str, user: dict = Depends(get_current_user)):
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
    webhook_url = "https://globagenius-production-b887.up.railway.app/api/telegram/webhook"
    deep_link = f"https://t.me/{bot_username}?start={token}"

    return {"link": deep_link, "token": token}


@router.post("/api/telegram/setup-webhook")
async def setup_telegram_webhook(request: Request):
    _require_admin(request)
    """Set Telegram webhook to point to our API."""
    import httpx
    webhook_url = "https://globagenius-production-b887.up.railway.app/api/telegram/webhook"
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
async def generate_article_endpoint(destination: str, country: str, request: Request):
    _require_admin(request)
    """Generate a new destination article via AI."""
    from app.agents.article_writer import generate_article

    try:
        article = generate_article(destination, country)
    except Exception as e:
        logger.error(f"Article generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)[:200]}")

    if not article:
        raise HTTPException(status_code=500, detail="Failed to generate article — LLM returned no data")

    slug = destination.lower().replace(" ", "-").replace("'", "")

    # Filter to only columns that exist in the DB
    db_article = {
        "slug": slug,
        "destination": article.get("destination", destination),
        "country": article.get("country", country),
        "title": article.get("title", ""),
        "subtitle": article.get("subtitle", ""),
        "intro": article.get("intro", ""),
        "sections": json.dumps(article.get("sections", [])),
        "best_time": article.get("best_time", ""),
        "budget_tip": article.get("budget_tip", ""),
        "tags": article.get("tags", []),
        "cover_photo": article.get("cover_photo", ""),
        "photo_query": article.get("photo_query", ""),
        "generated_at": article.get("generated_at"),
    }

    if db:
        try:
            db.table("articles").upsert(db_article, on_conflict="slug").execute()
        except Exception as e:
            logger.error(f"Failed to save article: {e}")

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
