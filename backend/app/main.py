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

# ── Sentry init ──
# Initialised before anything else so any boot-time exception (DB
# connection, Stripe key validation, Telegram token check) gets reported.
# DSN is read from SENTRY_DSN env var; if absent, sentry-sdk is a no-op
# so dev / CI runs stay quiet.
_SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if _SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=_SENTRY_DSN,
            environment=os.getenv("APP_ENV", "production"),
            release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "dev"),
            traces_sample_rate=0.05,  # 5% of requests get a trace
            profiles_sample_rate=0.0,  # profiling off, costs extra
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(level=None, event_level=40),  # WARNING+
            ],
            send_default_pii=False,  # never send Authorization headers / cookies
        )
        logger.info("Sentry initialised — environment=%s", os.getenv("APP_ENV", "production"))
    except Exception as e:
        # Never block startup on a Sentry import / init issue.
        logger.error("Sentry init failed (continuing without it): %s", e)

logger.info(f"Starting Globe Genius Pipeline — ENV={os.getenv('APP_ENV', 'unknown')} PORT={os.getenv('PORT', 'not set')}")

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import settings
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set — Telegram alerts will be silently disabled")
    else:
        logger.info("Telegram bot token configured ✓")

    # APScheduler defaults misfire_grace_time to 1 second, which means a
    # cron job whose firing instant is missed by even a brief Railway
    # restart is silently skipped. We saw this on update_destinations:
    # the priority_destinations table hadn't been refreshed for 9 days
    # because the Monday 03:00 firing was always missed during deploys.
    # 1h is plenty of slack for any of our cron jobs to recover.
    DEFAULT_MISFIRE_GRACE_SECONDS = 3600

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
            scheduler.add_job(
                func, "interval", id=job_id,
                misfire_grace_time=DEFAULT_MISFIRE_GRACE_SECONDS,
                **kwargs,
            )
        elif trigger == "cron":
            cron_kwargs = {}
            if "hour" in job_def:
                cron_kwargs["hour"] = job_def["hour"]
            if "minute" in job_def:
                cron_kwargs["minute"] = job_def["minute"]
            if "day_of_week" in job_def:
                cron_kwargs["day_of_week"] = job_def["day_of_week"]
            scheduler.add_job(
                func, "cron", id=job_id,
                misfire_grace_time=DEFAULT_MISFIRE_GRACE_SECONDS,
                **cron_kwargs,
            )

    scheduler.start()
    logger.info(f"Scheduler started with {len(scheduler.get_jobs())} jobs")

    # Wire RAG retriever to the travel planner (Supabase full-text search)
    try:
        from app.api.routes import db as rag_db
        from app.agents.rag import set_rag_retriever, RagRetriever
        if rag_db:
            set_rag_retriever(RagRetriever(rag_db))
            logger.info("RAG retriever initialised ✓")
        else:
            logger.warning("RAG retriever skipped — db not available")
    except Exception as e:
        logger.warning(f"RAG retriever init failed: {e}")

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
    allow_origins=[
        "http://localhost:3000",
        "https://www.globegenius.app",
        "https://globegenius.app",
        "https://globagenius-production-b887.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(bot_router)
