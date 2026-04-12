"""
transcript.py - Fetch and parse YouTube transcripts with timestamps
Compatible with youtube-transcript-api v1.x
"""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound, TranscriptsDisabled, VideoUnavailable,
    CouldNotRetrieveTranscript,
)
import re


def extract_video_id(url: str) -> str | None:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
        r"^([0-9A-Za-z_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_transcript(video_id: str) -> list[dict]:
    """
    Fetch transcript for a YouTube video.
    Returns list of {text, start, duration} dicts.
    Compatible with youtube-transcript-api v1.x (instance-based API).
    """
    api = YouTubeTranscriptApi()

    # Try English first
    try:
        fetched = api.fetch(video_id, languages=['en'])
        return [{"text": s.text, "start": s.start, "duration": s.duration} for s in fetched]
    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video.")
    except VideoUnavailable:
        raise ValueError("Video is unavailable or private.")
    except (NoTranscriptFound, CouldNotRetrieveTranscript):
        pass  # Will try other languages below
    except Exception:
        pass  # Will try other languages below

    # Fallback: discover all available languages, use the first one
    try:
        transcript_list = api.list(video_id)
        available = [t.language_code for t in transcript_list]
        if not available:
            raise ValueError("No transcripts available for this video.")
        fetched = api.fetch(video_id, languages=available)
        return [{"text": s.text, "start": s.start, "duration": s.duration} for s in fetched]
    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video.")
    except VideoUnavailable:
        raise ValueError("Video is unavailable or private.")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not fetch transcript: {str(e)}")


def chunk_transcript(transcript: list[dict], chunk_size: int = 300, overlap: int = 50) -> list[dict]:
    """
    Chunk transcript into overlapping windows, preserving timestamps.
    Each chunk: {text, start_time, end_time, chunk_id}
    """
    chunks = []
    words_buffer = []
    word_timestamps = []

    # Flatten transcript into word-level with timestamps
    for entry in transcript:
        words = entry['text'].split()
        start = entry['start']
        duration = entry.get('duration', 2.0)
        for i, word in enumerate(words):
            t = start + (duration * i / max(len(words), 1))
            words_buffer.append(word)
            word_timestamps.append(t)

    # Slide window
    step = chunk_size - overlap
    chunk_id = 0
    i = 0
    while i < len(words_buffer):
        end_idx = min(i + chunk_size, len(words_buffer))
        chunk_words = words_buffer[i:end_idx]
        chunk_times = word_timestamps[i:end_idx]

        chunk_text = " ".join(chunk_words)
        start_time = chunk_times[0]
        end_time = chunk_times[-1]

        chunks.append({
            "chunk_id": chunk_id,
            "text": chunk_text,
            "start_time": start_time,
            "end_time": end_time,
        })
        chunk_id += 1
        i += step
        if end_idx == len(words_buffer):
            break

    return chunks


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS string."""
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def make_youtube_link(video_id: str, seconds: float) -> str:
    """Create a deep-link YouTube URL at a specific timestamp."""
    t = int(seconds)
    return f"https://www.youtube.com/watch?v={video_id}&t={t}s"