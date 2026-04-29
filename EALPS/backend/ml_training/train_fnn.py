"""
EALPS — FNN Difficulty Scorer Training Script
=============================================
Run: python train_fnn.py
Output: ml_models/fnn_scorer.pkl

Training Data:
  Synthetic samples generated from known skill difficulty distributions.
  Features: bloom_level, prerequisite_count, abstraction_level, avg_hours_to_learn
  Target  : difficulty_score ∈ [0.0, 1.0]
"""
import sys
import os
import numpy as np
import pickle
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# Ensure we can import from parent
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

MODEL_SAVE_PATH = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'fnn_scorer.pkl')


# ────────────────────────────────────────────────────────
# Synthetic Training Data Generator
# ────────────────────────────────────────────────────────
SKILL_PROFILES = [
    # (skill_name, bloom, prereqs, abstraction, hours, true_difficulty)
    # Easy skills
    ("HTML Basics",          1, 0, 0.1, 8,   0.08),
    ("CSS Styling",          2, 1, 0.2, 12,  0.14),
    ("Git Basics",           1, 0, 0.1, 6,   0.07),
    ("Linux CLI Basics",     2, 0, 0.2, 10,  0.12),
    ("JSON/YAML",            1, 0, 0.1, 4,   0.05),
    ("Markdown",             1, 0, 0.05,3,   0.04),
    # Medium skills
    ("JavaScript",           3, 2, 0.4, 40,  0.38),
    ("Python",               3, 1, 0.4, 35,  0.33),
    ("React",                3, 3, 0.5, 60,  0.50),
    ("SQL",                  3, 1, 0.4, 30,  0.32),
    ("REST APIs",            3, 2, 0.5, 25,  0.40),
    ("Docker",               3, 2, 0.5, 20,  0.42),
    ("PostgreSQL",           3, 2, 0.5, 30,  0.44),
    ("Node.js",              3, 3, 0.5, 45,  0.48),
    ("Authentication/JWT",   3, 3, 0.6, 15,  0.52),
    ("TypeScript",           3, 3, 0.5, 30,  0.46),
    # Hard skills
    ("Machine Learning",     5, 5, 0.8, 120, 0.76),
    ("Deep Learning",        5, 6, 0.9, 150, 0.84),
    ("System Design",        6, 7, 0.8, 80,  0.80),
    ("Kubernetes",           4, 5, 0.7, 60,  0.68),
    ("TensorFlow",           4, 6, 0.8, 90,  0.74),
    ("Quantum Computing",    6, 8, 1.0, 200, 0.95),
    ("Compiler Design",      6, 7, 0.9, 160, 0.90),
    ("Distributed Systems",  6, 7, 0.9, 100, 0.88),
    ("MLOps",                5, 6, 0.8, 70,  0.73),
    ("Prompt Engineering",   4, 3, 0.6, 20,  0.55),
    ("Vector Databases",     4, 5, 0.7, 40,  0.62),
    ("LLMs (Fine-tuning)",   5, 7, 0.9, 80,  0.82),
    ("Terraform",            4, 4, 0.6, 35,  0.58),
    ("Feature Engineering",  4, 4, 0.7, 50,  0.65),
    ("Statistics",           4, 3, 0.7, 60,  0.62),
    ("Linear Algebra",       5, 3, 0.8, 80,  0.70),
    ("Qiskit",               5, 7, 0.9, 100, 0.88),
    ("Cloud Computing",      3, 3, 0.5, 40,  0.50),
    ("Data Visualization",   3, 2, 0.4, 25,  0.36),
]


def generate_training_data(n_samples: int = 3000):
    """
    Augment base profiles with noise to create a training distribution.
    """
    np.random.seed(42)
    X, y = [], []

    for bloom, prereqs, abstr, hours, true_score in [p[1:] for p in SKILL_PROFILES]:
        for _ in range(n_samples // len(SKILL_PROFILES)):
            b  = int(np.clip(bloom  + np.random.randint(-1, 2), 1, 6))
            p  = int(np.clip(prereqs + np.random.randint(-1, 2), 0, 10))
            a  = float(np.clip(abstr  + np.random.normal(0, 0.05), 0.0, 1.0))
            h  = float(np.clip(hours  + np.random.normal(0, hours * 0.1), 1.0, 200.0))
            # Difficulty with small noise
            ds = float(np.clip(true_score + np.random.normal(0, 0.03), 0.0, 1.0))
            X.append([b, p, a, h])
            y.append(ds)

    # Add pure random samples for generalization
    for _ in range(500):
        b  = int(np.random.randint(1, 7))
        p  = int(np.random.randint(0, 11))
        a  = float(np.random.uniform(0, 1))
        h  = float(np.random.uniform(1, 200))
        # Heuristic ground truth
        ds = 0.35 * (b-1)/5 + 0.25 * p/10 + 0.25 * a + 0.15 * h/200
        ds = float(np.clip(ds + np.random.normal(0, 0.02), 0, 1))
        X.append([b, p, a, h])
        y.append(ds)

    return np.array(X), np.array(y)


def train():
    print("=" * 60)
    print("  EALPS - FNN Skill Difficulty Scorer Training")
    print("=" * 60)

    print("\n[1/4] Generating synthetic training data...")
    X, y = generate_training_data(n_samples=3000)
    print(f"      Samples: {len(X)} | Features: {X.shape[1]}")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("\n[2/4] Building FNN pipeline (MinMaxScaler + MLPRegressor)...")
    pipeline = Pipeline([
        ('scaler', MinMaxScaler()),
        ('fnn', MLPRegressor(
            hidden_layer_sizes=(64, 32, 16),
            activation='relu',
            solver='adam',
            max_iter=1500,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=20,
            verbose=False,
        ))
    ])

    print("\n[3/4] Training...")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    mae    = mean_absolute_error(y_test, y_pred)
    r2     = r2_score(y_test, y_pred)

    print(f"\n[4/4] Evaluation on test set:")
    print(f"      MAE : {mae:.4f}  (target < 0.05)")
    print(f"      R²  : {r2:.4f}  (target > 0.90)")

    # Sample predictions
    print("\n  Sample predictions vs ground truth:")
    print(f"  {'Skill':<28} {'Predicted':>10} {'True':>10}")
    print("  " + "-" * 50)
    for name, bloom, prereqs, abstr, hours, true in SKILL_PROFILES[::6]:
        pred = pipeline.predict([[bloom, prereqs, abstr, hours]])[0]
        print(f"  {name:<28} {pred:>10.3f} {true:>10.3f}")

    # Save
    save_path = os.path.abspath(MODEL_SAVE_PATH)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'wb') as f:
        pickle.dump(pipeline, f)
    print(f"\n[OK] Model saved -> {save_path}")
    print("  Training complete. You can now start the backend.\n")


if __name__ == '__main__':
    train()
