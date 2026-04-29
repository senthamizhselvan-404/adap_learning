from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Curriculum, Skill, SkillDifficultyScore
from ..services.ollama_client import extract_skills_from_text
from ..ml.fnn_scorer import score_skill, get_model
from ..extensions import db

curriculum_bp = Blueprint('curriculum', __name__)

_MAX_RAW_TEXT = 8000  # characters


@curriculum_bp.route('/', methods=['GET'])
@jwt_required()
def list_curricula():
    page     = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    pagination = (
        Curriculum.query
        .order_by(Curriculum.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify({
        'curricula': [c.to_dict() for c in pagination.items],
        'total':     pagination.total,
        'page':      page,
        'pages':     pagination.pages,
    })


@curriculum_bp.route('/', methods=['POST'])
@jwt_required()
def create_curriculum():
    learner_id = get_jwt_identity()
    data       = request.get_json(silent=True) or {}

    title = data.get('title', '').strip() or 'Untitled Curriculum'
    if len(title) > 300:
        return jsonify({'error': 'title is too long (max 300 chars)'}), 400

    raw_text = data.get('raw_text', '')
    if not isinstance(raw_text, str):
        return jsonify({'error': 'raw_text must be a string'}), 400
    raw_text = raw_text[:_MAX_RAW_TEXT]

    curriculum = Curriculum(
        title       = title,
        institution = data.get('institution', ''),
        created_by  = learner_id,
        raw_text    = raw_text,
    )

    try:
        db.session.add(curriculum)
        db.session.flush()

        extracted_skills = []
        if raw_text:
            extracted = extract_skills_from_text(raw_text)
            model     = get_model()

            for item in extracted:
                name = item.get('skill_name', '').strip()
                if not name or len(name) > 300:
                    continue

                bloom = int(item.get('bloom_level', 3))
                bloom = max(1, min(6, bloom))
                hours = float(item.get('estimated_hours', 20))
                hours = max(0.5, min(500, hours))

                skill = Skill.query.filter(
                    Skill.skill_name.ilike(name)
                ).first()
                if not skill:
                    skill = Skill(
                        skill_name         = name,
                        category           = item.get('category', 'General')[:100],
                        bloom_level        = bloom,
                        avg_hours_to_learn = hours,
                    )
                    db.session.add(skill)
                    db.session.flush()

                    ds  = score_skill(skill.bloom_level, 1, 0.5, skill.avg_hours_to_learn, model)
                    sds = SkillDifficultyScore(
                        skill_id           = skill.skill_id,
                        difficulty_score   = ds,
                        prerequisite_count = 1,
                        abstraction_level  = 0.5,
                    )
                    db.session.add(sds)

                extracted_skills.append(skill.to_dict())

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Curriculum creation failed', 'detail': str(e)}), 500

    return jsonify({
        'curriculum':       curriculum.to_dict(),
        'extracted_skills': extracted_skills,
    }), 201
