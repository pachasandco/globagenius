import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.db import db

router = APIRouter()


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
