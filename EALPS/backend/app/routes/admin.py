from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from sqlalchemy import distinct
from ..models import Learner, Skill, MarketSkillData, LearningPathway, SkillDifficultyScore
from ..services.market_simulator import simulate_market_data, run_decay_detection
from ..services.ollama_client import analyse_curriculum_gaps
from ..extensions import db
from ..ml.fnn_scorer import score_skill, get_model

admin_bp = Blueprint('admin', __name__)


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        learner = db.session.get(Learner, get_jwt_identity())
        if not learner or learner.role not in ('admin', 'instructor'):
            return jsonify({'error': 'Admin access required'}), 403
        if not learner.is_active:
            return jsonify({'error': 'Account is deactivated'}), 403
        return fn(*args, **kwargs)
    return wrapper


@admin_bp.route('/curriculum/health', methods=['GET'])
@admin_required
def curriculum_health():
    try:
        decayed = (
            db.session.query(Skill.skill_name, Skill.category, MarketSkillData.demand_index)
            .join(MarketSkillData, MarketSkillData.skill_id == Skill.skill_id)
            .filter(MarketSkillData.decay_flag == True)
            .distinct(Skill.skill_name)
            .limit(20)
            .all()
        )
        emerging = (
            db.session.query(Skill.skill_name, Skill.category, MarketSkillData.demand_index)
            .join(MarketSkillData, MarketSkillData.skill_id == Skill.skill_id)
            .filter(MarketSkillData.emerging_flag == True)
            .distinct(Skill.skill_name)
            .limit(20)
            .all()
        )

        total_skills   = Skill.query.filter_by(is_active=True).count()
        decayed_count  = len(decayed)
        emerging_count = len(emerging)

        return jsonify({
            'kpis': {
                'total_active_skills': total_skills,
                'skills_with_decay':   decayed_count,
                'emerging_skills':     emerging_count,
                'coverage_score':      round(100 - (decayed_count / max(total_skills, 1) * 100), 1),
            },
            'decayed_skills':  [{'name': d[0], 'category': d[1], 'demand': d[2]} for d in decayed],
            'emerging_skills': [{'name': e[0], 'category': e[1], 'demand': e[2]} for e in emerging],
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch curriculum health', 'detail': str(e)}), 500


@admin_bp.route('/curriculum/analysis', methods=['GET'])
@admin_required
def curriculum_analysis():
    try:
        decayed  = [r.skill.skill_name for r in MarketSkillData.query.filter_by(decay_flag=True).limit(5) if r.skill]
        emerging = [r.skill.skill_name for r in MarketSkillData.query.filter_by(emerging_flag=True).limit(5) if r.skill]
        narrative = analyse_curriculum_gaps(decayed, emerging)
        return jsonify({'analysis': narrative, 'decayed': decayed, 'emerging': emerging})
    except Exception as e:
        return jsonify({'error': 'Analysis failed', 'detail': str(e)}), 500


@admin_bp.route('/market/refresh', methods=['POST'])
@admin_required
def refresh_market():
    try:
        simulate_market_data(months=6)
        return jsonify({'message': 'Market data refreshed and decay detection completed.'})
    except Exception as e:
        return jsonify({'error': 'Market refresh failed', 'detail': str(e)}), 500


@admin_bp.route('/stats', methods=['GET'])
@admin_required
def system_stats():
    try:
        return jsonify({
            'total_learners':  Learner.query.filter_by(role='learner').count(),
            'total_skills':    Skill.query.filter_by(is_active=True).count(),
            'total_pathways':  LearningPathway.query.count(),
            'active_pathways': LearningPathway.query.filter_by(status='active').count(),
        })
    except Exception as e:
        return jsonify({'error': 'Stats unavailable', 'detail': str(e)}), 500


@admin_bp.route('/skills', methods=['POST'])
@admin_required
def add_skill():
    data = request.get_json(silent=True) or {}

    name = data.get('skill_name', '').strip()
    if not name:
        return jsonify({'error': 'skill_name is required'}), 400

    bloom = int(data.get('bloom_level', 3))
    if bloom < 1 or bloom > 6:
        return jsonify({'error': 'bloom_level must be between 1 and 6'}), 400

    hours = float(data.get('avg_hours_to_learn', 20))
    if hours <= 0:
        return jsonify({'error': 'avg_hours_to_learn must be positive'}), 400

    cload = float(data.get('cognitive_load_score', 0.5))
    if not (0.0 <= cload <= 1.0):
        return jsonify({'error': 'cognitive_load_score must be between 0 and 1'}), 400

    if Skill.query.filter_by(skill_name=name).first():
        return jsonify({'error': f'Skill "{name}" already exists'}), 409

    try:
        skill = Skill(
            skill_name           = name,
            category             = data.get('category', 'General'),
            bloom_level          = bloom,
            avg_hours_to_learn   = hours,
            cognitive_load_score = cload,
        )
        db.session.add(skill)
        db.session.flush()

        model   = get_model()
        prereq  = max(0, bloom - 1)
        abstr   = min(1.0, cload + 0.1)
        ds      = score_skill(bloom, prereq, abstr, hours, model)
        sds     = SkillDifficultyScore(
            skill_id           = skill.skill_id,
            difficulty_score   = ds,
            prerequisite_count = prereq,
            abstraction_level  = abstr,
        )
        db.session.add(sds)
        db.session.commit()
        return jsonify(skill.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to add skill', 'detail': str(e)}), 500


@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    try:
        page     = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        users    = Learner.query.order_by(Learner.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return jsonify({
            'users':   [u.to_dict() for u in users.items],
            'total':   users.total,
            'page':    page,
            'pages':   users.pages,
        })
    except Exception as e:
        return jsonify({'error': 'Failed to list users', 'detail': str(e)}), 500


@admin_bp.route('/users/<user_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_user(user_id):
    user = db.session.get(Learner, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    try:
        user.is_active = False
        db.session.commit()
        return jsonify({'message': f'User {user.email} deactivated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to deactivate user', 'detail': str(e)}), 500
