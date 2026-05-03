import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Default 1 worker because APScheduler runs in-process; raising this
    # without setting RUN_SCHEDULER=0 would duplicate every cron job per worker.
    # See app/main.py — _RUN_SCHEDULER guard.
    workers = int(os.environ.get("WEB_CONCURRENCY", 1))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, workers=workers)
