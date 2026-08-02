"""
youtube_api.py
Thin wrapper around the YouTube Data API v3 "videos" endpoint.
Handles parsing video IDs out of pasted URLs and fetching stats.
"""

import re
import requests

API_BASE = "https://www.googleapis.com/youtube/v3/videos"

# Matches raw 11-char video IDs, and common URL shapes:
# watch?v=ID, youtu.be/ID, /embed/ID, /shorts/ID, /v/ID
_ID_PATTERNS = [
    r"(?:v=|\/embed\/|youtu\.be\/|\/v\/|\/shorts\/)([a-zA-Z0-9_-]{11})",
]


def extract_video_id(url_or_id: str):
    """Return an 11-char YouTube video ID from a pasted URL or raw ID, or None."""
    text = url_or_id.strip()
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", text):
        return text
    for pattern in _ID_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


class YouTubeAPIError(Exception):
    pass


def fetch_video_details(video_id: str, api_key: str) -> dict:
    """Fetch title, publish date, views, likes, comments for one video."""
    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key,
    }
    try:
        response = requests.get(API_BASE, params=params, timeout=10)
    except requests.RequestException as exc:
        raise YouTubeAPIError(f"Network error contacting YouTube API: {exc}") from exc

    if response.status_code == 403:
        raise YouTubeAPIError(
            "YouTube API returned 403 — check that your API key is valid, "
            "the YouTube Data API v3 is enabled for it, and you haven't hit your quota."
        )
    if response.status_code != 200:
        raise YouTubeAPIError(
            f"YouTube API error ({response.status_code}): {response.text[:200]}"
        )

    payload = response.json()
    items = payload.get("items", [])
    if not items:
        raise YouTubeAPIError(
            "No video found for that ID. It may be private, deleted, or mistyped."
        )

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    thumbnails = snippet.get("thumbnails", {})
    thumb = thumbnails.get("medium") or thumbnails.get("default") or {}

    return {
        "video_id": video_id,
        "title": snippet.get("title", "Untitled"),
        "channel_title": snippet.get("channelTitle", "Unknown channel"),
        "published_at": snippet.get("publishedAt", ""),
        "thumbnail_url": thumb.get("url", ""),
        # statistics.commentCount / likeCount can be absent if disabled
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
    }
