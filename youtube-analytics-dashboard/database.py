"""
database.py
Handles all persistent storage for tracked videos using SQLite.
SQLite is a single-file database — no server setup needed, and it
survives app restarts as long as the file itself isn't wiped
(see README for a note on this in free-tier hosting).
"""

import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager

DB_PATH = "youtube_dashboard.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create the videos table if it doesn't already exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                channel_title TEXT,
                published_at TEXT,
                thumbnail_url TEXT,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                first_tracked_at TEXT,
                last_updated_at TEXT
            )
            """
        )


def upsert_video(data: dict):
    """Insert a new tracked video, or update it if it already exists."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT video_id FROM videos WHERE video_id = ?", (data["video_id"],)
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE videos
                SET title = ?, channel_title = ?, published_at = ?,
                    thumbnail_url = ?, views = ?, likes = ?, comments = ?,
                    last_updated_at = ?
                WHERE video_id = ?
                """,
                (
                    data["title"],
                    data["channel_title"],
                    data["published_at"],
                    data["thumbnail_url"],
                    data["views"],
                    data["likes"],
                    data["comments"],
                    now,
                    data["video_id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO videos
                (video_id, title, channel_title, published_at, thumbnail_url,
                 views, likes, comments, first_tracked_at, last_updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["video_id"],
                    data["title"],
                    data["channel_title"],
                    data["published_at"],
                    data["thumbnail_url"],
                    data["views"],
                    data["likes"],
                    data["comments"],
                    now,
                    now,
                ),
            )


def get_all_videos():
    """Return all tracked videos, most recently updated first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM videos ORDER BY last_updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_all_video_ids():
    with get_connection() as conn:
        rows = conn.execute("SELECT video_id FROM videos").fetchall()
        return [row["video_id"] for row in rows]


def delete_video(video_id: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM videos WHERE video_id = ?", (video_id,))


def get_summary_stats():
    videos = get_all_videos()
    return {
        "total_videos": len(videos),
        "total_views": sum(v["views"] for v in videos),
        "total_likes": sum(v["likes"] for v in videos),
        "total_comments": sum(v["comments"] for v in videos),
    }
