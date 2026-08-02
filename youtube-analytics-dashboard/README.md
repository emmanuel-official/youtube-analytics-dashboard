# 📊 YouTube Analytics Dashboard

A lightweight, self-hosted dashboard to track public YouTube video stats
(views, likes, comments) over time. Built with **Streamlit** + **SQLite** —
no server admin needed, free to host, accessible from any browser or phone.

## Project structure

```
youtube-analytics-dashboard/
├── app.py                          # Main Streamlit app (UI + logic)
├── database.py                     # SQLite persistence layer
├── youtube_api.py                  # YouTube Data API v3 wrapper
├── requirements.txt                # Python dependencies
├── .gitignore                      # Keeps secrets/DB out of git
├── README.md
└── .streamlit/
    ├── config.toml                 # Dark theme config
    └── secrets.toml.example        # Template — copy, don't commit
```

The SQLite database file (`youtube_dashboard.db`) is created automatically
the first time you run the app — no setup required.

---

## 1. Get a YouTube Data API v3 key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or pick an existing one).
3. Go to **APIs & Services → Library**, search **YouTube Data API v3**, click **Enable**.
4. Go to **APIs & Services → Credentials → Create Credentials → API key**.
5. Click **Restrict key** and limit it to the YouTube Data API v3 — this
   stops the key from being usable for anything else if it ever leaks.

> ⚠️ **If you've ever pasted an API key into a chat, doc, or public repo,
> treat it as burned.** Delete it and generate a new one. Never commit a
> real key to GitHub — this project's `.gitignore` and `secrets.toml`
> pattern are set up specifically to prevent that.

## 2. Run it locally (optional, to test first)

```bash
git clone <your-repo-url>
cd youtube-analytics-dashboard
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Add your key locally (this file is gitignored, never committed)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# then edit .streamlit/secrets.toml and paste your real key in

streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

---

## 3. Deploy for free — Streamlit Community Cloud (recommended)

This is the easiest path since the app is already a Streamlit app.

1. **Push the project to GitHub.**
   Create a new repo and push everything *except* your real
   `.streamlit/secrets.toml` (it's already gitignored — double check it
   didn't get committed with `git status`).

2. **Go to [share.streamlit.io](https://share.streamlit.io)** and sign in
   with GitHub.

3. Click **New app**, select your repo, branch (`main`), and set the
   main file path to `app.py`.

4. Before deploying (or right after, under **Advanced settings → Secrets**
   / **App settings → Secrets**), paste in:

   ```toml
   YOUTUBE_API_KEY = "your_real_key_here"
   ```

   This keeps the key out of your repository entirely — the app reads it
   via `st.secrets` at runtime.

5. Click **Deploy**. You'll get a public URL like
   `https://your-app-name.streamlit.app` — open it from any device.

### ⚠️ Important: free-tier storage is not permanent

Streamlit Community Cloud's filesystem is **ephemeral** — if the app
goes to sleep from inactivity and restarts, or is redeployed, the
`youtube_dashboard.db` file resets to empty. For a personal tracker
that's fine to start with, but if you want your tracked videos to
survive restarts long-term, upgrade the storage layer later to a free
hosted database:

- **[Supabase](https://supabase.com)** (free Postgres) — swap
  `database.py`'s SQLite calls for `psycopg2` or `supabase-py`.
- **[Turso](https://turso.tech)** (free hosted SQLite, libSQL) — nearly
  a drop-in replacement, minimal code change from what's here.

The rest of the app (UI, API calls) stays identical either way — only
`database.py` would need updating.

---

## 4. Alternative: deploy on Render

If you'd rather not use Streamlit Cloud:

1. Push the repo to GitHub as above.
2. On [Render](https://render.com), click **New → Web Service**, connect
   your repo.
3. Set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. Under **Environment**, add an environment variable:
   `YOUTUBE_API_KEY = your_real_key_here`
5. You'll need one small code tweak so the app also checks environment
   variables (Render doesn't use `st.secrets` the same way Streamlit
   Cloud does) — add this near the top of `app.py`, right after the
   imports:

   ```python
   import os
   if "YOUTUBE_API_KEY" not in st.secrets and os.environ.get("YOUTUBE_API_KEY"):
       st.secrets._secrets = {"YOUTUBE_API_KEY": os.environ["YOUTUBE_API_KEY"]}
   ```

   (Streamlit Cloud users can skip this — its native Secrets manager
   already populates `st.secrets` directly.)

Render's free web services also spin down on inactivity and use
ephemeral disk, so the same SQLite caveat above applies there too.

---

## Notes on quota

The YouTube Data API v3 free tier gives you **10,000 units/day**. Each
video lookup (`videos.list`) costs **1 unit**, so tracking dozens of
videos and refreshing them regularly is nowhere close to the limit for
personal use.

## Features included

- ➕ Track any public video by pasting a link or raw video ID
- 🔄 One-click refresh of all tracked videos' stats
- 📈 Summary row: total views, likes, comments, videos tracked
- 🗑 Remove videos you no longer want to track
- 🌙 Dark theme with a card-grid layout, responsive across screen sizes
