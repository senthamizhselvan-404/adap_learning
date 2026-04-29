"""
EALPS Seed Data
===============
Run: python seed_data.py
Populates: 44 skills, admin user, demo learner, simulated market data.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db, bcrypt
from app.models import Learner, Skill, SkillDifficultyScore
from app.ml.fnn_scorer import score_skill, get_model
from app.services.market_simulator import simulate_market_data

SKILLS = [
    # (name, category, bloom, hours, cognitive_load)
    ("HTML",               "Web Development", 1, 8,   0.10),
    ("CSS",                "Web Development", 2, 12,  0.18),
    ("JavaScript",         "Programming",     3, 50,  0.45),
    ("TypeScript",         "Programming",     3, 30,  0.48),
    ("React",              "Frontend",        3, 60,  0.52),
    ("Node.js",            "Backend",         3, 45,  0.50),
    ("REST APIs",          "Backend",         3, 25,  0.40),
    ("SQL",                "Databases",       3, 30,  0.38),
    ("PostgreSQL",         "Databases",       3, 35,  0.44),
    ("Git",                "DevOps",          1, 8,   0.12),
    ("Docker",             "DevOps",          3, 20,  0.45),
    ("Kubernetes",         "DevOps",          4, 60,  0.68),
    ("CI/CD",              "DevOps",          3, 20,  0.42),
    ("Linux",              "Systems",         2, 15,  0.25),
    ("Shell Scripting",    "Systems",         3, 15,  0.38),
    ("Python",             "Programming",     3, 35,  0.35),
    ("Machine Learning",   "AI/ML",           5, 120, 0.80),
    ("Deep Learning",      "AI/ML",           5, 150, 0.85),
    ("TensorFlow",         "AI/ML",           4, 80,  0.75),
    ("PyTorch",            "AI/ML",           4, 80,  0.75),
    ("Pandas",             "Data Science",    3, 25,  0.38),
    ("NumPy",              "Data Science",    3, 20,  0.35),
    ("Data Visualization", "Data Science",    3, 20,  0.35),
    ("Statistics",         "Data Science",    4, 60,  0.65),
    ("Feature Engineering","Data Science",    4, 50,  0.65),
    ("MLOps",              "AI/ML",           5, 70,  0.72),
    ("LLMs",               "AI/ML",           5, 60,  0.78),
    ("Prompt Engineering", "AI/ML",           3, 15,  0.42),
    ("Vector Databases",   "AI/ML",           4, 35,  0.60),
    ("Cloud Computing",    "Cloud",           3, 40,  0.50),
    ("AWS",                "Cloud",           4, 60,  0.62),
    ("Terraform",          "DevOps",          4, 35,  0.58),
    ("System Design",      "Architecture",    6, 80,  0.82),
    ("Authentication",     "Security",        3, 15,  0.50),
    ("Linear Algebra",     "Mathematics",     5, 80,  0.72),
    ("Quantum Computing",  "Quantum",         6, 200, 0.95),
    ("Qiskit",             "Quantum",         5, 100, 0.88),
    ("Quantum Algorithms", "Quantum",         6, 120, 0.92),
    ("Networking",         "Systems",         3, 30,  0.45),
    ("Elasticsearch",      "Databases",       4, 25,  0.55),
    ("Redis",              "Databases",       3, 15,  0.38),
    ("GraphQL",            "Backend",         3, 25,  0.45),
    ("Rust",               "Programming",     5, 100, 0.82),
    ("Go",                 "Programming",     4, 50,  0.60),
]


def _hash_password(password: str) -> str:
    result = bcrypt.generate_password_hash(password)
    return result.decode('utf-8') if isinstance(result, bytes) else result


def seed():
    app = create_app()
    with app.app_context():
        model = get_model()
        if model:
            print('[FNN] Loaded trained model for difficulty scoring')
        else:
            print('[FNN] No trained model found — using heuristic fallback')

        # ── Admin user ────────────────────────────────────────────────────
        if not Learner.query.filter_by(email='admin@ealps.dev').first():
            admin = Learner(
                email           = 'admin@ealps.dev',
                password_hash   = _hash_password('admin123'),
                full_name       = 'EALPS Admin',
                role            = 'admin',
                effort_capacity = 40.0,
            )
            db.session.add(admin)
            print('[OK] Admin created: admin@ealps.dev / admin123')

        # ── Demo learner ──────────────────────────────────────────────────
        if not Learner.query.filter_by(email='learner@ealps.dev').first():
            learner = Learner(
                email           = 'learner@ealps.dev',
                password_hash   = _hash_password('learner123'),
                full_name       = 'Demo Learner',
                role            = 'learner',
                effort_capacity = 15.0,
                prior_skills    = ['HTML', 'CSS', 'Git'],
            )
            db.session.add(learner)
            print('[OK] Demo learner: learner@ealps.dev / learner123')

        # ── Skills ────────────────────────────────────────────────────────
        added = 0
        for name, category, bloom, hours, cload in SKILLS:
            if Skill.query.filter_by(skill_name=name).first():
                continue

            prereq_count = max(0, bloom - 1)
            abstraction  = min(1.0, cload + 0.1)

            skill = Skill(
                skill_name           = name,
                category             = category,
                bloom_level          = bloom,
                avg_hours_to_learn   = float(hours),
                cognitive_load_score = cload,
            )
            db.session.add(skill)
            db.session.flush()

            ds = score_skill(bloom, prereq_count, abstraction, float(hours), model)
            sds = SkillDifficultyScore(
                skill_id           = skill.skill_id,
                difficulty_score   = ds,
                prerequisite_count = prereq_count,
                abstraction_level  = abstraction,
                model_version      = 'fnn_v1' if model else 'heuristic_v1',
            )
            db.session.add(sds)
            added += 1

        db.session.commit()
        print(f'[OK] {added} skills seeded with difficulty scores')

        # ── Market data ───────────────────────────────────────────────────
        print('[..] Simulating market data (6 months)...')
        simulate_market_data(months=6)
        print('[OK] Market data and decay detection complete')
        print('\nSeed complete. Run the backend: python run.py')


if __name__ == '__main__':
    seed()
