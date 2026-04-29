"""
Market Data Simulator
======================
Generates synthetic market demand data for skills.
In production, replace simulate_market_data() with real API calls
(LinkedIn Talent Insights / O*NET / Glassdoor).
"""
import math
import random
from datetime import datetime, timedelta
from ..models import Skill, MarketSkillData
from ..ml.decay_detector import evaluate_skill_market
from ..extensions import db

HOT_SKILLS      = {"llms", "machine learning", "deep learning", "cloud computing",
                   "kubernetes", "prompt engineering", "vector databases", "mlops",
                   "quantum computing", "rust", "react", "typescript"}

DECLINING_SKILLS = {"jquery", "php", "flash", "objective-c", "soap apis"}


def get_base_demand(skill_name: str) -> float:
    name = skill_name.lower()
    if any(h in name for h in HOT_SKILLS):
        return random.uniform(70, 95)
    if any(d in name for d in DECLINING_SKILLS):
        return random.uniform(10, 30)
    return random.uniform(35, 75)


def _safe_demand(value: float) -> float:
    """Clamp and guard against NaN/Inf."""
    if not math.isfinite(value):
        return 50.0
    return max(1.0, min(100.0, value))


def simulate_market_data(months: int = 6):
    """
    Populate market_skill_data with synthetic historical data
    for all active skills over `months` months.
    """
    skills = Skill.query.filter_by(is_active=True).all()
    now    = datetime.utcnow()

    batch = []
    for skill in skills:
        recent = (
            MarketSkillData.query
            .filter_by(skill_id=skill.skill_id)
            .order_by(MarketSkillData.captured_at.desc())
            .first()
        )
        if recent and (now - recent.captured_at).days < 25:
            continue

        base   = get_base_demand(skill.skill_name)
        demand = base
        name   = skill.skill_name.lower()

        for m in range(months, 0, -1):
            if any(h in name for h in HOT_SKILLS):
                growth = random.uniform(0.05, 0.35)
            elif any(d in name for d in DECLINING_SKILLS):
                growth = random.uniform(-0.25, -0.05)
            else:
                growth = random.uniform(-0.10, 0.15)

            demand  = _safe_demand(demand * (1 + growth))
            growth  = round(growth, 4)
            captured = now - timedelta(days=30 * m)

            batch.append(MarketSkillData(
                skill_id      = skill.skill_id,
                demand_index  = round(demand, 2),
                growth_rate   = growth,
                decay_flag    = False,
                emerging_flag = False,
                data_source   = 'simulated',
                captured_at   = captured,
            ))

    if batch:
        db.session.bulk_save_objects(batch)
        db.session.commit()

    run_decay_detection()


def run_decay_detection():
    """Apply decay/emergence flags to all skills based on their market history."""
    skills = Skill.query.filter_by(is_active=True).all()
    for skill in skills:
        records = (
            MarketSkillData.query
            .filter_by(skill_id=skill.skill_id)
            .order_by(MarketSkillData.captured_at.asc())
            .all()
        )
        if not records:
            continue

        result = evaluate_skill_market([r.to_dict() for r in records])
        latest = records[-1]
        latest.decay_flag    = result['decay_flag']
        latest.emerging_flag = result['emerging_flag']

    db.session.commit()
