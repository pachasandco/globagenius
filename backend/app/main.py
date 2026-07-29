import asyncio
import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.account_plan_guard import router as account_plan_guard_router
from app.api.freemium import router as freemium_router
from app.api.preferences_freemium import (
    normalize_all_free_subscriptions,
    router as preferences_freemium_router,
)
from app.api.routes import router
from app.api.signup_public import router as signup_public_router
from app.freemium_policy import (
    guarded_send_grouped_flight_alerts,
    link_account_with_trial,
    reconcile_legacy_access,
    send_unlinked_welcome,
)
from app.notifications import bot_handler as bot_handler_module
from app.notifications.bot_handler import bot_router
from app.scheduler import jobs as scheduler_jobs
from app.scheduler.jobs import get_scheduler_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Keep the mature ranking/dispatch pipeline intact and replace only its final
# entitlement boundary. The webhook resolves these module globals at runtime,
# so patching here also updates Telegram account linking without duplicating a
# second webhook route.
scheduler_jobs.send_grouped_flight_alerts = guarded_send_grouped_flight_alerts
bot_handler_module._link_account = link_account_with_trial
bot_handler_module._send_welcome = send_unlinked_welcome

# ── Sentry init ──
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
    except Exception as exc:
        logger.error("Sentry init failed (continuing without it): %s", exc)

logger.info(
    "Starting Globe Genius Pipeline — ENV=%s PORT=%s",
    os.getenv("APP_ENV", "unknown"),
    os.getenv("PORT", "not set"),
)

scheduler = AsyncIOScheduler()
_RUN_SCHEDULER = os.getenv("RUN_SCHEDULER", "1") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import settings

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set — Telegram alerts will be silently disabled")
    else:
        logger.info("Telegram bot token configured ✓")

    # Idempotent production cutover: OG badges retain lifetime Premium; legacy
    # founder grants without a badge are revoked and those users become free.
    try:
        stats = await asyncio.to_thread(reconcile_legacy_access)
        logger.info("Access model reconciled: %s", stats)
        normalized = await asyncio.to_thread(normalize_all_free_subscriptions)
        logger.info("Freemium subscriptions normalized: %s users", normalized)
    except Exception as exc:
        # Do not prevent the service from starting, but surface the failure
        # loudly because access reconciliation is commercially important.
        logger.exception("Access reconciliation failed: %s", exc)

    default_misfire_grace_seconds = 3600
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
                misfire_grace_time=default_misfire_grace_seconds,
                coalesce=True,
                max_instances=1,
                **kwargs,
            )
        elif trigger == "cron":
            cron_kwargs = {}
            for key in ("hour", "minute", "day_of_week", "day", "timezone"):
                if key in job_def:
                    cron_kwargs[key] = job_def[key]
            scheduler.add_job(
                func,
                "cron",
                id=job_id,
                misfire_grace_time=default_misfire_grace_seconds,
                coalesce=True,
                max_instances=1,
                **cron_kwargs,
            )

    if _RUN_SCHEDULER:
        scheduler.start()
        logger.info("Scheduler started with %s jobs", len(scheduler.get_jobs()))

    # Kept for compatibility with historical internal jobs even though the
    # public travel-planner page and endpoints have been removed.
    try:
        from app.api.routes import db as rag_db
        from app.agents.rag import RagRetriever, set_rag_retriever

        if rag_db:
            set_rag_retriever(RagRetriever(rag_db))
            logger.info("RAG retriever initialised ✓")
        else:
            logger.warning("RAG retriever skipped — db not available")
    except Exception as exc:
        logger.warning("RAG retriever init failed: %s", exc)

    try:
        from app.notifications.telegram import _get_bot

        bot = _get_bot()
        if bot:
            from telegram import BotCommand

            await bot.set_my_commands(
                [
                    BotCommand("pause", "Mettre en pause les alertes"),
                    BotCommand("destinations", "Voir / bloquer des destinations"),
                    BotCommand("status", "État du pipeline"),
                    BotCommand("help", "Aide et commandes"),
                ]
            )
            logger.info("Telegram bot commands registered ✓")
    except Exception as exc:
        logger.warning("setMyCommands failed (menu may be empty): %s", exc)

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

# These routers are registered before the historical monolithic router so their
# modern public endpoints and entitlement-aware routes take priority.
app.include_router(signup_public_router)
app.include_router(preferences_freemium_router)
app.include_router(account_plan_guard_router)
app.include_router(freemium_router)
app.include_router(router)
app.include_router(bot_router)
