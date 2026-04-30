import requests as http_req
from urllib.parse import urlencode
from flask import Blueprint, request, jsonify, redirect, current_app
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
        role            = 'learner',
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
    if not learner:
        return jsonify({'error': 'Invalid credentials'}), 401

    # OAuth-only accounts have no password
    if not learner.password_hash:
        provider = learner.oauth_provider or 'social'
        return jsonify({'error': f'This account uses {provider} login. Please sign in with {provider}.'}), 401

    if not bcrypt.check_password_hash(learner.password_hash, password):
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


# ─────────────────────────────────────────
# OAuth helpers
# ─────────────────────────────────────────

def _issue_jwt_redirect(learner):
    """Create JWT tokens and redirect to frontend callback page."""
    frontend_url  = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
    access_token  = create_access_token(identity=learner.learner_id)
    refresh_token = create_refresh_token(identity=learner.learner_id)
    params = urlencode({'access_token': access_token, 'refresh_token': refresh_token})
    return redirect(f'{frontend_url}/auth/callback?{params}')


def _oauth_error_redirect(msg='oauth_failed'):
    frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
    return redirect(f'{frontend_url}/login?error={msg}')


def _find_or_create_learner(provider, provider_id, email, name):
    """Find existing user by OAuth ID or email; otherwise create a new account."""
    learner = Learner.query.filter_by(oauth_provider=provider, oauth_id=provider_id).first()
    if not learner and email:
        learner = Learner.query.filter_by(email=email).first()
        if learner:
            learner.oauth_provider = provider
            learner.oauth_id       = provider_id
    if not learner:
        learner = Learner(
            email         = email or f'{provider}_{provider_id}@oauth.local',
            password_hash = '',
            full_name     = name or 'User',
            role          = 'learner',
            oauth_provider = provider,
            oauth_id       = provider_id,
        )
        db.session.add(learner)
    learner.last_active = datetime.utcnow()
    db.session.commit()
    return learner


# ─────────────────────────────────────────
# Google OAuth
# ─────────────────────────────────────────

@auth_bp.route('/oauth/status', methods=['GET'])
def oauth_status():
    """Return which OAuth providers are configured (no secrets exposed)."""
    return jsonify({
        'google': bool(current_app.config.get('GOOGLE_CLIENT_ID')),
        'github': bool(current_app.config.get('GITHUB_CLIENT_ID')),
    })


@auth_bp.route('/google')
def google_login():
    client_id = current_app.config.get('GOOGLE_CLIENT_ID', '')
    if not client_id:
        return _oauth_error_redirect('not_configured')

    backend_url  = current_app.config.get('BACKEND_URL', 'http://localhost:5000')
    redirect_uri = f'{backend_url}/api/v1/auth/google/callback'

    params = urlencode({
        'client_id':     client_id,
        'redirect_uri':  redirect_uri,
        'response_type': 'code',
        'scope':         'openid email profile',
        'access_type':   'offline',
        'prompt':        'select_account',
    })
    return redirect(f'https://accounts.google.com/o/oauth2/v2/auth?{params}')


@auth_bp.route('/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        return _oauth_error_redirect('oauth_cancelled')

    client_id     = current_app.config.get('GOOGLE_CLIENT_ID', '')
    client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET', '')
    backend_url   = current_app.config.get('BACKEND_URL', 'http://localhost:5000')
    redirect_uri  = f'{backend_url}/api/v1/auth/google/callback'

    # Exchange code → access token
    try:
        token_resp = http_req.post('https://oauth2.googleapis.com/token', data={
            'code':          code,
            'client_id':     client_id,
            'client_secret': client_secret,
            'redirect_uri':  redirect_uri,
            'grant_type':    'authorization_code',
        }, timeout=15)
        token_resp.raise_for_status()
        g_access_token = token_resp.json().get('access_token')
        if not g_access_token:
            return _oauth_error_redirect('token_exchange_failed')
    except Exception:
        return _oauth_error_redirect('token_exchange_failed')

    # Fetch user info
    try:
        info_resp = http_req.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {g_access_token}'},
            timeout=10,
        )
        info_resp.raise_for_status()
        info = info_resp.json()
    except Exception:
        return _oauth_error_redirect('userinfo_failed')

    try:
        learner = _find_or_create_learner(
            provider    = 'google',
            provider_id = info.get('id', ''),
            email       = info.get('email', '').lower(),
            name        = info.get('name', ''),
        )
    except Exception:
        db.session.rollback()
        return _oauth_error_redirect('db_error')

    return _issue_jwt_redirect(learner)


# ─────────────────────────────────────────
# GitHub OAuth
# ─────────────────────────────────────────

@auth_bp.route('/github')
def github_login():
    client_id = current_app.config.get('GITHUB_CLIENT_ID', '')
    if not client_id:
        return _oauth_error_redirect('not_configured')

    backend_url  = current_app.config.get('BACKEND_URL', 'http://localhost:5000')
    redirect_uri = f'{backend_url}/api/v1/auth/github/callback'

    params = urlencode({
        'client_id':    client_id,
        'redirect_uri': redirect_uri,
        'scope':        'read:user user:email',
    })
    return redirect(f'https://github.com/login/oauth/authorize?{params}')


@auth_bp.route('/github/callback')
def github_callback():
    code = request.args.get('code')
    if not code:
        return _oauth_error_redirect('oauth_cancelled')

    client_id     = current_app.config.get('GITHUB_CLIENT_ID', '')
    client_secret = current_app.config.get('GITHUB_CLIENT_SECRET', '')
    backend_url   = current_app.config.get('BACKEND_URL', 'http://localhost:5000')
    redirect_uri  = f'{backend_url}/api/v1/auth/github/callback'

    # Exchange code → access token
    try:
        token_resp = http_req.post(
            'https://github.com/login/oauth/access_token',
            data={
                'client_id':     client_id,
                'client_secret': client_secret,
                'code':          code,
                'redirect_uri':  redirect_uri,
            },
            headers={'Accept': 'application/json'},
            timeout=15,
        )
        token_resp.raise_for_status()
        gh_access_token = token_resp.json().get('access_token')
        if not gh_access_token:
            return _oauth_error_redirect('token_exchange_failed')
    except Exception:
        return _oauth_error_redirect('token_exchange_failed')

    headers = {
        'Authorization': f'Bearer {gh_access_token}',
        'Accept':        'application/vnd.github+json',
    }

    # Fetch user profile
    try:
        user_resp = http_req.get('https://api.github.com/user', headers=headers, timeout=10)
        user_resp.raise_for_status()
        gh_user = user_resp.json()
    except Exception:
        return _oauth_error_redirect('userinfo_failed')

    # Fetch primary email (may not be in profile)
    email = gh_user.get('email', '')
    if not email:
        try:
            emails_resp = http_req.get('https://api.github.com/user/emails', headers=headers, timeout=10)
            if emails_resp.ok:
                for e in emails_resp.json():
                    if e.get('primary') and e.get('verified'):
                        email = e['email']
                        break
        except Exception:
            pass

    try:
        learner = _find_or_create_learner(
            provider    = 'github',
            provider_id = str(gh_user.get('id', '')),
            email       = email.lower() if email else '',
            name        = gh_user.get('name') or gh_user.get('login', ''),
        )
    except Exception:
        db.session.rollback()
        return _oauth_error_redirect('db_error')

    return _issue_jwt_redirect(learner)
