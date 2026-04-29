import os
import secrets
from datetime import timedelta


def _require_env(key: str, default: str) -> str:
    """Return env var or a stable default for dev; warn in production."""
    return os.environ.get(key, default)


class Config:
    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY     = _require_env('SECRET_KEY',     secrets.token_hex(32))
    JWT_SECRET_KEY = _require_env('JWT_SECRET_KEY', secrets.token_hex(32))

    # ── Database ──────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI        = os.environ.get('DATABASE_URL', 'sqlite:///ealps.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS      = {
        'pool_pre_ping': True,
        'pool_recycle':  300,
    }

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_TOKEN_LOCATION        = ['headers']
    JWT_HEADER_NAME           = 'Authorization'
    JWT_HEADER_TYPE           = 'Bearer'

    # ── Ollama ────────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL    = os.environ.get('OLLAMA_MODEL',    'gemma3:4b')

    # ── ML model ──────────────────────────────────────────────────────────────
    ML_MODEL_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'ml_models', 'fnn_scorer.pkl'
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000'
    ).split(',')

    # ── OAuth ─────────────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID',     '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    GITHUB_CLIENT_ID     = os.environ.get('GITHUB_CLIENT_ID',     '')
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET', '')
    BACKEND_URL          = os.environ.get('BACKEND_URL',  'http://localhost:5000')
    FRONTEND_URL         = os.environ.get('FRONTEND_URL', 'http://localhost:5173')

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATELIMIT_DEFAULT          = '200 per minute'
    RATELIMIT_STORAGE_URL      = 'memory://'
    RATELIMIT_HEADERS_ENABLED  = True

    # ── Request limits ────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB max request body
