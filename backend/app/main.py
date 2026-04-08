import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.api.routes import router
from app.notifications.bot_handler import bot_router
from app.scheduler.jobs import get_scheduler_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

import os

logger.info(f"Starting Globe Genius Pipeline — ENV={os.getenv('APP_ENV', 'unknown')} PORT={os.getenv('PORT', 'not set')}")

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    for job_def in get_scheduler_jobs():
        job_id = job_def["id"]
        func = job_def["func"]
        trigger = job_def["trigger"]

        if trigger == "interval":
            kwargs = {}
            if "hours" in job_def:
                kwargs["hours"] = job_def["hours"]
            if "minutes" in job_def:
                kwargs["minutes"] = job_def["minutes"]
            scheduler.add_job(func, "interval", id=job_id, **kwargs)
        elif trigger == "cron":
            scheduler.add_job(func, "cron", id=job_id, hour=job_def.get("hour", 0))

    scheduler.start()
    logger.info(f"Scheduler started with {len(scheduler.get_jobs())} jobs")

    yield

    scheduler.shutdown()
    logger.info("Scheduler shut down")


app = FastAPI(
    title="Globe Genius Pipeline",
    description="Travel deal detection pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app", "https://*.up.railway.app", "https://www.globegenius.app", "https://globegenius.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(bot_router)
