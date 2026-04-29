"""
Pathway Engine
==============
Generates personalised, effort-aware, difficulty-sequenced learning pathways.
Implements topological sorting with skill dependencies and bloom level.
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

# Skill dependencies: skill_name -> list of prerequisite skill names
SKILL_DEPENDENCIES = {
    # Web Development
    "HTML":                ["Git"],
    "CSS":                 ["HTML"],
    "JavaScript":          ["HTML", "CSS"],
    "TypeScript":          ["JavaScript"],
    "React":               ["JavaScript"],
    "Node.js":             ["JavaScript"],
    "REST APIs":           ["Node.js"],
    "GraphQL":             ["REST APIs"],
    
    # Databases
    "SQL":                 ["Git"],
    "PostgreSQL":          ["SQL"],
    "Redis":               ["SQL"],
    "Elasticsearch":       ["SQL"],
    
    # DevOps & Systems
    "Git":                 [],
    "Linux":               ["Git"],
    "Shell Scripting":     ["Linux"],
    "Docker":              ["Git", "Linux"],
    "Kubernetes":          ["Docker"],
    "CI/CD":               ["Docker", "Git"],
    "AWS":                 ["Linux"],
    "Terraform":           ["AWS"],
    "Networking":          ["Linux"],
    
    # Programming Fundamentals
    "Python":              ["Git"],
    "Go":                  ["Python"],
    "Rust":                ["Python"],
    
    # Data Science
    "Statistics":          ["Python"],
    "NumPy":               ["Python"],
    "Pandas":              ["Python", "NumPy"],
    "Data Visualization":  ["Python", "Pandas"],
    "Feature Engineering": ["Statistics", "Pandas"],
    
    # AI/ML
    "Machine Learning":    ["Python", "Statistics"],
    "Deep Learning":       ["Machine Learning"],
    "TensorFlow":          ["Deep Learning"],
    "PyTorch":             ["Deep Learning"],
    "LLMs":                ["Deep Learning"],
    "Prompt Engineering":  ["LLMs"],
    "Vector Databases":    ["LLMs"],
    "MLOps":               ["Machine Learning", "Docker", "Cloud Computing"],
    
    # Cloud & Advanced
    "Cloud Computing":     ["Linux"],
    "System Design":       ["REST APIs", "SQL", "Authentication"],
    "Authentication":      ["Python", "REST APIs"],
    
    # Mathematics & Quantum
    "Linear Algebra":      ["Python"],
    "Quantum Computing":   ["Linear Algebra"],
    "Qiskit":              ["Quantum Computing"],
    "Quantum Algorithms":  ["Qiskit"],
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
    """
    Topological sort with Kahn's algorithm respecting skill dependencies.
    Breaks ties by (bloom_level, difficulty_score) for consistent ordering.
    Returns skills in prerequisite order, then by difficulty level.
    """
    # Build skill name -> skill object map
    skill_map = {s.skill_name: s for s in skills}
    skill_names_set = set(skill_map.keys())
    
    # Build in-degree counts for topological sort
    in_degree = {s.skill_name: 0 for s in skills}
    adj_list = {s.skill_name: [] for s in skills}
    
    for skill_name, skill in skill_map.items():
        # Get prerequisites from SKILL_DEPENDENCIES
        prereqs = SKILL_DEPENDENCIES.get(skill_name, [])
        # Only include prerequisites that are in the current skill list
        valid_prereqs = [p for p in prereqs if p in skill_names_set]
        
        for prereq in valid_prereqs:
            adj_list[prereq].append(skill_name)
            in_degree[skill_name] += 1
    
    # Kahn's algorithm: process nodes with no incoming edges
    queue = [name for name in skill_map.keys() if in_degree[name] == 0]
    
    # Sort queue by (bloom_level, difficulty_score) for stable ordering
    def queue_sort_key(name):
        skill = skill_map[name]
        ds = skill.difficulty_score.difficulty_score if skill.difficulty_score else 0.5
        return (skill.bloom_level, ds)
    
    queue.sort(key=queue_sort_key)
    
    result = []
    while queue:
        # Always pick the next node with lowest (bloom_level, difficulty_score)
        queue.sort(key=queue_sort_key)
        current = queue.pop(0)
        result.append(skill_map[current])
        
        # Process neighbors
        for neighbor in adj_list[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # If result length != original skills, there's a cycle (shouldn't happen with valid data)
    if len(result) != len(skills):
        # Fallback: sort by (bloom_level, difficulty_score) if cycle detected
        def sort_key(s):
            ds = s.difficulty_score.difficulty_score if s.difficulty_score else 0.5
            return (s.bloom_level, ds)
        result = sorted(skills, key=sort_key)
    
    return result


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
