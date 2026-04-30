from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from ..models import (
    PracticeProblem, ProblemTestCase, ProblemSolution,
    PracticeSession, Skill, Learner, PathwaySkill, LearningPathway
)
from ..services.code_executor import CodeExecutor
from ..extensions import db
import json

practice_bp = Blueprint('practice', __name__)


# ─────────────────────────────────────────
# Standalone Code Execution (No Problem ID)
# ─────────────────────────────────────────
@practice_bp.route('/execute', methods=['POST'])
@jwt_required()
def execute_standalone():
    """
    Execute arbitrary code without a problem context.
    Used by the standalone IDE dashboard.
    """
    data = request.get_json()
    code = data.get('code', '').strip()
    language = data.get('language', 'python').lower()

    if not code:
        return jsonify({'error': 'Code is required'}), 400

    if language not in ['python', 'javascript', 'html', 'css']:
        return jsonify({'error': f'Language {language} not supported'}), 400

    result = CodeExecutor.execute(code, language, [], timeout=5)
    return jsonify(result), 200


# ─────────────────────────────────────────
# List Practice Problems
# ─────────────────────────────────────────
@practice_bp.route('/problems/', methods=['GET'])
@jwt_required()
def list_problems():
    """
    List all practice problems with optional filters.
    Query params: skill_id, difficulty, language, page, per_page
    """
    skill_id = request.args.get('skill_id', '').strip()
    difficulty = request.args.get('difficulty', '', type=int)
    language = request.args.get('language', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    q = PracticeProblem.query

    if skill_id:
        q = q.filter_by(skill_id=skill_id)
    if difficulty:
        q = q.filter_by(difficulty=difficulty)
    if language:
        q = q.filter(
            PracticeProblem.languages_supported.contains([language])
        )

    pagination = q.order_by(PracticeProblem.difficulty, PracticeProblem.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'problems': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
    })


# ─────────────────────────────────────────
# Get Problem Details
# ─────────────────────────────────────────
@practice_bp.route('/problems/<problem_id>', methods=['GET'])
@jwt_required()
def get_problem(problem_id):
    """
    Get a single problem with all its test cases (non-hidden ones).
    """
    problem = db.session.get(PracticeProblem, problem_id)
    if not problem:
        return jsonify({'error': 'Problem not found'}), 404

    return jsonify(problem.to_dict(include_test_cases=True))


# ─────────────────────────────────────────
# Execute Code (No Save)
# ─────────────────────────────────────────
@practice_bp.route('/problems/<problem_id>/execute', methods=['POST'])
@jwt_required()
def execute_code(problem_id):
    """
    Execute code without saving it. Returns execution results.
    """
    problem = db.session.get(PracticeProblem, problem_id)
    if not problem:
        return jsonify({'error': 'Problem not found'}), 404

    data = request.get_json()
    code = data.get('code', '').strip()
    language = data.get('language', 'python').lower()

    if not code:
        return jsonify({'error': 'Code is required'}), 400

    if language not in problem.languages_supported:
        return jsonify({'error': f'Language {language} not supported for this problem'}), 400

    # Get test cases (including hidden ones for execution)
    test_cases = [
        {
            'input_data': tc.input_data,
            'expected_output': tc.expected_output,
        }
        for tc in problem.test_cases.all()
    ]

    # Execute code
    result = CodeExecutor.execute(code, language, test_cases, problem.time_limit)

    return jsonify(result), 200


# ─────────────────────────────────────────
# Submit Solution (Save + Validate)
# ─────────────────────────────────────────
@practice_bp.route('/problems/<problem_id>/submit', methods=['POST'])
@jwt_required()
def submit_solution(problem_id):
    """
    Submit a solution for a problem. Saves it and validates against all test cases.
    """
    learner_id = get_jwt_identity()
    problem = db.session.get(PracticeProblem, problem_id)
    if not problem:
        return jsonify({'error': 'Problem not found'}), 404

    data = request.get_json()
    code = data.get('code', '').strip()
    language = data.get('language', 'python').lower()

    if not code:
        return jsonify({'error': 'Code is required'}), 400

    if language not in problem.languages_supported:
        return jsonify({'error': f'Language {language} not supported for this problem'}), 400

    # Get all test cases
    test_cases = [
        {
            'input_data': tc.input_data,
            'expected_output': tc.expected_output,
        }
        for tc in problem.test_cases.all()
    ]

    # Execute code
    result = CodeExecutor.execute(code, language, test_cases, problem.time_limit)

    # Calculate score (percentage of tests passed)
    passed_tests = sum(1 for tr in result['test_results'] if tr.get('passed', False))
    total_tests = len(result['test_results'])
    score = (passed_tests / total_tests * 100) if total_tests > 0 else 0

    # Create solution record
    solution = ProblemSolution(
        problem_id=problem_id,
        learner_id=learner_id,
        code=code,
        language=language,
        status=result['status'],
        test_results={
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'details': result['test_results'],
        },
        execution_time=result.get('execution_time', 0),
        score=score,
        last_executed_at=datetime.utcnow(),
    )

    db.session.add(solution)
    db.session.commit()

    # If passed, try to unlock next skill in pathway
    if result['status'] == 'passed':
        _try_unlock_next_skill(learner_id, problem.skill_id)

    return jsonify({
        'solution_id': solution.solution_id,
        'status': result['status'],
        'score': score,
        'message': 'All tests passed! 🎉' if result['status'] == 'passed' else f'{passed_tests}/{total_tests} tests passed',
        'test_results': result['test_results'],
    }), 201


# ─────────────────────────────────────────
# List Practice Sessions
# ─────────────────────────────────────────
@practice_bp.route('/sessions/', methods=['GET'])
@jwt_required()
def list_sessions():
    """
    List all practice sessions for the current learner.
    """
    learner_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    pagination = PracticeSession.query.filter_by(learner_id=learner_id).order_by(
        PracticeSession.started_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'sessions': [s.to_dict() for s in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
    })


# ─────────────────────────────────────────
# Get Practice Session Details
# ─────────────────────────────────────────
@practice_bp.route('/sessions/<session_id>', methods=['GET'])
@jwt_required()
def get_session(session_id):
    """
    Get details of a specific practice session with all solutions.
    """
    learner_id = get_jwt_identity()
    session = db.session.get(PracticeSession, session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    if session.learner_id != learner_id:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify(session.to_dict())


# ─────────────────────────────────────────
# Helper: Try to unlock next skill
# ─────────────────────────────────────────
def _try_unlock_next_skill(learner_id: str, skill_id: str) -> None:
    """
    When a learner solves a problem linked to a skill,
    try to unlock the next skill in their active pathway.
    """
    if not skill_id:
        return

    # Find active pathway
    pathway = LearningPathway.query.filter_by(
        learner_id=learner_id,
        status='active'
    ).first()

    if not pathway:
        return

    # Find pathway skill
    pathway_skill = PathwaySkill.query.filter_by(
        pathway_id=pathway.pathway_id,
        skill_id=skill_id
    ).first()

    if not pathway_skill:
        return

    # Mark current skill as completed if not already
    if pathway_skill.status != 'completed':
        pathway_skill.status = 'completed'

    # Find next locked skill
    next_skill = PathwaySkill.query.filter(
        PathwaySkill.pathway_id == pathway.pathway_id,
        PathwaySkill.sequence_order > pathway_skill.sequence_order,
        PathwaySkill.status == 'locked'
    ).order_by(PathwaySkill.sequence_order).first()

    if next_skill:
        next_skill.status = 'in_progress'

    db.session.commit()
