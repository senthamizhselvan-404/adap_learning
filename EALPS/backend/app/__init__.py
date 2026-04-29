import logging
from flask import Flask, jsonify
from flask_cors import CORS
from .config import Config
from .extensions import db, jwt, bcrypt, limiter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger('ealps')


def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)

    # Extensions
    CORS(app,
         resources={r'/api/*': {'origins': config.CORS_ORIGINS}},
         supports_credentials=True)
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)

    # ── JWT token blocklist ────────────────────────────────────────────────
    from .models import TokenBlocklist

    @jwt.token_in_blocklist_loader
    def check_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return db.session.query(
            TokenBlocklist.query.filter_by(jti=jti).exists()
        ).scalar()

    @jwt.revoked_token_loader
    def revoked_token_response(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has been revoked. Please log in again.'}), 401

    @jwt.expired_token_loader
    def expired_token_response(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired. Please refresh.'}), 401

    @jwt.invalid_token_loader
    def invalid_token_response(msg):
        return jsonify({'error': f'Invalid token: {msg}'}), 422

    @jwt.unauthorized_loader
    def missing_token_response(msg):
        return jsonify({'error': 'Authorization token required.'}), 401

    # ── Global error handlers ──────────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Bad request', 'detail': str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'error': 'Method not allowed'}), 405

    @app.errorhandler(413)
    def request_too_large(e):
        return jsonify({'error': 'Request body too large (max 1 MB)'}), 413

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({'error': 'Too many requests. Please slow down.'}), 429

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        logger.exception('Internal server error')
        return jsonify({'error': 'Internal server error'}), 500

    # ── Blueprints ─────────────────────────────────────────────────────────
    from .routes.auth       import auth_bp
    from .routes.learners   import learners_bp
    from .routes.pathways   import pathways_bp
    from .routes.skills     import skills_bp
    from .routes.admin      import admin_bp
    from .routes.curriculum import curriculum_bp

    app.register_blueprint(auth_bp,       url_prefix='/api/v1/auth')
    app.register_blueprint(learners_bp,   url_prefix='/api/v1/learners')
    app.register_blueprint(pathways_bp,   url_prefix='/api/v1/pathways')
    app.register_blueprint(skills_bp,     url_prefix='/api/v1/skills')
    app.register_blueprint(admin_bp,      url_prefix='/api/v1/admin')
    app.register_blueprint(curriculum_bp, url_prefix='/api/v1/curriculum')

    # ── Health check ───────────────────────────────────────────────────────
    @app.route('/health')
    def health():
        try:
            db.session.execute(db.text('SELECT 1'))
            db_status = 'ok'
        except Exception:
            db_status = 'error'
        return jsonify({'status': 'ok', 'db': db_status}), 200

    with app.app_context():
        db.create_all()
        logger.info('EALPS backend started')

    return app
