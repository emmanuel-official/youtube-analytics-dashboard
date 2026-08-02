"""
app.py
YouTube Analytics Dashboard — a lightweight Streamlit app to track
public video stats (views, likes, comments) over time.
"""

import streamlit as st

from database import (
    init_db,
    upsert_video,
    get_all_videos,
    get_all_video_ids,
    delete_video,
    get_summary_stats,
)
from youtube_api import extract_video_id, fetch_video_details, YouTubeAPIError

st.set_page_config(
    page_title="YouTube Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------
# Styling — dark theme with a neon accent, card grid, glowing metrics
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at top left, #0d1520 0%, #0a0e12 60%);
    }
    .dashboard-title {
        background: linear-gradient(90deg, #00ff9d, #00c2ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.2rem;
        padding-bottom: 0.2rem;
        margin-bottom: 0;
    }
    .dashboard-subtitle {
        color: #6b7785;
        font-size: 0.9rem;
        margin-top: -0.4rem;
        margin-bottom: 1.4rem;
    }
    .metric-card {
        background: #11161d;
        border: 1px solid #1f2933;
        border-radius: 14px;
        padding: 1.1rem 1rem;
        text-align: center;
        box-shadow: 0 0 20px rgba(0,255,157,0.04);
        transition: all 0.2s ease;
    }
    .metric-card:hover {
        border-color: #00ff9d;
        box-shadow: 0 0 22px rgba(0,255,157,0.18);
    }
    .metric-label {
        color: #8b949e;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        color: #e6edf3;
        font-size: 1.7rem;
        font-weight: 700;
    }
    .video-card {
        background: #11161d;
        border: 1px solid #1f2933;
        border-radius: 14px;
        padding: 0.9rem;
        margin-bottom: 0.5rem;
        transition: all 0.2s ease;
    }
    .video-card:hover {
        border-color: #00c2ff;
    }
    .video-thumb {
        width: 100%;
        border-radius: 10px;
        margin-bottom: 0.6rem;
        display: block;
    }
    .video-title {
        color: #e6edf3;
        font-weight: 600;
        font-size: 0.92rem;
        margin-bottom: 0.3rem;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        min-height: 2.4em;
    }
    .video-channel {
        color: #8b949e;
        font-size: 0.75rem;
        margin-bottom: 0.55rem;
    }
    .video-stats {
        display: flex;
        gap: 0.9rem;
        color: #00ff9d;
        font-size: 0.82rem;
        font-weight: 600;
        margin-bottom: 0.35rem;
    }
    .video-updated {
        color: #566270;
        font-size: 0.7rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_db()


# ----------------------------------------------------------------------
# API key resolution: prefer Streamlit secrets (used in deployment),
# fall back to a session-only sidebar input for local testing.
# ----------------------------------------------------------------------
def get_api_key():
    if "YOUTUBE_API_KEY" in st.secrets:
        return st.secrets["YOUTUBE_API_KEY"]
    return st.session_state.get("manual_api_key", "")


with st.sidebar:
    st.markdown("### 🔑 API Configuration")
    if "YOUTUBE_API_KEY" in st.secrets:
        st.success("API key loaded from Streamlit secrets.")
    else:
        st.session_state["manual_api_key"] = st.text_input(
            "YouTube Data API v3 Key",
            type="password",
            value=st.session_state.get("manual_api_key", ""),
            help="Kept only in this browser session — never written to disk.",
        )
        st.caption(
            "For your deployed app, set this permanently under "
            "Streamlit Cloud → App settings → Secrets instead."
        )
    st.divider()
    st.markdown("### ℹ️ About")
    st.caption(
        "Paste a YouTube video link or ID to start tracking it. "
        "Stats are stored locally in a SQLite database and persist "
        "between sessions."
    )

api_key = get_api_key()

# ----------------------------------------------------------------------
# Header + track input
# ----------------------------------------------------------------------
st.markdown('<div class="dashboard-title">📊 YouTube Analytics Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-subtitle">Track public video performance over time</div>', unsafe_allow_html=True)

col_input, col_button = st.columns([5, 1])
with col_input:
    video_input = st.text_input(
        "Paste a YouTube video link or video ID",
        label_visibility="collapsed",
        placeholder="https://www.youtube.com/watch?v=... or dQw4w9WgXcQ",
        key="video_input",
    )
with col_button:
    track_clicked = st.button("➕ Track Video", use_container_width=True)

if track_clicked:
    if not api_key:
        st.error("Add your YouTube Data API v3 key in the sidebar first.")
    elif not video_input.strip():
        st.error("Paste a video link or ID first.")
    else:
        vid = extract_video_id(video_input)
        if not vid:
            st.error("Couldn't find a valid video ID in that input.")
        else:
            try:
                with st.spinner("Fetching video data..."):
                    data = fetch_video_details(vid, api_key)
                    upsert_video(data)
                st.success(f"Now tracking: {data['title']}")
                st.rerun()
            except YouTubeAPIError as e:
                st.error(str(e))
            except Exception as e:  # noqa: BLE001 — surface anything unexpected to the user
                st.error(f"Unexpected error: {e}")

st.divider()

# ----------------------------------------------------------------------
# Refresh all
# ----------------------------------------------------------------------
videos = get_all_videos()

refresh_col, _ = st.columns([1, 5])
with refresh_col:
    if st.button("🔄 Refresh All Stats", use_container_width=True, disabled=(len(videos) == 0)):
        if not api_key:
            st.error("Add your YouTube API key in the sidebar first.")
        else:
            ids = get_all_video_ids()
            progress = st.progress(0, text="Refreshing...")
            errors = []
            for i, vid in enumerate(ids):
                try:
                    data = fetch_video_details(vid, api_key)
                    upsert_video(data)
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{vid}: {e}")
                progress.progress((i + 1) / len(ids), text=f"Refreshing {i + 1}/{len(ids)}")
            progress.empty()
            if errors:
                st.warning("Some videos failed to refresh:\n" + "\n".join(errors))
            else:
                st.success("All videos refreshed!")
            st.rerun()

# ----------------------------------------------------------------------
# Summary metrics row
# ----------------------------------------------------------------------
stats = get_summary_stats()


def format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


m1, m2, m3, m4 = st.columns(4)
for col, label, value in [
    (m1, "Total Views", stats["total_views"]),
    (m2, "Total Likes", stats["total_likes"]),
    (m3, "Total Comments", stats["total_comments"]),
    (m4, "Videos Tracked", stats["total_videos"]),
]:
    with col:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{format_number(value)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# ----------------------------------------------------------------------
# Video card grid
# ----------------------------------------------------------------------
st.markdown("### 🎬 Tracked Videos")

if not videos:
    st.info("No videos tracked yet. Paste a link above to get started.")
else:
    cols_per_row = 3
    for i in range(0, len(videos), cols_per_row):
        row_videos = videos[i : i + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, video in zip(cols, row_videos):
            with col:
                published = video["published_at"][:10] if video["published_at"] else "—"
                updated = (
                    video["last_updated_at"][:16].replace("T", " ")
                    if video["last_updated_at"]
                    else "—"
                )
                st.markdown(
                    f"""
                    <div class="video-card">
                        <img src="{video['thumbnail_url']}" class="video-thumb" />
                        <div class="video-title">{video['title']}</div>
                        <div class="video-channel">{video['channel_title']} · Published {published}</div>
                        <div class="video-stats">
                            <span>👁 {format_number(video['views'])}</span>
                            <span>👍 {format_number(video['likes'])}</span>
                            <span>💬 {format_number(video['comments'])}</span>
                        </div>
                        <div class="video-updated">Last updated: {updated} UTC</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("🗑 Remove", key=f"del_{video['video_id']}", use_container_width=True):
                    delete_video(video["video_id"])
                    st.rerun()
