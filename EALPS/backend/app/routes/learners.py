from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Learner, ProgressRecord, Skill
from ..extensions import db

learners_bp = Blueprint('learners', __name__)


@learners_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    learner = db.session.get(Learner, get_jwt_identity())
    if not learner:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(learner.to_dict())


@learners_bp.route('/me/skills', methods=['PUT'])
@jwt_required()
def update_skills():
    learner = db.session.get(Learner, get_jwt_identity())
    if not learner:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}

    prior = data.get('prior_skills')
    if prior is not None:
        if not isinstance(prior, list):
            return jsonify({'error': 'prior_skills must be a list'}), 400
        learner.prior_skills = [str(s).strip() for s in prior if str(s).strip()]

    effort = data.get('effort_capacity')
    if effort is not None:
        effort = float(effort)
        if effort <= 0 or effort > 168:
            return jsonify({'error': 'effort_capacity must be between 0 and 168 hours/week'}), 400
        learner.effort_capacity = effort

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Update failed'}), 500

    return jsonify(learner.to_dict())


@learners_bp.route('/me/progress', methods=['GET'])
@jwt_required()
def get_progress():
    learner_id = get_jwt_identity()
    page     = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)

    pagination = (
        ProgressRecord.query
        .filter_by(learner_id=learner_id)
        .order_by(ProgressRecord.logged_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify({
        'records':  [r.to_dict() for r in pagination.items],
        'total':    pagination.total,
        'page':     page,
        'pages':    pagination.pages,
    })


@learners_bp.route('/me/progress', methods=['POST'])
@jwt_required()
def log_progress():
    learner_id = get_jwt_identity()
    data       = request.get_json(silent=True) or {}
    skill_id   = data.get('skill_id')
    hours      = data.get('hours_logged', 0)

    if not skill_id:
        return jsonify({'error': 'skill_id is required'}), 400

    try:
        hours = float(hours)
    except (TypeError, ValueError):
        return jsonify({'error': 'hours_logged must be a number'}), 400

    if hours < 0:
        return jsonify({'error': 'hours_logged cannot be negative'}), 400
    if hours > 24:
        return jsonify({'error': 'hours_logged cannot exceed 24 hours per entry'}), 400

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
                learner_id=learner_id,
                skill_id=skill_id,
                hours_logged=hours,
            )
            db.session.add(record)

        if record.hours_logged >= skill.avg_hours_to_learn * 0.9:
            record.is_completed = True

        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to log progress'}), 500

    return jsonify(record.to_dict())
