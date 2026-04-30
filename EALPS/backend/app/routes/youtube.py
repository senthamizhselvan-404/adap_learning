"""
youtube.py — YouTube skill tracking endpoints for the EALPS React app.

Endpoints:
  POST /api/v1/youtube/match-skill   — Claude AI skill detection
  POST /api/v1/youtube/track         — Log watch progress to DB (JWT optional)
  GET  /api/v1/youtube/skills        — List available skills
  GET  /api/v1/youtube/history       — Learner's watch history (JWT required)
"""
import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from ..models import Learner, Skill, VideoTrack
from ..extensions import db

youtube_bp = Blueprint('youtube', __name__)

# ── CORS: allow the React dev server and standalone tracker pages ──────────────

@youtube_bp.after_request
def add_cors(response):
    origin = request.headers.get('Origin', '')
    allowed = {'http://localhost:5173', 'http://localhost:3000', 'http://localhost:5000'}
    if origin in allowed or not origin:
        response.headers['Access-Control-Allow-Origin'] = origin or '*'
    else:
        response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

@youtube_bp.route('/match-skill', methods=['OPTIONS'])
@youtube_bp.route('/track',       methods=['OPTIONS'])
@youtube_bp.route('/history',     methods=['OPTIONS'])
@youtube_bp.route('/skills',      methods=['OPTIONS'])
def preflight():
    return '', 204


# ── Claude AI skill matching ───────────────────────────────────────────────────

_DEFAULT_SKILLS = [
    "Python Basics", "Python OOP", "Data Structures", "Algorithms",
    "React Fundamentals", "React Hooks", "State Management", "REST APIs",
    "FastAPI", "SQL Databases", "NoSQL Databases", "Machine Learning",
    "Deep Learning", "Data Analysis", "CSS & Styling", "HTML Basics",
    "JavaScript ES6", "Git & Version Control", "Docker", "System Design",
]


def _match_with_claude(video_title: str, video_description: str = "") -> dict:
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return {
            "matched_skill": None, "confidence": 0.0,
            "reasoning": "ANTHROPIC_API_KEY not set — add it to your .env file.",
            "is_relevant": False, "should_log": False,
        }

    db_skills = [s.skill_name for s in Skill.query.filter_by(is_active=True).all()]
    skills = db_skills if db_skills else _DEFAULT_SKILLS

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
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        result["should_log"] = bool(
            result.get("is_relevant") and result.get("confidence", 0) >= 0.6
        )
        return result
    except json.JSONDecodeError:
        return {
            "matched_skill": None, "confidence": 0.0,
            "reasoning": "Claude response could not be parsed.",
            "is_relevant": False, "should_log": False,
        }
    except Exception as exc:
        return {
            "matched_skill": None, "confidence": 0.0,
            "reasoning": f"Claude error: {exc}",
            "is_relevant": False, "should_log": False,
        }


# ── POST /match-skill ──────────────────────────────────────────────────────────

@youtube_bp.route('/match-skill', methods=['POST'])
def match_skill():
    data = request.get_json(silent=True) or {}
    title = data.get('video_title', '').strip()
    if not title:
        return jsonify({'error': 'video_title is required'}), 400
    return jsonify(_match_with_claude(title, data.get('video_description', '')))


# ── POST /track ────────────────────────────────────────────────────────────────

@youtube_bp.route('/track', methods=['POST'])
def track_video():
    data = request.get_json(silent=True) or {}
    video_id = data.get('video_id', '').strip()
    title    = data.get('video_title', '').strip()

    if not video_id:
        return jsonify({'error': 'video_id is required'}), 400

    # Resolve learner — JWT takes priority, fallback to body user_id
    learner_id = None
    try:
        verify_jwt_in_request(optional=True)
        learner_id = get_jwt_identity()
    except Exception:
        pass

    if not learner_id:
        learner_id = data.get('user_id', '').strip() or None

    # Match skill via Claude
    match = _match_with_claude(title, data.get('video_description', ''))

    # Guests and unknown users: just return the match without persisting
    if not learner_id or learner_id == 'guest-user':
        return jsonify({
            'skill_match':     match,
            'progress_logged': False,
            'message':         'Login to save your progress',
        })

    learner = db.session.get(Learner, learner_id)
    if not learner:
        return jsonify({'error': 'Learner not found'}), 404

    watched = max(0, int(data.get('watched_seconds', 0)))

    # Resolve matching Skill row (may be None if Claude couldn't match)
    skill = None
    if match.get('matched_skill'):
        skill = Skill.query.filter_by(
            skill_name=match['matched_skill'], is_active=True
        ).first()

    logged = False
    if match.get('should_log'):
        track = VideoTrack.query.filter_by(
            learner_id=learner_id, video_id=video_id
        ).first()
        if not track:
            track = VideoTrack(
                learner_id=learner_id,
                video_id=video_id,
                video_title=title,
                skill_id=skill.skill_id if skill else None,
                total_watched_seconds=watched,
            )
            db.session.add(track)
        else:
            track.total_watched_seconds += watched
            track.updated_at = datetime.utcnow()
            if skill and not track.skill_id:
                track.skill_id = skill.skill_id
        db.session.commit()
        logged = True

    return jsonify({
        'skill_match':     match,
        'progress_logged': logged,
        'message': (
            f"Progress saved for '{match['matched_skill']}'"
            if logged
            else "Video not logged (low confidence or off-topic)"
        ),
    })


# ── GET /skills ────────────────────────────────────────────────────────────────

@youtube_bp.route('/skills', methods=['GET'])
def get_skills():
    db_skills = [s.skill_name for s in Skill.query.filter_by(is_active=True).all()]
    skills = db_skills if db_skills else _DEFAULT_SKILLS
    return jsonify({'skills': skills, 'total': len(skills)})


# ── GET /history ───────────────────────────────────────────────────────────────

@youtube_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    learner_id = get_jwt_identity()
    tracks = (
        VideoTrack.query
        .filter_by(learner_id=learner_id)
        .order_by(VideoTrack.updated_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for t in tracks:
        skill = db.session.get(Skill, t.skill_id) if t.skill_id else None
        result.append({
            **t.to_dict(),
            'skill_name':     skill.skill_name if skill else None,
            'watched_minutes': round(t.total_watched_seconds / 60, 1),
        })
    return jsonify({'history': result, 'total': len(result)})
