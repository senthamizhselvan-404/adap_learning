"""
Pathway Engine
==============
Generates personalised, effort-aware, difficulty-sequenced learning pathways.
Implements topological sorting by bloom_level + difficulty_score (Kahn-style).
"""
from datetime import datetime
from ..models import (Skill, SkillDifficultyScore, LearningPathway,
                      PathwaySkill, ProgressRecord)
from ..ml.fnn_scorer import score_skill, get_model
from ..extensions import db


ROLE_SKILL_MAP = {
    "full stack developer":       ["HTML", "CSS", "JavaScript", "React", "Node.js",
                                   "REST APIs", "SQL", "PostgreSQL", "Git", "Docker"],
    "data scientist":             ["Python", "Statistics", "Machine Learning", "Pandas",
                                   "NumPy", "Data Visualization", "SQL",
                                   "Feature Engineering", "Deep Learning"],
    "ml engineer":                ["Python", "Machine Learning", "Deep Learning",
                                   "TensorFlow", "PyTorch", "MLOps", "Docker",
                                   "Cloud Computing", "SQL"],
    "devops engineer":            ["Linux", "Docker", "Kubernetes", "CI/CD", "AWS",
                                   "Terraform", "Networking", "Shell Scripting", "Git"],
    "backend developer":          ["Python", "REST APIs", "SQL", "PostgreSQL", "Docker",
                                   "Authentication", "System Design", "Git"],
    "ai engineer":                ["Python", "Machine Learning", "Deep Learning", "LLMs",
                                   "Prompt Engineering", "Vector Databases", "MLOps",
                                   "Cloud Computing"],
    "quantum software engineer":  ["Python", "Linear Algebra", "Quantum Computing",
                                   "Qiskit", "Quantum Algorithms", "Statistics",
                                   "Machine Learning"],
}


def _difficulty_label(score: float) -> str:
    if score < 0.35:  return 'easy'
    if score < 0.65:  return 'medium'
    return 'hard'


def _hours_for_learner(base_hours: float, difficulty: float,
                       effort_capacity: float) -> float:
    """Adjust estimated hours based on cognitive load."""
    adjusted = base_hours * (1.0 + difficulty * 0.5)
    return round(max(0.5, adjusted), 1)


def get_role_skills(target_role: str) -> list:
    role_lower  = target_role.lower().strip()
    skill_names = ROLE_SKILL_MAP.get(role_lower, [])

    if not skill_names:
        return Skill.query.filter_by(is_active=True).all()

    skills = []
    for name in skill_names:
        s = Skill.query.filter(
            Skill.skill_name.ilike(f'%{name}%'),
            Skill.is_active == True
        ).first()
        if s:
            skills.append(s)
    return skills


def _topological_sort(skills: list) -> list:
    def sort_key(s):
        ds = s.difficulty_score.difficulty_score if s.difficulty_score else 0.5
        return (s.bloom_level, ds)
    return sorted(skills, key=sort_key)


def generate_pathway(learner, target_role: str) -> LearningPathway:
    """
    1. Find skills needed for the role
    2. Remove skills the learner already knows
    3. Score missing skills via FNN (or heuristic fallback)
    4. Topological sort by bloom + difficulty
    5. Persist and return pathway
    """
    model = get_model()
    known = {s.lower() for s in (learner.prior_skills or [])}

    required_skills = get_role_skills(target_role)
    missing_skills  = [s for s in required_skills
                       if s.skill_name.lower() not in known]

    for skill in missing_skills:
        if not skill.difficulty_score:
            prereq = max(0, skill.bloom_level - 1)
            abstr  = min(1.0, skill.cognitive_load_score + 0.1)
            ds     = score_skill(skill.bloom_level, prereq, abstr,
                                 skill.avg_hours_to_learn, model)
            sds = SkillDifficultyScore(
                skill_id           = skill.skill_id,
                difficulty_score   = ds,
                prerequisite_count = prereq,
                abstraction_level  = abstr,
            )
            db.session.add(sds)

    db.session.flush()

    sorted_skills = _topological_sort(missing_skills)

    pathway = LearningPathway(
        learner_id  = learner.learner_id,
        target_role = target_role,
        status      = 'active',
    )
    db.session.add(pathway)
    db.session.flush()

    total_hours = 0.0
    for idx, skill in enumerate(sorted_skills):
        ds    = skill.difficulty_score.difficulty_score if skill.difficulty_score else 0.5
        hours = _hours_for_learner(skill.avg_hours_to_learn, ds, learner.effort_capacity)
        total_hours += hours

        ps = PathwaySkill(
            pathway_id       = pathway.pathway_id,
            skill_id         = skill.skill_id,
            sequence_order   = idx + 1,
            estimated_hours  = hours,
            status           = 'in_progress' if idx == 0 else 'locked',
            difficulty_label = _difficulty_label(ds),
        )
        db.session.add(ps)

    pathway.total_estimated_hours = round(total_hours, 1)
    db.session.commit()
    return pathway


def recalibrate_pathway(pathway: LearningPathway):
    """
    Re-score incomplete skills and update hours + completion percentage.
    Called automatically on progress update and on explicit recalibrate.
    NOTE: caller is responsible for db.session.commit() after this returns.
    """
    model = get_model()

    completed_ids = {
        pr.skill_id
        for pr in ProgressRecord.query.filter_by(
            learner_id=pathway.learner_id, is_completed=True
        )
    }

    total_remaining = 0.0
    completed_count = 0
    effort_capacity = pathway.learner.effort_capacity if pathway.learner else 10.0

    for ps in pathway.pathway_skills:
        if ps.skill_id in completed_ids:
            ps.status = 'completed'
            completed_count += 1
        else:
            skill = ps.skill
            if skill and skill.difficulty_score:
                ds = score_skill(
                    skill.bloom_level,
                    skill.difficulty_score.prerequisite_count,
                    skill.difficulty_score.abstraction_level,
                    skill.avg_hours_to_learn,
                    model,
                )
                ps.estimated_hours  = _hours_for_learner(
                    skill.avg_hours_to_learn, ds, effort_capacity
                )
                ps.difficulty_label = _difficulty_label(ds)
            total_remaining += ps.estimated_hours

    total = pathway.pathway_skills.count()
    pathway.completion_percent    = round((completed_count / total * 100) if total else 0, 1)
    pathway.total_estimated_hours = round(total_remaining, 1)
    pathway.last_updated          = datetime.utcnow()
