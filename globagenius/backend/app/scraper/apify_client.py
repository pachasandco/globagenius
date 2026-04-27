# backend/app/scraper/apify_client.py
import logging
from apify_client import ApifyClient
from app.config import settings

logger = logging.getLogger(__name__)

ACTOR_TIMEOUT_S = 600
POLL_INTERVAL_S = 10


def get_apify_client() -> ApifyClient:
    return ApifyClient(settings.APIFY_API_TOKEN)


def run_actor(actor_id: str, run_input: dict) -> list[dict]:
    client = get_apify_client()
    logger.info(f"Starting actor {actor_id} with input: {run_input}")

    run = client.actor(actor_id).call(run_input=run_input, timeout_secs=ACTOR_TIMEOUT_S)

    if not run:
        logger.error(f"Actor {actor_id} returned no run object")
        return []

    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        logger.error(f"Actor {actor_id} has no dataset")
        return []

    items = list(client.dataset(dataset_id).iterate_items())
    logger.info(f"Actor {actor_id} returned {len(items)} items")
    return items
