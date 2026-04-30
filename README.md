# YouTube Skill Tracker
## Drop-in integration for your Learning Pathway app

---

## Files in this folder

| File | What it does |
|------|-------------|
| `youtube-tracker.js` | Frontend — embed player + track watch time |
| `youtube_skill_matcher.py` | Backend — Claude AI skill matching + FastAPI routes |
| `example.html` | Working example showing how to use both |

---

## Setup in 3 steps

### Step 1 — Backend (Python)

```bash
pip install anthropic fastapi uvicorn
export ANTHROPIC_API_KEY="sk-ant-YOUR_KEY_HERE"
```

In your `main.py`:

```python
from fastapi import FastAPI
from youtube_skill_matcher import router   # <-- import the router

app = FastAPI()
app.include_router(router)                 # <-- one line to add all endpoints
```

Run it:
```bash
uvicorn main:app --reload
```

### Step 2 — Frontend (HTML)

Copy `youtube-tracker.js` into your project folder, then:

```html
<!-- 1. Add a div with your YouTube video ID -->
<div data-video-id="YOUTUBE_VIDEO_ID_HERE"></div>

<!-- 2. Add the script tag (just once, before </body>) -->
<script src="youtube-tracker.js"></script>
```

That's it. The tracker automatically:
- Embeds the YouTube player
- Detects the skill using Claude AI
- Shows a skill badge below the video
- Logs progress every 30 seconds

### Step 3 — Connect your database

In `youtube_skill_matcher.py`, find the `_log_progress()` function
and replace the `print()` with your real database write:

```python
def _log_progress(user_id, skill, watched_seconds, video_id):
    # Replace this with your DB logic:
    db.execute(
        "INSERT INTO progress (user_id, skill, seconds, video_id) VALUES (?, ?, ?, ?)",
        [user_id, skill, watched_seconds, video_id]
    )
    return True
```

---

## Customize your skill list

Open `youtube_skill_matcher.py` and edit the `SKILL_GRAPH` list:

```python
SKILL_GRAPH = [
    "Your Skill 1",
    "Your Skill 2",
    ...
]
```

---

## API endpoints (auto-created)

| Method | URL | What it does |
|--------|-----|-------------|
| POST | `/api/youtube/match-skill` | Match a video title to a skill |
| POST | `/api/youtube/track` | Track + log learner progress |
| GET  | `/api/youtube/skills` | List all skills in the curriculum |
