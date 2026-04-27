"""Ingest YouTube travel channel transcripts into Supabase rag_chunks table."""

import hashlib
import logging
import re
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _transcript_api = YouTubeTranscriptApi()
    TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    _transcript_api = None
    TRANSCRIPT_API_AVAILABLE = False
    logger.warning("youtube-transcript-api not installed")


def _resolve_uploads_playlist(handle: str, api_key: str) -> str | None:
    """Resolve a channel handle to its uploads playlist ID."""
    # Strip leading @ if present
    handle = handle.lstrip("@")
    try:
        resp = httpx.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "contentDetails", "forHandle": handle, "key": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if items:
            return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except Exception as e:
        logger.error(f"Failed to resolve handle @{handle}: {e}")
    return None


def get_channel_videos(channel_id: str, api_key: str, max_results: int = 50,
                       handle: str = "") -> list[dict]:
    """Fetch recent video IDs from a YouTube channel via uploads playlist."""
    # Resolve uploads playlist from handle (preferred) or derive from channel_id
    playlist_id = None
    if handle:
        playlist_id = _resolve_uploads_playlist(handle, api_key)
    if not playlist_id and channel_id.startswith("UC"):
        # Uploads playlist = replace UC prefix with UU
        playlist_id = "UU" + channel_id[2:]

    if not playlist_id:
        logger.error(f"Cannot resolve uploads playlist for {channel_id}")
        return []

    videos = []
    page_token = None

    while len(videos) < max_results:
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": min(50, max_results - len(videos)),
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            resp = httpx.get(
                "https://www.googleapis.com/youtube/v3/playlistItems",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"YouTube playlist error for {playlist_id}: {e}")
            break

        for item in data.get("items", []):
            vid_id = item.get("snippet", {}).get("resourceId", {}).get("videoId")
            title = item.get("snippet", {}).get("title", "")
            if vid_id:
                videos.append({"id": vid_id, "title": title})

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return videos


def get_transcript(video_id: str) -> Optional[str]:
    """Fetch transcript for a YouTube video (French preferred, English fallback)."""
    if not TRANSCRIPT_API_AVAILABLE or _transcript_api is None:
        return None
    try:
        result = _transcript_api.fetch(video_id, languages=["fr", "en"])
        return " ".join(s.text for s in result)
    except Exception:
        try:
            # Fallback: pick any available transcript
            tlist = _transcript_api.list(video_id)
            transcript = next(iter(tlist))
            result = transcript.fetch()
            return " ".join(s.text for s in result)
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
                   max_videos: int = 30, **kwargs) -> dict:
    """Fetch videos, transcripts, chunk them and upsert into rag_chunks."""
    stats = {"videos_found": 0, "transcribed": 0, "chunks": 0, "skipped": 0}

    handle = kwargs.get("handle", "")
    videos = get_channel_videos(channel_id, api_key, max_results=max_videos, handle=handle)
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
                "chunk_hash": hashlib.md5(chunk.encode()).hexdigest(),
            }
            for chunk in chunks
        ]

        try:
            db.table("rag_chunks").upsert(
                rows,
                on_conflict="video_id,chunk_hash",
            ).execute()
            stats["chunks"] += len(rows)
        except Exception as e:
            logger.error(f"Failed to upsert chunks for {vid_id}: {e}")

        time.sleep(0.3)  # rate limit

    logger.info(f"{channel_name}: {stats}")
    return stats
