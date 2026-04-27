"""Ingest YouTube travel channel transcripts into Supabase rag_chunks table."""

import logging
import re
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    TRANSCRIPT_API_AVAILABLE = False
    logger.warning("youtube-transcript-api not installed")


def get_channel_videos(channel_id: str, api_key: str, max_results: int = 50) -> list[dict]:
    """Fetch recent video IDs from a YouTube channel via Data API v3."""
    videos = []
    page_token = None

    while len(videos) < max_results:
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "maxResults": min(50, max_results - len(videos)),
            "order": "date",
            "type": "video",
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            resp = httpx.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"YouTube API error for channel {channel_id}: {e}")
            break

        for item in data.get("items", []):
            vid_id = item.get("id", {}).get("videoId")
            title = item.get("snippet", {}).get("title", "")
            if vid_id:
                videos.append({"id": vid_id, "title": title})

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return videos


def get_transcript(video_id: str) -> Optional[str]:
    """Fetch transcript for a YouTube video (French preferred, English fallback)."""
    if not TRANSCRIPT_API_AVAILABLE:
        return None
    try:
        entries = YouTubeTranscriptApi.get_transcript(video_id, languages=["fr", "en"])
        return " ".join(e["text"] for e in entries)
    except Exception as e:
        logger.debug(f"No transcript for {video_id}: {e}")
        return None


def clean_text(text: str) -> str:
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_words: int = 200, overlap: int = 30) -> list[str]:
    words = text.split()
    step = max(1, chunk_words - overlap)
    return [
        " ".join(words[i: i + chunk_words])
        for i in range(0, len(words), step)
        if words[i: i + chunk_words]
    ]


def extract_destinations_from_title(title: str) -> list[str]:
    """Best-effort: extract destination names from a video title."""
    # Remove common non-destination words
    stopwords = {
        "vlog", "travel", "trip", "guide", "day", "days", "week", "food",
        "best", "top", "things", "to", "do", "in", "at", "the", "my", "our",
        "voyage", "jour", "jours", "semaine", "visite", "visiter", "découvrir",
    }
    words = re.findall(r"[A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+", title)
    return [w for w in words if w.lower() not in stopwords and len(w) > 3]


def ingest_channel(channel_id: str, channel_name: str, db, api_key: str,
                   max_videos: int = 30) -> dict:
    """Fetch videos, transcripts, chunk them and upsert into rag_chunks."""
    stats = {"videos_found": 0, "transcribed": 0, "chunks": 0, "skipped": 0}

    videos = get_channel_videos(channel_id, api_key, max_results=max_videos)
    stats["videos_found"] = len(videos)
    logger.info(f"{channel_name}: {len(videos)} videos found")

    for video in videos:
        vid_id = video["id"]
        title = video["title"]

        transcript = get_transcript(vid_id)
        if not transcript:
            stats["skipped"] += 1
            continue

        stats["transcribed"] += 1
        cleaned = clean_text(transcript)
        chunks = chunk_text(cleaned)
        destinations = extract_destinations_from_title(title)
        destination = destinations[0] if destinations else None

        rows = [
            {
                "channel": channel_name,
                "video_id": vid_id,
                "video_title": title,
                "destination": destination,
                "chunk_text": chunk,
            }
            for chunk in chunks
        ]

        try:
            db.table("rag_chunks").upsert(
                rows,
                on_conflict="video_id,md5(chunk_text)",
            ).execute()
            stats["chunks"] += len(rows)
        except Exception as e:
            logger.error(f"Failed to upsert chunks for {vid_id}: {e}")

        time.sleep(0.3)  # rate limit

    logger.info(f"{channel_name}: {stats}")
    return stats
