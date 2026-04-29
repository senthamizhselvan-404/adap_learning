from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import distinct
from ..models import Skill, MarketSkillData
from ..extensions import db

skills_bp = Blueprint('skills', __name__)


@skills_bp.route('/', methods=['GET'])
@jwt_required()
def list_skills():
    category = request.args.get('category', '').strip()
    page     = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)

    q = Skill.query.filter_by(is_active=True)
    if category:
        q = q.filter(Skill.category.ilike(f'%{category}%'))

    pagination = q.order_by(Skill.skill_name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'skills':   [s.to_dict(include_market=True) for s in pagination.items],
        'total':    pagination.total,
        'page':     page,
        'pages':    pagination.pages,
    })


@skills_bp.route('/<skill_id>', methods=['GET'])
@jwt_required()
def get_skill(skill_id):
    skill = db.get_or_404(Skill, skill_id)
    return jsonify(skill.to_dict(include_market=True))


@skills_bp.route('/<skill_id>/market', methods=['GET'])
@jwt_required()
def skill_market(skill_id):
    skill = db.session.get(Skill, skill_id)
    if not skill:
        return jsonify({'error': 'Skill not found'}), 404

    limit   = min(request.args.get('limit', 24, type=int), 120)
    records = (
        MarketSkillData.query
        .filter_by(skill_id=skill_id)
        .order_by(MarketSkillData.captured_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify([r.to_dict() for r in reversed(records)])


@skills_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    cats = (
        db.session.query(distinct(Skill.category))
        .filter(Skill.is_active == True)
        .order_by(Skill.category)
        .all()
    )
    return jsonify([c[0] for c in cats])
