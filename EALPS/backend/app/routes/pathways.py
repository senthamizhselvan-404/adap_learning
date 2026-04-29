from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Learner, LearningPathway, PathwaySkill, ProgressRecord, Skill
from ..services.pathway_engine import generate_pathway, recalibrate_pathway
from ..services.ollama_client import generate_pathway_explanation
from ..extensions import db

pathways_bp = Blueprint('pathways', __name__)

_VALID_STATUSES = frozenset({'active', 'completed', 'paused', 'abandoned'})


@pathways_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate():
    learner = db.session.get(Learner, get_jwt_identity())
    if not learner:
        return jsonify({'error': 'User not found'}), 404

    data        = request.get_json(silent=True) or {}
    target_role = data.get('target_role', '').strip()
    if not target_role:
        return jsonify({'error': 'target_role is required'}), 400
    if len(target_role) > 200:
        return jsonify({'error': 'target_role is too long (max 200 chars)'}), 400

    try:
        pathway = generate_pathway(learner, target_role)
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Pathway generation failed', 'detail': str(e)}), 500

    skills_data = [
        ps.to_dict() for ps in
        pathway.pathway_skills.order_by(PathwaySkill.sequence_order).limit(5)
    ]
    explanation = generate_pathway_explanation(target_role, skills_data)

    result = pathway.to_dict()
    result['explanation'] = explanation
    return jsonify(result), 201


@pathways_bp.route('/', methods=['GET'])
@jwt_required()
def list_pathways():
    learner_id = get_jwt_identity()
    pathways   = LearningPathway.query.filter_by(learner_id=learner_id).all()
    return jsonify([p.to_dict() for p in pathways])


@pathways_bp.route('/<pathway_id>', methods=['GET'])
@jwt_required()
def get_pathway(pathway_id):
    learner_id = get_jwt_identity()
    pathway    = LearningPathway.query.filter_by(
        pathway_id=pathway_id, learner_id=learner_id
    ).first_or_404()
    return jsonify(pathway.to_dict())


@pathways_bp.route('/<pathway_id>/status', methods=['PATCH'])
@jwt_required()
def update_status(pathway_id):
    learner_id = get_jwt_identity()
    pathway    = LearningPathway.query.filter_by(
        pathway_id=pathway_id, learner_id=learner_id
    ).first_or_404()

    data   = request.get_json(silent=True) or {}
    status = data.get('status', '').strip()
    if status not in _VALID_STATUSES:
        return jsonify({'error': f'status must be one of: {sorted(_VALID_STATUSES)}'}), 400

    try:
        pathway.status = status
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Status update failed'}), 500

    return jsonify(pathway.to_dict())


@pathways_bp.route('/<pathway_id>/progress', methods=['PUT'])
@jwt_required()
def update_progress(pathway_id):
    learner_id = get_jwt_identity()
    pathway    = LearningPathway.query.filter_by(
        pathway_id=pathway_id, learner_id=learner_id
    ).first_or_404()

    data     = request.get_json(silent=True) or {}
    skill_id = data.get('skill_id')
    if not skill_id:
        return jsonify({'error': 'skill_id is required'}), 400

    try:
        hours = float(data.get('hours_logged', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'hours_logged must be a number'}), 400

    if hours < 0:
        return jsonify({'error': 'hours_logged cannot be negative'}), 400

    skill = db.session.get(Skill, skill_id)
    if not skill:
        return jsonify({'error': 'Skill not found'}), 404

    try:
        record = ProgressRecord.query.filter_by(
            learner_id=learner_id, skill_id=skill_id
        ).first()
        if record:
            record.hours_logged += hours
        else:
            record = ProgressRecord(
                learner_id=learner_id, skill_id=skill_id, hours_logged=hours
            )
            db.session.add(record)

        db.session.flush()

        ps = PathwaySkill.query.filter_by(
            pathway_id=pathway_id, skill_id=skill_id
        ).first()
        if ps and skill:
            if record.hours_logged >= skill.avg_hours_to_learn * 0.9:
                ps.status           = 'completed'
                record.is_completed = True
                # Unlock next skill by sequence order
                next_ps = (
                    PathwaySkill.query
                    .filter(
                        PathwaySkill.pathway_id == pathway_id,
                        PathwaySkill.sequence_order > ps.sequence_order,
                        PathwaySkill.status == 'locked',
                    )
                    .order_by(PathwaySkill.sequence_order)
                    .first()
                )
                if next_ps:
                    next_ps.status = 'in_progress'
            else:
                ps.status = 'in_progress'

        recalibrate_pathway(pathway)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Progress update failed', 'detail': str(e)}), 500

    return jsonify(pathway.to_dict())


@pathways_bp.route('/<pathway_id>/recalibrate', methods=['POST'])
@jwt_required()
def recalibrate(pathway_id):
    learner_id = get_jwt_identity()
    pathway    = LearningPathway.query.filter_by(
        pathway_id=pathway_id, learner_id=learner_id
    ).first_or_404()
    try:
        recalibrate_pathway(pathway)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Recalibration failed', 'detail': str(e)}), 500
    return jsonify(pathway.to_dict())
