# ============================================================
#  youtube_skill_matcher.py
#  Drop this file into your project.
#  It does 3 things:
#    1. Embeds a YouTube video in any page
#    2. Tracks what the learner watches
#    3. Uses Claude AI to identify the learning skill
#
#  SETUP (one time):
#    pip install anthropic fastapi uvicorn
#    export ANTHROPIC_API_KEY="sk-ant-..."
#
#  USAGE in your FastAPI app:
#    from youtube_skill_matcher import router
#    app.include_router(router)
# ============================================================

import os
import json
import anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# ── Anthropic client (reads ANTHROPIC_API_KEY from env) ──────
client = anthropic.Anthropic()

# ── Router (mounts to your existing FastAPI app) ─────────────
router = APIRouter(prefix="/api/youtube", tags=["YouTube Skill Tracker"])


# ────────────────────────────────────────────────────────────
#  STEP 1 ── CUSTOMIZE YOUR SKILL LIST
#  Replace these with the actual skills in your curriculum.
# ────────────────────────────────────────────────────────────
SKILL_GRAPH = [
    "Python Basics",
    "Python OOP",
    "Data Structures",
    "Algorithms",
    "React Fundamentals",
    "React Hooks",
    "State Management",
    "REST APIs",
    "FastAPI",
    "SQL Databases",
    "NoSQL Databases",
    "Machine Learning",
    "Deep Learning",
    "Data Analysis",
    "CSS & Styling",
    "HTML Basics",
    "JavaScript ES6",
    "Git & Version Control",
    "Docker",
    "System Design",
]


# ────────────────────────────────────────────────────────────
#  CORE FUNCTION ── match_skill_to_video()
#  Pass a YouTube video title (and optional description).
#  Returns: matched skill, confidence score, reasoning.
# ────────────────────────────────────────────────────────────
def match_skill_to_video(
    video_title: str,
    video_description: str = "",
    custom_skills: list[str] = None,
) -> dict:
    """
    Uses Claude AI to match a YouTube video to a skill
    in your learning curriculum.

    Args:
        video_title       : Title of the YouTube video
        video_description : (Optional) video description for better accuracy
        custom_skills     : (Optional) override the default SKILL_GRAPH list

    Returns dict:
        {
            "matched_skill" : "React Hooks"  or None,
            "confidence"    : 0.91,
            "reasoning"     : "The video covers useState and useEffect...",
            "is_relevant"   : True,
            "should_log"    : True   # False if confidence < 0.6
        }
    """
    skills = custom_skills or SKILL_GRAPH

    prompt = f"""You are a curriculum expert for an adaptive learning platform.

Given this YouTube video, identify which ONE skill it best matches from the list below.

VIDEO TITLE: {video_title}
VIDEO DESCRIPTION: {video_description or "Not provided"}

AVAILABLE SKILLS:
{json.dumps(skills, indent=2)}

Rules:
- Pick only ONE skill — the closest match.
- If the video is clearly off-topic (gaming, cooking, vlogs, music, etc.), set is_relevant to false.
- Be generous — a "Python tutorial for beginners" clearly maps to "Python Basics".

Respond ONLY in this exact JSON format with no extra text:
{{
  "matched_skill": "exact skill name from the list, or null if not relevant",
  "confidence": 0.0,
  "reasoning": "one sentence explanation",
  "is_relevant": true
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

        # Add a convenience flag — only log if confidence is high enough
        result["should_log"] = (
            result.get("is_relevant", False)
            and result.get("confidence", 0) >= 0.6
        )
        return result

    except json.JSONDecodeError:
        return {
            "matched_skill": None,
            "confidence": 0.0,
            "reasoning": "Claude response could not be parsed.",
            "is_relevant": False,
            "should_log": False,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")


# ────────────────────────────────────────────────────────────
#  PYDANTIC MODELS  (request / response shapes)
# ────────────────────────────────────────────────────────────
class VideoTrackRequest(BaseModel):
    user_id: str
    video_id: str
    video_title: str
    video_description: Optional[str] = ""
    watched_seconds: int
    total_duration: Optional[int] = 0


class SkillMatchRequest(BaseModel):
    video_title: str
    video_description: Optional[str] = ""


# ────────────────────────────────────────────────────────────
#  API ENDPOINTS
# ────────────────────────────────────────────────────────────

@router.post("/match-skill")
async def match_skill_endpoint(body: SkillMatchRequest):
    """
    Lightweight endpoint — just returns the skill match.
    Use this to show the learner what skill a video covers
    BEFORE they watch it.

    POST /api/youtube/match-skill
    Body: { "video_title": "...", "video_description": "..." }
    """
    result = match_skill_to_video(
        video_title=body.video_title,
        video_description=body.video_description,
    )
    return result


@router.post("/track")
async def track_video_endpoint(body: VideoTrackRequest):
    """
    Full tracking endpoint — matches skill AND logs progress.
    Call this when the learner finishes or pauses a video.

    POST /api/youtube/track
    Body: { user_id, video_id, video_title, watched_seconds, ... }
    """
    # 1. Match the skill
    match = match_skill_to_video(
        video_title=body.video_title,
        video_description=body.video_description,
    )

    # 2. Only log progress if Claude is confident enough
    logged = False
    if match["should_log"]:
        logged = _log_progress(
            user_id=body.user_id,
            skill=match["matched_skill"],
            watched_seconds=body.watched_seconds,
            video_id=body.video_id,
        )

    return {
        "skill_match": match,
        "progress_logged": logged,
        "message": (
            f"Progress saved for '{match['matched_skill']}'"
            if logged
            else "Video not logged (low confidence or off-topic)"
        ),
    }


@router.get("/skills")
async def get_skills():
    """
    Returns the full skill list.
    Useful for the frontend to display available skills.

    GET /api/youtube/skills
    """
    return {"skills": SKILL_GRAPH, "total": len(SKILL_GRAPH)}


# ────────────────────────────────────────────────────────────
#  HELPER ── _log_progress()
#  Replace this with your real database logic.
# ────────────────────────────────────────────────────────────
def _log_progress(
    user_id: str,
    skill: str,
    watched_seconds: int,
    video_id: str,
) -> bool:
    """
    TODO: Replace with your real database write.
    Example: INSERT INTO learner_progress (user_id, skill, seconds, video_id)

    For now prints to console so you can verify it works.
    """
    print(
        f"[PROGRESS] user={user_id} | skill='{skill}' "
        f"| watched={watched_seconds}s | video={video_id}"
    )
    return True
