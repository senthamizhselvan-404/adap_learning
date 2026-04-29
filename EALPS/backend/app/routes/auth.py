from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
)
from datetime import datetime
from ..models import Learner, TokenBlocklist
from ..extensions import db, bcrypt, limiter

auth_bp = Blueprint('auth', __name__)

_ALLOWED_REGISTER_ROLES = frozenset({'learner'})


@auth_bp.route('/register', methods=['POST'])
@limiter.limit('10 per minute')
def register():
    data = request.get_json(silent=True) or {}
    required = ['email', 'password', 'full_name']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields: email, password, full_name'}), 400

    email = data['email'].strip().lower()
    if not email or '@' not in email:
        return jsonify({'error': 'Invalid email address'}), 400

    password = data['password']
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    full_name = data['full_name'].strip()
    if not full_name:
        return jsonify({'error': 'full_name cannot be blank'}), 400

    if Learner.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    learner = Learner(
        email           = email,
        password_hash   = pw_hash,
        full_name       = full_name,
        role            = 'learner',          # role is never taken from input
        effort_capacity = float(data.get('effort_capacity', 10.0)),
        prior_skills    = data.get('prior_skills', []),
    )
    try:
        db.session.add(learner)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Registration failed. Please try again.'}), 500

    access_token  = create_access_token(identity=learner.learner_id)
    refresh_token = create_refresh_token(identity=learner.learner_id)
    return jsonify({
        'access_token':  access_token,
        'refresh_token': refresh_token,
        'learner':       learner.to_dict(),
    }), 201


@auth_bp.route('/login', methods=['POST'])
@limiter.limit('20 per minute')
def login():
    data    = request.get_json(silent=True) or {}
    email   = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    learner = Learner.query.filter_by(email=email).first()
    if not learner or not bcrypt.check_password_hash(learner.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    if not learner.is_active:
        return jsonify({'error': 'Account is deactivated. Contact support.'}), 403

    try:
        learner.last_active = datetime.utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()

    access_token  = create_access_token(identity=learner.learner_id)
    refresh_token = create_refresh_token(identity=learner.learner_id)
    return jsonify({
        'access_token':  access_token,
        'refresh_token': refresh_token,
        'learner':       learner.to_dict(),
    })


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity     = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({'access_token': access_token})


@auth_bp.route('/logout', methods=['DELETE'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    try:
        db.session.add(TokenBlocklist(jti=jti))
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Logout failed'}), 500
    return jsonify({'message': 'Successfully logged out'}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    learner = db.session.get(Learner, get_jwt_identity())
    if not learner:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(learner.to_dict())
