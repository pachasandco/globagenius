import asyncio
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import db
from app.config import settings

router = APIRouter()

VALID_AIRPORTS = settings.MVP_AIRPORTS
VALID_OFFER_TYPES = ["package", "flight", "accommodation"]


class SignupRequest(BaseModel):
    email: str


class PreferencesRequest(BaseModel):
    airport_code: str
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
def list_packages(min_score: int = 0, limit: int = 20):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    resp = (
        db.table("packages")
        .select("*")
        .eq("status", "active")
        .gte("score", min_score)
        .order("score", desc=True)
        .limit(limit)
        .execute()
    )
    return {"packages": resp.data or []}


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
def signup(req: SignupRequest):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    # Check if user exists
    existing = db.table("users").select("id").eq("email", req.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    user = db.table("users").insert({"email": req.email}).execute()
    if not user.data:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user_id = user.data[0]["id"]

    # Create default preferences
    db.table("user_preferences").insert({
        "user_id": user_id,
        "airport_code": "CDG",
        "offer_types": ["package", "flight", "accommodation"],
    }).execute()

    return {"user_id": user_id, "email": req.email}


@router.post("/api/auth/login")
def login(req: SignupRequest):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    user = db.table("users").select("*").eq("email", req.email).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")

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

    if req.airport_code not in VALID_AIRPORTS:
        raise HTTPException(status_code=400, detail=f"Invalid airport. Valid: {VALID_AIRPORTS}")

    for ot in req.offer_types:
        if ot not in VALID_OFFER_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid offer type. Valid: {VALID_OFFER_TYPES}")

    update_data = {
        "airport_code": req.airport_code,
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

    bot_username = "GlobeGeniusBot"
    deep_link = f"https://t.me/{bot_username}?start={token}"

    return {"link": deep_link, "token": token}


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
