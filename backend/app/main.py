import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.api.routes import router
from app.api.signup_public import router as signup_public_router
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

        _traces_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))
        sentry_sdk.init(
            dsn=_SENTRY_DSN,
            environment=os.getenv("APP_ENV", "production"),
            release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "dev"),
            traces_sample_rate=_traces_rate,
            profiles_sample_rate=0.0,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(level=None, event_level=40),
            ],
            send_default_pii=False,
        )
        logger.info("Sentry initialised — environment=%s", os.getenv("APP_ENV", "production"))
    except Exception as e:
        logger.error("Sentry init failed (continuing without it): %s", e)

logger.info(f"Starting Globe Genius Pipeline — ENV={os.getenv('APP_ENV', 'unknown')} PORT={os.getenv('PORT', 'not set')}")

scheduler = AsyncIOScheduler()
_RUN_SCHEDULER = os.getenv("RUN_SCHEDULER", "1") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import settings
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set — Telegram alerts will be silently disabled")
    else:
        logger.info("Telegram bot token configured ✓")

    DEFAULT_MISFIRE_GRACE_SECONDS = 3600

    if not _RUN_SCHEDULER:
        logger.info("Scheduler disabled (RUN_SCHEDULER=0) — API-only worker, jobs will not run here")

    for job_def in (get_scheduler_jobs() if _RUN_SCHEDULER else []):
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
                func,
                "interval",
                id=job_id,
                misfire_grace_time=DEFAULT_MISFIRE_GRACE_SECONDS,
                coalesce=True,
                max_instances=1,
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
            if "timezone" in job_def:
                cron_kwargs["timezone"] = job_def["timezone"]
            scheduler.add_job(
                func,
                "cron",
                id=job_id,
                misfire_grace_time=DEFAULT_MISFIRE_GRACE_SECONDS,
                coalesce=True,
                max_instances=1,
                **cron_kwargs,
            )

    if _RUN_SCHEDULER:
        scheduler.start()
        logger.info(f"Scheduler started with {len(scheduler.get_jobs())} jobs")

    # Keep the existing RAG initialisation for compatibility with historical
    # jobs, even though the public travel-planner route has been removed.
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

    try:
        from app.notifications.telegram import _get_bot
        bot = _get_bot()
        if bot:
            from telegram import BotCommand
            await bot.set_my_commands([
                BotCommand("pause", "Mettre en pause les alertes"),
                BotCommand("destinations", "Voir / bloquer des destinations"),
                BotCommand("status", "État du pipeline"),
                BotCommand("help", "Aide et commandes"),
            ])
            logger.info("Telegram bot commands registered ✓")
    except Exception as e:
        logger.warning(f"setMyCommands failed (menu may be empty): {e}")

    yield

    if _RUN_SCHEDULER and scheduler.running:
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

# Public signup is registered separately so the historical founder route can
# remain intact for compatibility without blocking new standard accounts.
app.include_router(signup_public_router)
app.include_router(router)
app.include_router(bot_router)
