"""
metadata.py - Fetch YouTube video metadata (title, thumbnail, duration, channel)
"""

import requests
import json
import re


def fetch_metadata(video_id: str) -> dict:
    """
    Fetch video metadata using YouTube oEmbed API + noembed fallback.
    Returns dict with title, author, thumbnail_url, duration_str.
    """
    # Try YouTube oEmbed (no API key needed)
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        resp = requests.get(oembed_url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            thumbnail = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
            return {
                "title": data.get("title", "Unknown Title"),
                "author": data.get("author_name", "Unknown Channel"),
                "thumbnail_url": thumbnail,
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
    except Exception:
        pass

    # Fallback: minimal info
    return {
        "title": f"Video ({video_id})",
        "author": "Unknown",
        "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }
