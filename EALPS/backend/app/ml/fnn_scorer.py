"""
FNN Skill Difficulty Scorer
============================
Architecture : MLPRegressor — 3 hidden layers [64, 32, 16] with ReLU
Inputs       : bloom_level, prerequisite_count, abstraction_level, avg_hours_to_learn
Output       : difficulty_score ∈ [0.0, 1.0]

numpy/scikit-learn are imported lazily so the app boots even when they are
not yet installed; the pure-Python heuristic fallback is used in that case.
"""
import os
import pickle


MODEL_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'ml_models', 'fnn_scorer.pkl'
)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def score_skill(bloom_level: int,
                prerequisite_count: int,
                abstraction_level: float,
                avg_hours_to_learn: float,
                model=None) -> float:
    """
    Return a difficulty score [0,1] for a single skill.
    Falls back to a deterministic weighted heuristic when model is None
    or when numpy/scikit-learn are not available.
    """
    if model is not None:
        try:
            import numpy as np
            X = np.array([[bloom_level, prerequisite_count, abstraction_level, avg_hours_to_learn]])
            score = float(np.clip(model.predict(X)[0], 0.0, 1.0))
            return round(score, 4)
        except Exception:
            pass  # fall through to heuristic

    bloom_norm  = (bloom_level - 1) / 5.0
    prereq_norm = _clamp(prerequisite_count / 10.0)
    hours_norm  = _clamp(avg_hours_to_learn / 200.0)
    score = (
        0.35 * bloom_norm
        + 0.25 * prereq_norm
        + 0.25 * _clamp(abstraction_level)
        + 0.15 * hours_norm
    )
    return round(_clamp(score), 4)


def load_model():
    """Load trained model from disk. Returns None if not found or sklearn unavailable."""
    path = os.path.abspath(MODEL_PATH)
    if not os.path.exists(path):
        return None
    try:
        import sklearn  # noqa: F401 — confirm sklearn present before unpickling
        with open(path, 'rb') as f:
            return pickle.load(f)
    except Exception:
        return None


def save_model(model, path=None):
    path = path or os.path.abspath(MODEL_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        pickle.dump(model, f)
    print(f"[FNN] Model saved → {path}")


def _build_pipeline():
    from sklearn.neural_network import MLPRegressor
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.pipeline import Pipeline
    return Pipeline([
        ('scaler', MinMaxScaler()),
        ('fnn', MLPRegressor(
            hidden_layer_sizes=(64, 32, 16),
            activation='relu',
            solver='adam',
            max_iter=1000,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.15,
        ))
    ])


_model_cache = None


def get_model():
    global _model_cache
    if _model_cache is None:
        _model_cache = load_model()
    return _model_cache
