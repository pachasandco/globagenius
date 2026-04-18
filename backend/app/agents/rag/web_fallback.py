"""Web search fallback for destinations not covered by YouTube transcripts."""

import logging
from typing import Optional

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

logger = logging.getLogger(__name__)


def search_destination(destination: str, limit: int = 5) -> list[dict]:
    """
    Search the web for information about a destination.

    Uses DuckDuckGo (free, no API key required).

    Args:
        destination: Destination name (e.g., "Tokyo", "Paris")
        limit: Number of results to return

    Returns:
        List of dicts: {title, body, url}
    """
    if DDGS is None:
        logger.warning("duckduckgo-search not installed, cannot fetch web results")
        return []

    try:
        ddgs = DDGS()
        results = ddgs.text(destination, max_results=limit)
        return results or []
    except Exception as e:
        logger.error(f"Web search failed for {destination}: {e}")
        return []


def format_search_results(results: list[dict]) -> str:
    """
    Format web search results into a readable string for LLM context.

    Args:
        results: List of search result dicts

    Returns:
        Formatted text block
    """
    if not results:
        return ""

    lines = ["Sources: Web Search"]
    for i, result in enumerate(results, 1):
        title = result.get("title", "")
        body = result.get("body", "")
        lines.append(f"\n{i}. {title}")
        if body:
            lines.append(f"   {body[:200]}...")

    return "\n".join(lines)
