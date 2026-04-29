from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from ..models import Learner, LearningPathway
from ..services.schedule_engine import ScheduleOptimizer
from ..extensions import db

schedules_bp = Blueprint('schedules', __name__)


@schedules_bp.route('/<pathway_id>/generate', methods=['POST'])
@jwt_required()
def generate_schedule(pathway_id):
    """
    Generate a personalized weekly learning schedule for a pathway.

    Request JSON:
    {
        "start_date": "2026-04-30" (optional, default: today),
        "available_days": [0, 1, 2, 3, 4, 5] (optional, Mon=0, Sun=6),
        "max_hours_per_day": 4.0 (optional, default: 4)
    }
    """
    learner = db.session.get(Learner, get_jwt_identity())
    if not learner:
        return jsonify({'error': 'User not found'}), 404

    # Get the pathway
    pathway = LearningPathway.query.filter_by(
        pathway_id=pathway_id,
        learner_id=learner.learner_id
    ).first()

    if not pathway:
        return jsonify({'error': 'Pathway not found'}), 404

    # Parse request parameters
    data = request.get_json(silent=True) or {}

    # Parse start date
    start_date = None
    if 'start_date' in data:
        try:
            start_date = datetime.fromisoformat(data['start_date']).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid start_date format (use ISO format)'}), 400
    else:
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date -= timedelta(days=start_date.weekday())  # Align to Monday

    # Parse available days
    available_days = data.get('available_days')
    if available_days:
        try:
            available_days = [int(d) for d in available_days]
            if not all(0 <= d <= 6 for d in available_days):
                return jsonify({'error': 'Days must be 0-6 (Mon=0, Sun=6)'}), 400
        except (TypeError, ValueError):
            return jsonify({'error': 'available_days must be list of integers'}), 400
    else:
        available_days = list(range(6))  # Mon-Sat default

    # Parse max hours per day
    try:
        max_hours_per_day = float(data.get('max_hours_per_day', 4.0))
        if max_hours_per_day <= 0 or max_hours_per_day > 12:
            return jsonify({'error': 'max_hours_per_day must be between 0 and 12'}), 400
    except (TypeError, ValueError):
        return jsonify({'error': 'max_hours_per_day must be a number'}), 400

    try:
        # Generate schedule
        optimizer = ScheduleOptimizer(pathway, learner)
        schedule, explanation = optimizer.generate(
            start_date=start_date,
            available_days=available_days,
            max_hours_per_day=max_hours_per_day
        )

        result = schedule.to_dict()
        result['explanation'] = explanation
        return jsonify(result), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Schedule generation failed', 'detail': str(e)}), 500


@schedules_bp.route('/<pathway_id>/suggest-adjustment', methods=['POST'])
@jwt_required()
def suggest_schedule_adjustment(pathway_id):
    """
    Suggest schedule adjustments based on learner feedback.

    Request JSON:
    {
        "completed_skills": ["skill1", "skill2"],
        "struggling_with": ["skill3"],
        "available_hours_reduced": true/false,
        "preferred_daily_hours": 3.5
    }
    """
    learner = db.session.get(Learner, get_jwt_identity())
    if not learner:
        return jsonify({'error': 'User not found'}), 404

    pathway = LearningPathway.query.filter_by(
        pathway_id=pathway_id,
        learner_id=learner.learner_id
    ).first()

    if not pathway:
        return jsonify({'error': 'Pathway not found'}), 404

    data = request.get_json(silent=True) or {}

    # Adapt learner effort capacity if indicated
    if data.get('available_hours_reduced'):
        learner.effort_capacity = max(5.0, learner.effort_capacity * 0.8)
    if 'preferred_daily_hours' in data:
        try:
            daily = float(data['preferred_daily_hours'])
            learner.effort_capacity = daily * 6  # Assume 6-day week
        except (TypeError, ValueError):
            pass

    db.session.commit()

    try:
        optimizer = ScheduleOptimizer(pathway, learner)
        schedule, explanation = optimizer.generate()

        result = schedule.to_dict()
        result['explanation'] = explanation
        result['adjusted_capacity'] = learner.effort_capacity
        return jsonify(result), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Schedule adjustment failed', 'detail': str(e)}), 500
