import asyncio
import json
import re
import secrets
import logging
import stripe
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


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """Optional JWT verification: returns None if no token or invalid token,
    instead of raising. Used by endpoints that have public + private modes."""
    if not credentials:
        return None
    try:
        return _verify_jwt(credentials.credentials)
    except HTTPException:
        return None


def _is_premium_user(user: dict | None) -> bool:
    """Check if a user dict maps to a premium subscription.
    Delegates to _get_user_tier which checks premium_grants first,
    then stripe_customer_id — single source of truth."""
    if not user:
        return False
    user_id = user.get("user_id") or user.get("sub")
    return _get_user_tier(user_id) == "premium"


def _get_user_tier(user_id: str | None) -> str:
    """Return 'premium' or 'free' for a user.

    Priority 1: active premium_grants row (manual admin grant, can have expiry)
    Priority 2: stripe_customer_id on user_preferences (Stripe subscriber)
    Fallback: 'free'
    """
    if not user_id or not db:
        return "free"
    # Priority 1: manual admin grant
    try:
        grant_resp = (
            db.table("premium_grants")
            .select("expires_at,revoked")
            .eq("user_id", user_id)
            .eq("revoked", False)
            .limit(1)
            .execute()
        )
        if grant_resp.data:
            expires_at = grant_resp.data[0].get("expires_at")
            if not expires_at:
                return "premium"
            try:
                exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if exp > datetime.now(timezone.utc):
                    return "premium"
            except Exception:
                pass
    except Exception:
        pass
    # Priority 2: stripe subscription (customer_id alone is not enough —
    # a user may have started checkout without completing payment)
    try:
        row = (
            db.table("user_preferences")
            .select("stripe_customer_id,stripe_subscription_id")
            .eq("user_id", user_id)
            .execute()
        )
        if (
            row.data
            and row.data[0].get("stripe_customer_id")
            and row.data[0].get("stripe_subscription_id")
        ):
            return "premium"
    except Exception:
        pass
    return "free"


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

    @field_validator("min_discount")
    @classmethod
    def validate_min_discount(cls, v: int) -> int:
        allowed = {20, 30, 40, 50, 60}
        if v not in allowed:
            raise ValueError(f"min_discount must be one of {sorted(allowed)}")
        return v


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


@router.get("/api/history/stats")
def history_stats(request: Request):
    """Price history statistics — admin only."""
    _require_admin(request)
    if not db:
        return {"error": "no db"}

    total_flights = db.table("raw_flights").select("id", count="exact").execute()
    total_hotels = db.table("raw_accommodations").select("id", count="exact").execute()
    total_baselines = db.table("price_baselines").select("id", count="exact").execute()
    total_packages = db.table("packages").select("id", count="exact").execute()
    total_qualified = db.table("qualified_items").select("id", count="exact").execute()

    # Distinct routes
    routes = db.table("raw_flights").select("origin, destination").execute()
    unique_routes = set()
    for r in (routes.data or []):
        unique_routes.add(f"{r['origin']}-{r['destination']}")

    # Distinct cities
    cities = db.table("raw_accommodations").select("city").execute()
    unique_cities = {c["city"] for c in (cities.data or [])}

    return {
        "total_flights": total_flights.count or 0,
        "total_accommodations": total_hotels.count or 0,
        "total_baselines": total_baselines.count or 0,
        "total_packages": total_packages.count or 0,
        "total_qualified_items": total_qualified.count or 0,
        "unique_routes": len(unique_routes),
        "unique_cities": len(unique_cities),
        "routes": sorted(list(unique_routes))[:30],
        "cities": sorted(list(unique_cities)),
    }


@router.get("/api/history/prices")
def price_history(request: Request, origin: str = "", destination: str = "", limit: int = 50):
    """Get price history for a specific route — admin only."""
    _require_admin(request)
    if not db:
        return {"error": "no db"}

    query = db.table("raw_flights").select("origin, destination, departure_date, return_date, price, airline, scraped_at").order("scraped_at", desc=True).limit(limit)
    if origin:
        query = query.eq("origin", origin)
    if destination:
        query = query.eq("destination", destination)

    resp = query.execute()
    return {"prices": resp.data or [], "count": len(resp.data or [])}


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
def list_packages(
    min_score: int = 0,
    limit: int = 20,
    plan: str = "free",
    min_discount: int = 0,
    user: dict | None = Depends(get_optional_user),
):
    """List deals with paywall on sensitive fields.

    free  = qualified flight items 20-29% (vol seul, tier "free")
    premium = qualified flight items 30%+ (vol seul, tier "premium")

    Sensitive fields (price, baseline_price, source_url) are nullified
    server-side based on the caller's auth state:

    - Anonymous (no JWT)         → all fields nullified for all deals
    - Authenticated, non-premium → free deals visible in full,
                                   premium deals masked
    - Authenticated, premium     → all fields visible

    Non-sensitive fields (origin, destination, dates, airline, stops,
    discount_pct, tier, ...) are always returned so the UI can show a
    visible-but-locked card with a CTA to upgrade."""
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    if plan == "premium":
        plan_floor = 30
        discount_filter = ("gte", 30)
    else:
        plan_floor = 20
        discount_filter = ("range", 20, 30)  # 20 <= d < 30

    # A caller-supplied min_discount raises the floor (but never lowers it).
    effective_floor = max(min_discount, plan_floor)

    query = (
        db.table("qualified_items").select("*")
        .eq("status", "active")
        .eq("type", "flight")
        .gte("score", min_score)
    )
    if discount_filter[0] == "gte":
        query = query.gte("discount_pct", effective_floor)
    elif effective_floor >= discount_filter[2]:
        # Caller raised the floor past the free-tier ceiling → drop the
        # upper bound and behave like a plain gte(effective_floor).
        query = query.gte("discount_pct", effective_floor)
    else:
        query = query.gte("discount_pct", effective_floor).lt("discount_pct", discount_filter[2])

    qi_resp = query.order("score", desc=True).limit(limit * 3).execute()
    qualified = qi_resp.data or []

    if not qualified:
        return {"items": [], "plan": plan}

    # Fetch raw_flights in one round-trip by item_id
    item_ids = [q["item_id"] for q in qualified if q.get("item_id")]
    flights_by_id: dict[str, dict] = {}
    if item_ids:
        rf_resp = (
            db.table("raw_flights")
            .select("id, origin, destination, departure_date, return_date, airline, stops, source_url, trip_duration_days, duration_minutes")
            .in_("id", item_ids)
            .execute()
        )
        for f in (rf_resp.data or []):
            flights_by_id[f["id"]] = f

    is_authenticated = user is not None
    is_premium = _is_premium_user(user)

    # Dedup: same flight (origin+dest+dates) can appear multiple times
    # across scrape runs. Keep the highest-score entry per route+dates.
    seen_flights: set[str] = set()
    items = []
    for qi in qualified:
        flight = flights_by_id.get(qi.get("item_id")) or {}
        dedup_key = f"{flight.get('origin','')}-{flight.get('destination','')}-{flight.get('departure_date','')}-{flight.get('return_date','')}"
        if dedup_key in seen_flights:
            continue
        seen_flights.add(dedup_key)
        tier = qi.get("tier", "free")

        # Decide whether sensitive fields are visible for this deal
        if is_premium:
            unlocked = True
        elif is_authenticated and tier == "free":
            unlocked = True
        else:
            unlocked = False

        items.append({
            "id": qi["id"],
            "tier": tier,
            "discount_pct": qi["discount_pct"],
            "score": qi["score"],
            "created_at": qi["created_at"],
            # Always-visible enrichment
            "origin": flight.get("origin", ""),
            "destination": flight.get("destination", ""),
            "departure_date": flight.get("departure_date", ""),
            "return_date": flight.get("return_date", ""),
            "airline": flight.get("airline"),
            "stops": flight.get("stops", 0),
            "trip_duration_days": flight.get("trip_duration_days"),
            "duration_minutes": flight.get("duration_minutes"),
            # Sensitive fields — nullified when locked
            "price": qi["price"] if unlocked else None,
            "baseline_price": qi["baseline_price"] if unlocked else None,
            "source_url": flight.get("source_url", "") if unlocked else None,
            "locked": not unlocked,
        })

    return {"items": items[:limit], "plan": plan}


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
        job_recalculate_baselines,
        job_expire_stale_data,
        job_travelpayouts_enrichment,
    )

    jobs = {
        "scrape_flights": job_scrape_flights,
        "recalculate_baselines": job_recalculate_baselines,
        "expire_stale_data": job_expire_stale_data,
        "travelpayouts_enrichment": job_travelpayouts_enrichment,
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

    # Free tier cannot filter on discounts >= 30 — silently floor to 29
    # and signal the cap back to the client via `capped`.
    caller_id = user.get("user_id") or user.get("sub")
    tier = _get_user_tier(caller_id)
    capped = False
    effective_min_discount = req.min_discount
    if tier == "free" and effective_min_discount >= 30:
        effective_min_discount = 29
        capped = True

    update_data = {
        "airport_codes": req.airport_codes,
        "offer_types": req.offer_types,
        "min_discount": effective_min_discount,
        "max_budget": req.max_budget,
        "preferred_destinations": req.preferred_destinations or [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    resp = db.table("user_preferences").update(update_data).eq("user_id", user_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    return {**resp.data[0], "capped": capped}


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


# ─── STRIPE ───

@router.post("/api/stripe/create-checkout")
async def create_checkout(user: dict = Depends(get_current_user)):
    """Create a Stripe Checkout session for premium subscription."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    user_id = user["sub"]
    user_email = user.get("email", "")

    # Check if user already has a Stripe customer
    if db:
        prefs = db.table("user_preferences").select("stripe_customer_id").eq("user_id", user_id).execute()
        customer_id = prefs.data[0].get("stripe_customer_id") if prefs.data else None
    else:
        customer_id = None

    try:
        # Create or reuse customer
        if not customer_id:
            customer = stripe.Customer.create(email=user_email, metadata={"user_id": user_id})
            customer_id = customer.id
            if db:
                db.table("user_preferences").update({"stripe_customer_id": customer_id}).eq("user_id", user_id).execute()

        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
            discounts=[{"coupon": settings.STRIPE_COUPON_ID}] if settings.STRIPE_COUPON_ID else [],
            success_url="https://globegenius.app/home?payment=success",
            cancel_url="https://globegenius.app/home?payment=cancel",
        )

        return {"checkout_url": session.url, "session_id": session.id}

    except stripe.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks (subscription events)."""
    if not settings.STRIPE_SECRET_KEY:
        return {"ok": True}

    stripe.api_key = settings.STRIPE_SECRET_KEY
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        if settings.STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
        else:
            event = json.loads(payload)
    except Exception as e:
        logger.error(f"Stripe webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        if db and customer_id:
            db.table("user_preferences").update({
                "stripe_subscription_id": subscription_id,
                "is_premium": True,
            }).eq("stripe_customer_id", customer_id).execute()
            logger.info(f"Premium activated for customer {customer_id}")

    elif event_type in ("customer.subscription.deleted", "customer.subscription.paused"):
        customer_id = data.get("customer")
        if db and customer_id:
            db.table("user_preferences").update({
                "is_premium": False,
            }).eq("stripe_customer_id", customer_id).execute()
            logger.info(f"Premium deactivated for customer {customer_id}")

    return {"ok": True}


@router.post("/api/stripe/portal")
async def create_portal(user: dict = Depends(get_current_user)):
    """Create Stripe Customer Portal session for managing subscription."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    user_id = user["sub"]

    if db:
        prefs = db.table("user_preferences").select("stripe_customer_id").eq("user_id", user_id).execute()
        customer_id = prefs.data[0].get("stripe_customer_id") if prefs.data else None
    else:
        customer_id = None

    if not customer_id:
        raise HTTPException(status_code=400, detail="No subscription found")

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url="https://globegenius.app/home",
        )
        return {"portal_url": session.url}
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/stripe/status")
async def subscription_status(user: dict = Depends(get_current_user)):
    """Check if current user has premium subscription.
    Uses _get_user_tier as single source of truth (checks premium_grants
    first, then stripe_customer_id)."""
    user_id = user.get("sub") or user.get("user_id")
    return {"is_premium": _get_user_tier(user_id) == "premium"}


# ─── ADMIN CONSOLE ───

class AdminGrantPremiumRequest(BaseModel):
    expires_at: str | None = None
    reason: str | None = None


class AdminMinDiscountRequest(BaseModel):
    value: int

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: int) -> int:
        if v not in {20, 30, 40, 50, 60}:
            raise ValueError("value must be one of 20,30,40,50,60")
        return v


@router.get("/api/admin/users")
def admin_list_users(request: Request, limit: int = 100):
    _require_admin(request)
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    users_resp = db.table("users").select("id,email,created_at").limit(limit).execute()
    users = users_resp.data or []
    user_ids = [u["id"] for u in users]
    prefs_by_user = {}
    grants_by_user = {}
    if user_ids:
        prefs_resp = (
            db.table("user_preferences")
            .select("user_id,min_discount,stripe_customer_id,telegram_connected,telegram_chat_id")
            .in_("user_id", user_ids)
            .execute()
        )
        prefs_by_user = {p["user_id"]: p for p in (prefs_resp.data or [])}
        try:
            grants_resp = (
                db.table("premium_grants")
                .select("user_id,expires_at,revoked,granted_at,reason")
                .in_("user_id", user_ids)
                .eq("revoked", False)
                .execute()
            )
            grants_by_user = {g["user_id"]: g for g in (grants_resp.data or [])}
        except Exception:
            grants_by_user = {}
    items = []
    for u in users:
        uid = u["id"]
        prefs = prefs_by_user.get(uid, {})
        grant = grants_by_user.get(uid)
        tier = _get_user_tier(uid)
        items.append({
            "id": uid,
            "email": u["email"],
            "created_at": u["created_at"],
            "tier": tier,
            "min_discount": prefs.get("min_discount", 20),
            "stripe_customer_id": prefs.get("stripe_customer_id"),
            "telegram_connected": prefs.get("telegram_connected", False),
            "has_grant": bool(grant),
            "grant_expires_at": grant.get("expires_at") if grant else None,
            "is_admin": u["email"] in settings.ADMIN_EMAILS,
        })
    return {"items": items, "count": len(items)}


@router.get("/api/admin/users/{user_id}")
def admin_get_user(user_id: str, request: Request):
    _require_admin(request)
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    user_resp = db.table("users").select("*").eq("id", user_id).execute()
    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")
    prefs_resp = db.table("user_preferences").select("*").eq("user_id", user_id).execute()
    grants = []
    try:
        g_resp = db.table("premium_grants").select("*").eq("user_id", user_id).execute()
        grants = g_resp.data or []
    except Exception:
        pass
    return {
        "user": user_resp.data[0],
        "preferences": prefs_resp.data[0] if prefs_resp.data else None,
        "grants": grants,
        "tier": _get_user_tier(user_id),
    }


@router.put("/api/admin/users/{user_id}/premium")
def admin_grant_premium(user_id: str, req: AdminGrantPremiumRequest, request: Request):
    _require_admin(request)
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    row = {
        "user_id": user_id,
        "granted_by": "admin",
        "expires_at": req.expires_at,
        "reason": req.reason,
        "revoked": False,
        "revoked_at": None,
    }
    resp = db.table("premium_grants").upsert(row, on_conflict="user_id").execute()
    return {"ok": True, "grant": (resp.data[0] if resp.data else row)}


@router.delete("/api/admin/users/{user_id}/premium")
def admin_revoke_premium(user_id: str, request: Request):
    _require_admin(request)
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    resp = (
        db.table("premium_grants")
        .update({
            "revoked": True,
            "revoked_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("user_id", user_id)
        .execute()
    )
    return {"ok": True, "revoked_count": len(resp.data or [])}


@router.put("/api/admin/users/{user_id}/min_discount")
def admin_update_min_discount(user_id: str, req: AdminMinDiscountRequest, request: Request):
    _require_admin(request)
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    resp = db.table("user_preferences").update({"min_discount": req.value}).eq("user_id", user_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User preferences not found")
    return {"ok": True, "min_discount": req.value}


@router.post("/api/admin/users/{user_id}/reset_prefs")
def admin_reset_prefs(user_id: str, request: Request):
    _require_admin(request)
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    defaults = {
        "airport_codes": ["CDG"],
        "offer_types": ["package", "flight", "accommodation"],
        "min_discount": 20,
        "max_budget": None,
        "preferred_destinations": [],
    }
    resp = db.table("user_preferences").update(defaults).eq("user_id", user_id).execute()
    return {"ok": True, "reset": bool(resp.data)}
