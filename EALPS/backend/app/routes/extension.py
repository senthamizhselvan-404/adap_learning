"""
extension.py — API endpoints consumed by the EALPS Chrome extension.

Endpoints:
  GET  /api/v1/extension/skill-match?videoId=X[&userId=Y]
  POST /api/v1/extension/track
  POST /api/v1/extension/complete
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from ..models import Learner, Skill, VideoTrack
from ..extensions import db
import re

extension_bp = Blueprint('extension', __name__)

# ── CORS: allow requests from chrome-extension:// origins ─────────────────────

@extension_bp.after_request
def cors_headers(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@extension_bp.route('/skill-match',  methods=['OPTIONS'])
@extension_bp.route('/track',        methods=['OPTIONS'])
@extension_bp.route('/complete',     methods=['OPTIONS'])
def preflight():
    return '', 204


# ── Skill-matching helpers ─────────────────────────────────────────────────────

_STOP = {
    'the','a','an','and','or','in','on','at','to','for','of','with',
    'how','what','why','is','are','was','were','be','been',
    'tutorial','course','learn','learning','introduction','intro',
    'part','ep','episode','full','complete','beginners','advanced',
}

def _keywords(text: str) -> set:
    words = re.sub(r'[^a-z0-9 ]', ' ', text.lower()).split()
    return {w for w in words if len(w) > 2 and w not in _STOP}

def _match_skill(title: str, channel: str):
    """Return the Skill whose name best overlaps with the video title/channel."""
    words = _keywords(f'{title} {channel}')
    if not words:
        return None
    best, best_score = None, 0
    for skill in Skill.query.filter_by(is_active=True).all():
        score = len(words & _keywords(skill.skill_name))
        if score > best_score:
            best, best_score = skill, score
    return best if best_score > 0 else None


# ── GET /skill-match ───────────────────────────────────────────────────────────

@extension_bp.route('/skill-match', methods=['GET'])
def skill_match():
    video_id = request.args.get('videoId', '').strip()
    user_id  = request.args.get('userId',  '').strip()

    if not video_id:
        return jsonify({'error': 'videoId is required'}), 400

    track = (VideoTrack.query
             .filter_by(learner_id=user_id, video_id=video_id)
             .first()) if user_id else None

    skill = db.session.get(Skill, track.skill_id) if (track and track.skill_id) else None

    if not skill and track:
        skill = _match_skill(track.video_title or '', track.channel_name or '')

    if not skill:
        return jsonify({'skillName': None, 'skillId': None,
                        'progressPct': 0, 'minutesLeft': None})

    watched_min = (track.total_watched_seconds / 60) if track else 0
    total_min   = skill.avg_hours_to_learn * 60
    pct  = min(100.0, watched_min / total_min * 100) if total_min else 0
    left = max(0.0,   total_min   - watched_min)

    return jsonify({
        'skillName':   skill.skill_name,
        'skillId':     skill.skill_id,
        'progressPct': round(pct,  1),
        'minutesLeft': round(left, 0),
    })


# ── POST /track ────────────────────────────────────────────────────────────────

@extension_bp.route('/track', methods=['POST'])
def track_video():
    data     = request.get_json(silent=True) or {}
    video_id = data.get('videoId', '').strip()
    user_id  = data.get('userId',  '').strip()

    if not video_id or not user_id:
        return jsonify({'error': 'videoId and userId are required'}), 400

    if not db.session.get(Learner, user_id):
        return jsonify({'error': 'Learner not found'}), 404

    watched = max(0, int(data.get('watchedSeconds', 0)))

    track = VideoTrack.query.filter_by(learner_id=user_id, video_id=video_id).first()
    if not track:
        title   = data.get('videoTitle',  '')
        channel = data.get('channelName', '')
        skill   = _match_skill(title, channel)
        track   = VideoTrack(
            learner_id=user_id, video_id=video_id,
            video_title=title,  channel_name=channel,
            skill_id=skill.skill_id if skill else None,
            total_watched_seconds=watched,
        )
        db.session.add(track)
    else:
        track.total_watched_seconds += watched
        track.updated_at = datetime.utcnow()

    db.session.commit()

    skill = db.session.get(Skill, track.skill_id) if track.skill_id else None
    pct, left = 0, None
    if skill:
        total_min = skill.avg_hours_to_learn * 60
        watched_min = track.total_watched_seconds / 60
        pct  = min(100.0, watched_min / total_min * 100) if total_min else 0
        left = round(max(0.0, total_min - watched_min), 0)

    return jsonify({
        'ok': True,
        'skillName':   skill.skill_name if skill else None,
        'progressPct': round(pct, 1),
        'minutesLeft': left,
    })


# ── POST /complete ─────────────────────────────────────────────────────────────

@extension_bp.route('/complete', methods=['POST'])
def complete_video():
    data     = request.get_json(silent=True) or {}
    video_id = data.get('videoId', '').strip()
    user_id  = data.get('userId',  '').strip()

    if not video_id or not user_id:
        return jsonify({'error': 'videoId and userId are required'}), 400

    track = VideoTrack.query.filter_by(learner_id=user_id, video_id=video_id).first()
    if track:
        track.is_completed = True
        track.updated_at   = datetime.utcnow()
        db.session.commit()

    return jsonify({'ok': True, 'completed': True})
