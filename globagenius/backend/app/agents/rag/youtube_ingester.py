"""Ingest YouTube transcripts into RAG vector database."""

import logging
from typing import Optional
import re

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

logger = logging.getLogger(__name__)


def get_channel_videos(channel_id: str, max_results: int = 50) -> list[dict]:
    """
    Fetch video IDs and metadata from a YouTube channel.

    NOTE: This requires YouTube Data API which is not free.
    For now, this is a placeholder. In production, use youtube-dl or pytube
    to scrape the channel's latest videos.
    """
    logger.warning(f"Channel video fetch not yet implemented for {channel_id}")
    return []


def get_transcript(video_id: str) -> Optional[str]:
    """
    Fetch transcript for a YouTube video.

    Args:
        video_id: YouTube video ID (e.g., "dQw4w9WgXcQ")

    Returns:
        Full transcript text, or None if transcript unavailable
    """
    if YouTubeTranscriptApi is None:
        logger.error("youtube-transcript-api not installed")
        return None

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "fr"])
        # Combine all transcript entries into one text
        text = " ".join([entry["text"] for entry in transcript_list])
        return text
    except Exception as e:
        logger.warning(f"Failed to fetch transcript for video {video_id}: {e}")
        return None


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Input text
        chunk_size: Target chunk size in tokens (approximate, based on word count)
        overlap: Overlap between chunks in tokens

    Returns:
        List of text chunks
    """
    # Simple word-based chunking (1 word ≈ 1.3 tokens, so divide by 1.3)
    words = text.split()
    word_chunk_size = max(1, int(chunk_size / 1.3))
    overlap_words = max(1, int(overlap / 1.3))

    chunks = []
    for i in range(0, len(words), word_chunk_size - overlap_words):
        chunk = " ".join(words[i : i + word_chunk_size])
        if chunk.strip():
            chunks.append(chunk)

    return chunks


def clean_text(text: str) -> str:
    """Clean transcript text: remove extra whitespace, artifacts."""
    # Remove [Music], [Applause], etc.
    text = re.sub(r"\[.*?\]", "", text)
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def ingest_channel(
    channel_id: str,
    channel_name: str,
    db_client,
    max_videos: int = 50,
    chunk_size: int = 500,
    overlap: int = 50,
) -> dict:
    """
    Ingest all transcripts from a YouTube channel into vector DB.

    Args:
        channel_id: YouTube channel ID
        channel_name: Human-readable channel name
        db_client: ChromaDB client
        max_videos: Max videos to ingest per channel
        chunk_size: Token size per chunk
        overlap: Overlap between chunks

    Returns:
        Stats dict: {videos_found, videos_with_transcript, chunks_ingested, errors}
    """
    stats = {
        "videos_found": 0,
        "videos_with_transcript": 0,
        "chunks_ingested": 0,
        "errors": [],
    }

    # Placeholder: get_channel_videos is not yet implemented
    videos = get_channel_videos(channel_id, max_results=max_videos)
    stats["videos_found"] = len(videos)

    for video in videos:
        video_id = video.get("id")
        video_title = video.get("title", "Unknown")

        # Fetch transcript
        transcript = get_transcript(video_id)
        if not transcript:
            continue

        stats["videos_with_transcript"] += 1

        # Clean and chunk
        cleaned = clean_text(transcript)
        chunks = chunk_text(cleaned, chunk_size=chunk_size, overlap=overlap)

        # Ingest chunks into vector DB
        for chunk in chunks:
            try:
                db_client.add_document(
                    text=chunk,
                    metadata={
                        "channel": channel_name,
                        "video_id": video_id,
                        "video_title": video_title,
                    },
                )
                stats["chunks_ingested"] += 1
            except Exception as e:
                logger.error(f"Failed to ingest chunk from {video_id}: {e}")
                stats["errors"].append(str(e))

    return stats
