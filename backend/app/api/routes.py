import asyncio
import json
import re
import secrets
import logging
import stripe
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
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
_RATE_LIMIT_PURGE_INTERVAL = 300  # purge stale keys every 5 minutes
_rate_limit_last_purge: float = 0.0


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(key: str):
    global _rate_limit_last_purge
    now = datetime.now(timezone.utc).timestamp()

    # Periodically purge keys with no recent activity to prevent unbounded growth
    if now - _rate_limit_last_purge > _RATE_LIMIT_PURGE_INTERVAL:
        cutoff = now - RATE_LIMIT_WINDOW
        stale = [k for k, ts in _rate_limits.items() if not ts or max(ts) < cutoff]
        for k in stale:
            del _rate_limits[k]
        _rate_limit_last_purge = now

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

    Priority 1: active premium_grants row (manual admin grant, optional expiry)
    Priority 2: premium_expires_at on user_preferences (set by Stripe webhook +
                refreshed daily by job_sync_stripe_subscriptions)
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
    # Priority 2: Stripe subscription — check premium_expires_at written by
    # webhook + refreshed daily by job_sync_stripe_subscriptions.
    try:
        row = (
            db.table("user_preferences")
            .select("premium_expires_at")
            .eq("user_id", user_id)
            .execute()
        )
        if row.data:
            expires_at = row.data[0].get("premium_expires_at")
            if expires_at:
                try:
                    exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if exp > datetime.now(timezone.utc):
                        return "premium"
                except Exception:
                    pass
    except Exception:
        pass
    return "free"


async def _get_user_tier_async(user_id: str | None) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_user_tier, user_id)


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
    max_budget: int | None = None
    preferred_destinations: list[str] | None = None
    deal_tier: str = "regular"

    @field_validator("deal_tier")
    @classmethod
    def validate_deal_tier(cls, v: str) -> str:
        allowed = {"regular", "exceptional"}
        if v not in allowed:
            raise ValueError(f"deal_tier must be one of {sorted(allowed)}")
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
        .limit(50)
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

    try:
        flights = db.table("raw_flights").select("origin, destination, departure_date, return_date, price, source").order("scraped_at", desc=True).limit(5).execute()
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

        return {
            "flights_sample": flights.data or [],
            "baselines_sample": baselines.data or [],
            "price_diagnosis": diagnosis,
        }
    except Exception as e:
        return {"error": str(e)}


GLOBAL_MIN_DISCOUNT = 40   # aligned with Telegram dispatch threshold
FREE_TIER_WEEKLY_LIMIT = 3  # full unlocked deals per week for free users


@router.get("/api/packages")
def list_packages(
    min_score: int = 0,
    limit: int = 50,
    plan: str = "free",
    min_discount: int = 0,
    user: dict | None = Depends(get_optional_user),
):
    """Return deals aligned with Telegram dispatch rules.

    All deals: ≥50% discount only.
    Premium: all deals unlocked, no weekly cap.
    Free authenticated: up to 3 unlocked per rolling 7-day window
                        (same deals as Telegram), rest shown masked.
    Anonymous: all deals masked.
    """
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    effective_floor = max(min_discount, GLOBAL_MIN_DISCOUNT)

    # Only show deals reverified within the last 4h. Deals without reverified_at
    # (pre-migration rows) are included via the OR fallback to created_at.
    freshness_cutoff = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()

    qi_resp = (
        db.table("qualified_items").select("*")
        .eq("status", "active")
        .eq("type", "flight")
        .gte("discount_pct", effective_floor)
        .gte("score", min_score)
        .gte("reverified_at", freshness_cutoff)
        .order("score", desc=True)
        .limit(limit * 3)
        .execute()
    )
    qualified = qi_resp.data or []

    if not qualified:
        return {"items": [], "plan": plan}

    # Fetch raw_flights in one round-trip
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

    is_premium = _is_premium_user(user)
    user_id = (user.get("sub") or user.get("user_id")) if user else None

    # For free users: count how many deals they've already received this week
    # via Telegram (sent_alerts) — the homepage quota mirrors Telegram's.
    free_weekly_used = 0
    if user_id and not is_premium:
        week_start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        try:
            wk_resp = (
                db.table("sent_alerts")
                .select("alert_key", count="exact")
                .eq("user_id", user_id)
                .gte("created_at", week_start)
                .execute()
            )
            free_weekly_used = wk_resp.count or 0
        except Exception:
            pass

    # Dedup by route+dates (same flight from multiple scrape runs)
    seen_flights: set[str] = set()
    items = []
    free_unlocked_this_request = 0  # unlocked deals served in this response

    for qi in qualified:
        flight = flights_by_id.get(qi.get("item_id")) or {}
        dedup_key = (
            f"{flight.get('origin','')}-{flight.get('destination','')}"
            f"-{flight.get('departure_date','')}-{flight.get('return_date','')}"
        )
        if dedup_key in seen_flights:
            continue
        seen_flights.add(dedup_key)

        if is_premium:
            unlocked = True
        elif user_id:
            # Free user: allow up to FREE_TIER_WEEKLY_LIMIT unlocked deals
            # across both Telegram and the homepage this week.
            remaining = FREE_TIER_WEEKLY_LIMIT - free_weekly_used - free_unlocked_this_request
            if remaining > 0:
                unlocked = True
                free_unlocked_this_request += 1
            else:
                unlocked = False
        else:
            unlocked = False

        items.append({
            "id": qi["id"],
            "tier": qi.get("tier", "free"),
            "discount_pct": qi["discount_pct"],
            "score": qi["score"],
            "created_at": qi["created_at"],
            "origin": flight.get("origin", ""),
            "destination": flight.get("destination", ""),
            "departure_date": flight.get("departure_date", ""),
            "return_date": flight.get("return_date", ""),
            "airline": flight.get("airline"),
            "stops": flight.get("stops", 0),
            "trip_duration_days": flight.get("trip_duration_days"),
            "duration_minutes": flight.get("duration_minutes"),
            "price": qi["price"] if unlocked else None,
            "baseline_price": qi["baseline_price"] if unlocked else None,
            "source_url": flight.get("source_url", "") if unlocked else None,
            "locked": not unlocked,
        })

    return {"items": items[:limit], "plan": "premium" if is_premium else "free"}


@router.get("/api/qualified-items")
def list_qualified_items(type_filter: str = "", limit: int = 20, user: dict = Depends(get_current_user)):
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
        job_update_destinations,
    )

    jobs = {
        "scrape_flights": job_scrape_flights,
        "recalculate_baselines": job_recalculate_baselines,
        "expire_stale_data": job_expire_stale_data,
        "travelpayouts_enrichment": job_travelpayouts_enrichment,
        "update_destinations": job_update_destinations,
    }

    if job_name not in jobs:
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_name}")

    asyncio.create_task(jobs[job_name]())
    return {"status": "triggered", "job": job_name}


# ─── AUTH ───

@router.post("/api/auth/signup")
async def signup(req: SignupRequest, request: Request):
    _check_rate_limit(f"signup:{_client_ip(request)}")
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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/api/auth/login")
def login(req: LoginRequest, request: Request):
    _check_rate_limit(f"login:{_client_ip(request)}")
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
    if user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    prefs = db.table("user_preferences").select("*").eq("user_id", user_id).execute()
    if not prefs.data:
        raise HTTPException(status_code=404, detail="Preferences not found")

    return prefs.data[0]


@router.put("/api/users/{user_id}/preferences")
def update_preferences(user_id: str, req: PreferencesRequest, user: dict = Depends(get_current_user)):
    if user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    for ac in req.airport_codes:
        if ac not in VALID_AIRPORTS:
            raise HTTPException(status_code=400, detail=f"Invalid airport '{ac}'. Valid: {VALID_AIRPORTS}")

    for ot in req.offer_types:
        if ot not in VALID_OFFER_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid offer type. Valid: {VALID_OFFER_TYPES}")

    # Free tier cannot choose "exceptional" tier — silently floor to "regular".
    caller_id = user.get("user_id") or user.get("sub")
    tier = _get_user_tier(caller_id)
    effective_deal_tier = req.deal_tier
    if tier == "free" and effective_deal_tier == "exceptional":
        effective_deal_tier = "regular"

    update_data = {
        "airport_codes": req.airport_codes,
        "offer_types": req.offer_types,
        "max_budget": req.max_budget,
        "preferred_destinations": req.preferred_destinations or [],
        "deal_tier": effective_deal_tier,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    resp = db.table("user_preferences").update(update_data).eq("user_id", user_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    # Sync telegram_subscribers: add entries for each airport if Telegram is connected
    prefs = resp.data[0]
    if prefs.get("telegram_connected") and prefs.get("telegram_chat_id"):
        chat_id = prefs["telegram_chat_id"]
        new_airports = req.airport_codes or []

        # Get current subscriptions
        try:
            current_subs = db.table("telegram_subscribers").select("airport_code").eq("user_id", user_id).execute()
            current_airports = {s["airport_code"] for s in current_subs.data}
        except Exception:
            current_airports = set()

        # Add missing subscriptions
        for airport in new_airports:
            if airport not in current_airports:
                try:
                    db.table("telegram_subscribers").insert({
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "airport_code": airport,
                    }).execute()
                except Exception:
                    pass  # Silent fail if duplicate or constraint issue

        # Remove unselected subscriptions
        for airport in current_airports:
            if airport not in new_airports:
                try:
                    db.table("telegram_subscribers").delete().eq("user_id", user_id).eq("airport_code", airport).execute()
                except Exception:
                    pass  # Silent fail

    return resp.data[0]


@router.put("/api/users/{user_id}/email")
def update_email(user_id: str, req: dict, user: dict = Depends(get_current_user)):
    if user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    new_email = req.get("email", "").strip().lower()
    if not new_email or "@" not in new_email:
        raise HTTPException(status_code=400, detail="Invalid email format")

    # Check if email already exists
    existing = db.table("users").select("id").eq("email", new_email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already in use")

    # Update email in users table
    resp = db.table("users").update({"email": new_email}).eq("id", user_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    return {"email": new_email, "message": "Email updated successfully"}


@router.put("/api/users/{user_id}/password")
def update_password(user_id: str, req: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    if user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    _check_rate_limit(f"change_password:{user_id}")
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 6 caracteres")

    # Fetch current password hash
    row = db.table("users").select("password_hash").eq("id", user_id).single().execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    if not _verify_password(req.current_password, row.data["password_hash"]):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")

    # Update password
    db.table("users").update({"password_hash": _hash_password(req.new_password)}).eq("id", user_id).execute()

    return {"message": "Password updated successfully"}


# ─── TELEGRAM CONNECT ───

@router.post("/api/users/{user_id}/telegram/generate-link")
def generate_telegram_link(user_id: str, user: dict = Depends(get_current_user)):
    """Generate a unique link for user to connect their Telegram."""
    if user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    token = secrets.token_urlsafe(16)

    # Store token temporarily in preferences
    db.table("user_preferences").update({
        "telegram_connect_token": token,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", user_id).execute()

    bot_username = "Globegenius_bot"
    deep_link = f"https://t.me/{bot_username}?start={token}"

    return {"link": deep_link, "token": token}


@router.post("/api/telegram/setup-webhook")
async def setup_telegram_webhook(request: Request):
    _require_admin(request)
    """Set Telegram webhook to point to our API."""
    import httpx
    webhook_url = f"{settings.BACKEND_URL}/api/telegram/webhook"
    telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"

    async with httpx.AsyncClient() as client:
        resp = await client.post(telegram_url, json={"url": webhook_url})
        return resp.json()


@router.get("/api/users/{user_id}/telegram/status")
def telegram_status(user_id: str, user: dict = Depends(get_current_user)):
    if user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
async def planner_chat(user_id: str, req: PlannerMessage, user: dict = Depends(get_current_user)):
    """Chat with the travel planner agent."""
    if user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.agents.rag import get_or_create_session
    session = get_or_create_session(user_id)
    response = session.chat(req.message)
    return response or {"type": "error", "message": "Pas de reponse"}


@router.post("/api/planner/{user_id}/reset")
async def planner_reset(user_id: str, user: dict = Depends(get_current_user)):
    """Reset the planner conversation."""
    if user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.agents.rag import reset_session
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
            payment_method_types=["card"],
            line_items=[{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
            discounts=[{"coupon": settings.STRIPE_COUPON_ID}] if settings.STRIPE_COUPON_ID else [],
            success_url=f"{settings.FRONTEND_URL}/home?payment=success",
            cancel_url=f"{settings.FRONTEND_URL}/home?payment=cancel",
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

    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.error(f"Stripe webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        if db and customer_id and subscription_id:
            # Fetch current_period_end from the subscription to set exact expiry
            premium_expires_at = None
            try:
                stripe.api_key = settings.STRIPE_SECRET_KEY
                sub = stripe.Subscription.retrieve(subscription_id)
                period_end = sub.get("current_period_end")
                if period_end:
                    from datetime import datetime, timezone
                    premium_expires_at = datetime.fromtimestamp(period_end, tz=timezone.utc).isoformat()
            except Exception as e:
                logger.warning(f"Could not fetch subscription period_end: {e}")

            db.table("user_preferences").update({
                "stripe_subscription_id": subscription_id,
                "is_premium": True,
                **({"premium_expires_at": premium_expires_at} if premium_expires_at else {}),
            }).eq("stripe_customer_id", customer_id).execute()
            logger.info(f"Premium activated for customer {customer_id} expires={premium_expires_at}")

    elif event_type == "customer.subscription.updated":
        # Renewal or plan change — update the expiry date
        customer_id = data.get("customer")
        period_end = data.get("current_period_end")
        status = data.get("status", "")
        if db and customer_id and period_end and status in ("active", "trialing"):
            from datetime import datetime, timezone
            expires_at = datetime.fromtimestamp(period_end, tz=timezone.utc).isoformat()
            db.table("user_preferences").update({
                "premium_expires_at": expires_at,
                "is_premium": True,
            }).eq("stripe_customer_id", customer_id).execute()
            logger.info(f"Subscription renewed for customer {customer_id} until {expires_at}")

    elif event_type in ("customer.subscription.deleted", "customer.subscription.paused"):
        customer_id = data.get("customer")
        if db and customer_id:
            from datetime import datetime, timezone
            db.table("user_preferences").update({
                "is_premium": False,
                "premium_expires_at": datetime.now(timezone.utc).isoformat(),
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
            return_url=f"{settings.FRONTEND_URL}/home",
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
    return {"is_premium": await _get_user_tier_async(user_id) == "premium"}


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


@router.get("/api/admin/routes")
def admin_routes(request: Request):
    """Return all monitored routes with scraping source and baseline status."""
    _require_admin(request)
    from app.scraper.tier1_routes import TIER1_ROUTES

    # Build tier1 lookup: (origin, destination) → list of airlines
    tier1_map: dict[tuple[str, str], list[str]] = {}
    for o, d, airlines in TIER1_ROUTES:
        tier1_map[(o, d)] = airlines

    # Fetch all baselines to check which routes have an active baseline
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    baselines_resp = db.table("price_baselines").select(
        "origin,destination,avg_price,sample_count,updated_at"
    ).execute()
    baseline_by_route: dict[tuple[str, str], dict] = {}
    for b in (baselines_resp.data or []):
        if isinstance(b, dict) and b.get("origin") and b.get("destination"):
            key = (b["origin"], b["destination"])
            # Keep the most recently updated baseline per route
            existing = baseline_by_route.get(key)
            if not existing or b.get("updated_at", "") > existing.get("updated_at", ""):
                baseline_by_route[key] = b

    # Travelpayouts routes: fetch distinct (origin, destination) from raw_flights
    # that are NOT in tier1_map
    tp_resp = db.table("raw_flights").select("origin,destination").execute()
    tp_routes: set[tuple[str, str]] = set()
    for r in (tp_resp.data or []):
        if isinstance(r, dict) and r.get("origin") and r.get("destination"):
            key = (r["origin"], r["destination"])
            if key not in tier1_map:
                tp_routes.add(key)

    rows = []

    # Tier 1 routes
    for (o, d), airlines in tier1_map.items():
        bl = baseline_by_route.get((o, d))
        rows.append({
            "origin": o,
            "destination": d,
            "sources": airlines,
            "tier": "tier1",
            "has_baseline": bl is not None,
            "baseline_avg": round(bl["avg_price"]) if bl and bl.get("avg_price") else None,
            "baseline_samples": bl["sample_count"] if bl else 0,
            "baseline_updated_at": bl["updated_at"] if bl else None,
        })

    # Travelpayouts-only routes
    for (o, d) in sorted(tp_routes):
        bl = baseline_by_route.get((o, d))
        rows.append({
            "origin": o,
            "destination": d,
            "sources": ["travelpayouts"],
            "tier": "tier2",
            "has_baseline": bl is not None,
            "baseline_avg": round(bl["avg_price"]) if bl and bl.get("avg_price") else None,
            "baseline_samples": bl["sample_count"] if bl else 0,
            "baseline_updated_at": bl["updated_at"] if bl else None,
        })

    # Sort: tier1 first, then alphabetically by origin+destination
    rows.sort(key=lambda r: (r["tier"], r["origin"], r["destination"]))

    return {"routes": rows, "total": len(rows), "tier1_count": len(tier1_map), "tier2_count": len(tp_routes)}


# ---------------------------------------------------------------------------
# Destination Wishlists
# ---------------------------------------------------------------------------

IATA_RE = re.compile(r"^[A-Z]{3}$")


class WishlistCreateRequest(BaseModel):
    origin: str
    destination: str
    max_price: int | None = None
    month: int | None = None
    label: str | None = None

    @field_validator("origin", "destination")
    @classmethod
    def validate_iata(cls, v: str) -> str:
        v = v.strip().upper()
        if not IATA_RE.match(v):
            raise ValueError("Code IATA invalide (3 lettres majuscules)")
        return v

    @field_validator("max_price")
    @classmethod
    def validate_max_price(cls, v: int | None) -> int | None:
        if v is not None and (v < 0 or v > 9999):
            raise ValueError("max_price doit être entre 0 et 9999")
        return v

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: int | None) -> int | None:
        if v is not None and v not in range(1, 13):
            raise ValueError("month doit être entre 1 et 12")
        return v

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()[:80]
        return v or None


@router.get("/api/users/{user_id}/wishlists")
def get_wishlists(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    resp = (
        db.table("destination_wishlists")
        .select("*")
        .eq("user_id", user_id)
        .eq("active", True)
        .order("created_at", desc=False)
        .execute()
    )
    return {"wishlists": resp.data or []}


@router.post("/api/users/{user_id}/wishlists", status_code=201)
def create_wishlist(
    user_id: str,
    req: WishlistCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    # Cap: 10 active wishlists per user
    count_resp = (
        db.table("destination_wishlists")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("active", True)
        .execute()
    )
    if (count_resp.count or 0) >= 10:
        raise HTTPException(status_code=422, detail="Maximum 10 destinations en wishlist")

    if req.origin == req.destination:
        raise HTTPException(status_code=422, detail="Origine et destination identiques")

    row = {
        "user_id": user_id,
        "origin": req.origin,
        "destination": req.destination,
        "max_price": req.max_price,
        "month": req.month,
        "label": req.label,
        "active": True,
    }
    try:
        resp = db.table("destination_wishlists").insert(row).execute()
    except Exception as exc:
        # Unique constraint violation = entry already exists
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Cette destination est déjà dans votre wishlist")
        raise HTTPException(status_code=500, detail="Erreur lors de la création")
    return {"wishlist": resp.data[0] if resp.data else row}


@router.delete("/api/users/{user_id}/account", status_code=200)
def delete_account(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    # Disconnect Telegram before deleting so the bot can't send stale alerts
    try:
        db.table("user_preferences").update({
            "telegram_connected": False,
            "telegram_chat_id": None,
        }).eq("user_id", user_id).execute()
    except Exception:
        pass
    # Delete user row — cascades wipe preferences, wishlists, sent_alerts, etc.
    db.table("users").delete().eq("id", user_id).execute()
    return {"ok": True}


@router.delete("/api/users/{user_id}/wishlists/{wishlist_id}", status_code=200)
def delete_wishlist(
    user_id: str,
    wishlist_id: str,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    resp = (
        db.table("destination_wishlists")
        .delete()
        .eq("id", wishlist_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Wishlist introuvable")
    return {"ok": True}


# ── CLICK TRACKING ──────────────────────────────────────────────────────────

@router.get("/r/{token}")
def redirect_tracking(token: str):
    """Redirect a tracked alert link and record the click."""
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    resp = db.table("alert_redirect_tokens").select("url,clicked_at,click_count").eq("token", token).maybe_single().execute()
    row = resp.data if resp else None
    if not row:
        raise HTTPException(status_code=404, detail="Lien introuvable")

    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        db.table("alert_redirect_tokens").update({
            "clicked_at": row.get("clicked_at") or now_iso,
            "click_count": (row.get("click_count") or 0) + 1,
        }).eq("token", token).execute()
    except Exception:
        pass

    url = row["url"]
    return RedirectResponse(url=url, status_code=302)


@router.get("/api/admin/ctr")
def admin_ctr(request: Request, days: int = 30):
    """Click-through rate dashboard for Telegram alerts."""
    _require_admin(request)
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Total alerts sent in window
    sent_resp = (
        db.table("sent_alerts")
        .select("destination,alert_type", count="exact")
        .gte("sent_at", since)
        .execute()
    )
    total_sent = sent_resp.count or 0

    # Clicks recorded (tokens created in window)
    tokens_resp = (
        db.table("alert_redirect_tokens")
        .select("destination,origin,click_count,clicked_at")
        .gte("created_at", since)
        .execute()
    )
    tokens = tokens_resp.data or []

    total_tokens = len(tokens)
    total_clicked = sum(1 for t in tokens if t.get("click_count", 0) > 0)
    total_clicks = sum(t.get("click_count", 0) for t in tokens)

    ctr = round(total_clicked / total_tokens * 100, 1) if total_tokens > 0 else 0.0

    # CTR per destination (top 10)
    by_dest: dict[str, dict] = {}
    for t in tokens:
        dest = t.get("destination") or "?"
        entry = by_dest.setdefault(dest, {"tokens": 0, "clicked": 0, "clicks": 0})
        entry["tokens"] += 1
        if t.get("click_count", 0) > 0:
            entry["clicked"] += 1
            entry["clicks"] += t["click_count"]

    top_destinations = sorted(
        [
            {
                "destination": dest,
                "tokens": v["tokens"],
                "clicked": v["clicked"],
                "clicks": v["clicks"],
                "ctr": round(v["clicked"] / v["tokens"] * 100, 1) if v["tokens"] else 0,
            }
            for dest, v in by_dest.items()
        ],
        key=lambda x: x["ctr"],
        reverse=True,
    )[:10]

    return {
        "period_days": days,
        "total_sent": total_sent,
        "total_links_generated": total_tokens,
        "total_links_clicked": total_clicked,
        "total_clicks": total_clicks,
        "ctr_pct": ctr,
        "top_destinations": top_destinations,
    }
