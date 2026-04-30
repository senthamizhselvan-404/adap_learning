import uuid
from datetime import datetime
from ..extensions import db


def gen_uuid():
    return str(uuid.uuid4())


# ─────────────────────────────────────────
# JWT Token Blocklist  (logout / revocation)
# ─────────────────────────────────────────
class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'

    id         = db.Column(db.Integer, primary_key=True)
    jti        = db.Column(db.String(36), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────
# Learner
# ─────────────────────────────────────────
class Learner(db.Model):
    __tablename__ = 'learners'

    learner_id      = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    email           = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash   = db.Column(db.String(255), nullable=False, default='')
    full_name       = db.Column(db.String(200), nullable=False)
    role            = db.Column(db.String(20), nullable=False, default='learner')
    is_active       = db.Column(db.Boolean, default=True, nullable=False)
    prior_skills    = db.Column(db.JSON, nullable=True)
    effort_capacity = db.Column(db.Float, nullable=False, default=10.0)
    oauth_provider  = db.Column(db.String(50),  nullable=True)
    oauth_id        = db.Column(db.String(255), nullable=True, index=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    last_active     = db.Column(db.DateTime, nullable=True)

    pathways = db.relationship('LearningPathway', backref='learner', lazy='dynamic')
    progress = db.relationship('ProgressRecord',  backref='learner', lazy='dynamic')

    def to_dict(self):
        return {
            'learner_id':      self.learner_id,
            'email':           self.email,
            'full_name':       self.full_name,
            'role':            self.role,
            'is_active':       self.is_active,
            'prior_skills':    self.prior_skills or [],
            'effort_capacity': self.effort_capacity,
            'oauth_provider':  self.oauth_provider,
            'created_at':      self.created_at.isoformat(),
            'last_active':     self.last_active.isoformat() if self.last_active else None,
        }


# ─────────────────────────────────────────
# Skill
# ─────────────────────────────────────────
class Skill(db.Model):
    __tablename__ = 'skills'

    skill_id            = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    skill_name          = db.Column(db.String(300), unique=True, nullable=False, index=True)
    category            = db.Column(db.String(100), nullable=False, index=True)
    taxonomy_code       = db.Column(db.String(50), nullable=True)
    bloom_level         = db.Column(db.Integer, nullable=False, default=3)
    avg_hours_to_learn  = db.Column(db.Float, nullable=False, default=20.0)
    cognitive_load_score= db.Column(db.Float, nullable=False, default=0.5)
    is_active           = db.Column(db.Boolean, default=True, index=True)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)

    difficulty_score = db.relationship('SkillDifficultyScore', backref='skill', uselist=False)
    market_data      = db.relationship('MarketSkillData', backref='skill', lazy='dynamic')
    course_links     = db.relationship('CourseSkill', backref='skill', lazy='dynamic')
    progress_records = db.relationship('ProgressRecord', backref='skill', lazy='dynamic')

    def to_dict(self, include_market=False):
        d = {
            'skill_id':             self.skill_id,
            'skill_name':           self.skill_name,
            'category':             self.category,
            'bloom_level':          self.bloom_level,
            'avg_hours_to_learn':   self.avg_hours_to_learn,
            'cognitive_load_score': self.cognitive_load_score,
            'is_active':            self.is_active,
            'difficulty_score':     self.difficulty_score.difficulty_score if self.difficulty_score else None,
        }
        if include_market:
            latest = self.market_data.order_by(MarketSkillData.captured_at.desc()).first()
            d['market'] = latest.to_dict() if latest else None
        return d


# ─────────────────────────────────────────
# Skill Difficulty Score (FNN output)
# ─────────────────────────────────────────
class SkillDifficultyScore(db.Model):
    __tablename__ = 'skill_difficulty_scores'

    score_id           = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    skill_id           = db.Column(db.String(36), db.ForeignKey('skills.skill_id'), nullable=False, unique=True)
    difficulty_score   = db.Column(db.Float, nullable=False)
    prerequisite_count = db.Column(db.Integer, default=0)
    abstraction_level  = db.Column(db.Float, default=0.5)
    model_version      = db.Column(db.String(50), default='fnn_v1')
    scored_at          = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'difficulty_score':   self.difficulty_score,
            'prerequisite_count': self.prerequisite_count,
            'abstraction_level':  self.abstraction_level,
            'model_version':      self.model_version,
            'scored_at':          self.scored_at.isoformat(),
        }


# ─────────────────────────────────────────
# Learning Pathway
# ─────────────────────────────────────────
class LearningPathway(db.Model):
    __tablename__ = 'learning_pathways'

    pathway_id            = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    learner_id            = db.Column(db.String(36), db.ForeignKey('learners.learner_id'), nullable=False, index=True)
    target_role           = db.Column(db.String(200), nullable=False)
    status                = db.Column(db.String(20), default='active')
    total_estimated_hours = db.Column(db.Float, default=0.0)
    completion_percent    = db.Column(db.Float, default=0.0)
    generated_at          = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated          = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pathway_skills = db.relationship(
        'PathwaySkill', backref='pathway', lazy='dynamic',
        order_by='PathwaySkill.sequence_order'
    )

    VALID_STATUSES = frozenset({'active', 'completed', 'paused', 'abandoned'})

    def to_dict(self):
        skills = [ps.to_dict() for ps in self.pathway_skills.order_by(PathwaySkill.sequence_order)]
        return {
            'pathway_id':            self.pathway_id,
            'learner_id':            self.learner_id,
            'target_role':           self.target_role,
            'status':                self.status,
            'total_estimated_hours': self.total_estimated_hours,
            'completion_percent':    self.completion_percent,
            'generated_at':          self.generated_at.isoformat(),
            'last_updated':          self.last_updated.isoformat(),
            'skills':                skills,
        }


# ─────────────────────────────────────────
# Pathway Skills (join table with metadata)
# ─────────────────────────────────────────
class PathwaySkill(db.Model):
    __tablename__ = 'pathway_skills'

    __table_args__ = (
        db.Index('ix_pathway_skills_pathway_seq', 'pathway_id', 'sequence_order'),
    )

    id               = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    pathway_id       = db.Column(db.String(36), db.ForeignKey('learning_pathways.pathway_id'), nullable=False)
    skill_id         = db.Column(db.String(36), db.ForeignKey('skills.skill_id'), nullable=False, index=True)
    sequence_order   = db.Column(db.Integer, nullable=False)
    estimated_hours  = db.Column(db.Float, nullable=False)
    status           = db.Column(db.String(20), default='locked')
    difficulty_label = db.Column(db.String(20), default='medium')

    skill = db.relationship('Skill')

    def to_dict(self):
        return {
            'id':               self.id,
            'skill_id':         self.skill_id,
            'skill_name':       self.skill.skill_name if self.skill else '',
            'category':         self.skill.category if self.skill else '',
            'sequence_order':   self.sequence_order,
            'estimated_hours':  self.estimated_hours,
            'status':           self.status,
            'difficulty_label': self.difficulty_label,
            'bloom_level':      self.skill.bloom_level if self.skill else 0,
            'difficulty_score': (
                self.skill.difficulty_score.difficulty_score
                if self.skill and self.skill.difficulty_score else 0.5
            ),
        }


# ─────────────────────────────────────────
# Curriculum & Courses
# ─────────────────────────────────────────
class Curriculum(db.Model):
    __tablename__ = 'curricula'

    curriculum_id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    title         = db.Column(db.String(300), nullable=False)
    institution   = db.Column(db.String(200))
    created_by    = db.Column(db.String(36), db.ForeignKey('learners.learner_id'))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    raw_text      = db.Column(db.Text, nullable=True)

    courses = db.relationship('Course', backref='curriculum', lazy='dynamic')

    def to_dict(self):
        return {
            'curriculum_id': self.curriculum_id,
            'title':         self.title,
            'institution':   self.institution,
            'created_at':    self.created_at.isoformat(),
            'course_count':  self.courses.count(),
        }


class Course(db.Model):
    __tablename__ = 'courses'

    course_id     = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    curriculum_id = db.Column(db.String(36), db.ForeignKey('curricula.curriculum_id'), nullable=False)
    course_name   = db.Column(db.String(300), nullable=False)
    description   = db.Column(db.Text)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    course_skills = db.relationship('CourseSkill', backref='course', lazy='dynamic')

    def to_dict(self):
        return {
            'course_id':   self.course_id,
            'course_name': self.course_name,
            'description': self.description,
            'skills':      [cs.skill_id for cs in self.course_skills],
        }


class CourseSkill(db.Model):
    __tablename__ = 'course_skills'

    id        = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.course_id'), nullable=False)
    skill_id  = db.Column(db.String(36), db.ForeignKey('skills.skill_id'), nullable=False)


# ─────────────────────────────────────────
# Market Skill Data
# ─────────────────────────────────────────
class MarketSkillData(db.Model):
    __tablename__ = 'market_skill_data'

    __table_args__ = (
        db.Index('ix_market_skill_captured', 'skill_id', 'captured_at'),
    )

    market_id     = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    skill_id      = db.Column(db.String(36), db.ForeignKey('skills.skill_id'), nullable=False)
    demand_index  = db.Column(db.Float, nullable=False)
    growth_rate   = db.Column(db.Float, default=0.0)
    decay_flag    = db.Column(db.Boolean, default=False)
    emerging_flag = db.Column(db.Boolean, default=False)
    data_source   = db.Column(db.String(100), default='simulated')
    captured_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'demand_index':  self.demand_index,
            'growth_rate':   self.growth_rate,
            'decay_flag':    self.decay_flag,
            'emerging_flag': self.emerging_flag,
            'data_source':   self.data_source,
            'captured_at':   self.captured_at.isoformat(),
        }


# ─────────────────────────────────────────
# Progress Record
# ─────────────────────────────────────────
class ProgressRecord(db.Model):
    __tablename__ = 'progress_records'

    __table_args__ = (
        db.Index('ix_progress_learner_skill', 'learner_id', 'skill_id'),
    )

    id           = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    learner_id   = db.Column(db.String(36), db.ForeignKey('learners.learner_id'), nullable=False)
    skill_id     = db.Column(db.String(36), db.ForeignKey('skills.skill_id'), nullable=False)
    hours_logged = db.Column(db.Float, default=0.0)
    is_completed = db.Column(db.Boolean, default=False)
    logged_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'skill_id':     self.skill_id,
            'hours_logged': self.hours_logged,
            'is_completed': self.is_completed,
            'logged_at':    self.logged_at.isoformat(),
        }


# ─────────────────────────────────────────
# Practice Problem
# ─────────────────────────────────────────
class PracticeProblem(db.Model):
    __tablename__ = 'practice_problems'

    problem_id          = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    title               = db.Column(db.String(300), nullable=False, index=True)
    description         = db.Column(db.Text, nullable=False)
    difficulty          = db.Column(db.Integer, nullable=False, default=3)
    skill_id            = db.Column(db.String(36), db.ForeignKey('skills.skill_id'), nullable=True, index=True)
    languages_supported = db.Column(db.JSON, nullable=False, default=['python'])
    time_limit          = db.Column(db.Integer, nullable=False, default=5)
    memory_limit        = db.Column(db.Integer, nullable=False, default=256)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at          = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    skill = db.relationship('Skill')
    test_cases = db.relationship('ProblemTestCase', backref='problem', lazy='dynamic', cascade='all, delete-orphan')
    solutions = db.relationship('ProblemSolution', backref='problem', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, include_test_cases=False):
        d = {
            'problem_id':           self.problem_id,
            'title':                self.title,
            'description':          self.description,
            'difficulty':           self.difficulty,
            'skill_id':             self.skill_id,
            'skill_name':           self.skill.skill_name if self.skill else None,
            'languages_supported':  self.languages_supported,
            'time_limit':           self.time_limit,
            'memory_limit':         self.memory_limit,
            'created_at':           self.created_at.isoformat(),
        }
        if include_test_cases:
            d['test_cases'] = [tc.to_dict() for tc in self.test_cases.filter_by(is_hidden=False).all()]
        return d


# ─────────────────────────────────────────
# Problem Test Case
# ─────────────────────────────────────────
class ProblemTestCase(db.Model):
    __tablename__ = 'problem_test_cases'

    test_case_id     = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    problem_id       = db.Column(db.String(36), db.ForeignKey('practice_problems.problem_id'), nullable=False, index=True)
    input_data       = db.Column(db.Text, nullable=False)
    expected_output  = db.Column(db.Text, nullable=False)
    is_hidden        = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'test_case_id':    self.test_case_id,
            'input':           self.input_data,
            'expected_output': self.expected_output,
            'is_hidden':       self.is_hidden,
        }


# ─────────────────────────────────────────
# Problem Solution (Learner Submission)
# ─────────────────────────────────────────
class ProblemSolution(db.Model):
    __tablename__ = 'problem_solutions'

    __table_args__ = (
        db.Index('ix_problem_solutions_learner_problem', 'learner_id', 'problem_id'),
    )

    solution_id    = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    problem_id     = db.Column(db.String(36), db.ForeignKey('practice_problems.problem_id'), nullable=False)
    learner_id     = db.Column(db.String(36), db.ForeignKey('learners.learner_id'), nullable=False, index=True)
    code           = db.Column(db.Text, nullable=False)
    language       = db.Column(db.String(20), nullable=False, default='python')
    status         = db.Column(db.String(20), nullable=False, default='submitted')
    test_results   = db.Column(db.JSON, nullable=True)
    execution_time = db.Column(db.Float, nullable=True)
    score          = db.Column(db.Float, nullable=True)
    submitted_at   = db.Column(db.DateTime, default=datetime.utcnow)
    last_executed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'solution_id':       self.solution_id,
            'problem_id':        self.problem_id,
            'learner_id':        self.learner_id,
            'language':          self.language,
            'status':            self.status,
            'test_results':      self.test_results,
            'execution_time':    self.execution_time,
            'score':             self.score,
            'submitted_at':      self.submitted_at.isoformat(),
            'last_executed_at':  self.last_executed_at.isoformat() if self.last_executed_at else None,
        }


# ─────────────────────────────────────────
# YouTube Video Track (Chrome Extension)
# ─────────────────────────────────────────
class VideoTrack(db.Model):
    __tablename__ = 'video_tracks'

    __table_args__ = (
        db.UniqueConstraint('learner_id', 'video_id', name='uq_learner_video'),
    )

    track_id     = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    learner_id   = db.Column(db.String(36), db.ForeignKey('learners.learner_id'), nullable=False, index=True)
    video_id     = db.Column(db.String(50),  nullable=False, index=True)
    video_title  = db.Column(db.String(500), nullable=True)
    channel_name = db.Column(db.String(200), nullable=True)
    skill_id     = db.Column(db.String(36),  db.ForeignKey('skills.skill_id'), nullable=True)
    total_watched_seconds = db.Column(db.Integer,  default=0,     nullable=False)
    is_completed          = db.Column(db.Boolean,  default=False,  nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'track_id':             self.track_id,
            'video_id':             self.video_id,
            'video_title':          self.video_title,
            'channel_name':         self.channel_name,
            'skill_id':             self.skill_id,
            'total_watched_seconds': self.total_watched_seconds,
            'is_completed':         self.is_completed,
        }


# ─────────────────────────────────────────
# Practice Session
# ─────────────────────────────────────────
class PracticeSession(db.Model):
    __tablename__ = 'practice_sessions'

    __table_args__ = (
        db.Index('ix_practice_sessions_learner', 'learner_id'),
    )

    session_id              = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    learner_id              = db.Column(db.String(36), db.ForeignKey('learners.learner_id'), nullable=False)
    skill_id                = db.Column(db.String(36), db.ForeignKey('skills.skill_id'), nullable=True)
    total_problems_attempted = db.Column(db.Integer, default=0)
    total_problems_solved    = db.Column(db.Integer, default=0)
    total_duration          = db.Column(db.Integer, default=0)
    average_score           = db.Column(db.Float, nullable=True)
    started_at              = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at                = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'session_id':                self.session_id,
            'learner_id':                self.learner_id,
            'skill_id':                  self.skill_id,
            'total_problems_attempted':  self.total_problems_attempted,
            'total_problems_solved':     self.total_problems_solved,
            'total_duration':            self.total_duration,
            'average_score':             self.average_score,
            'started_at':                self.started_at.isoformat(),
            'ended_at':                  self.ended_at.isoformat() if self.ended_at else None,
        }
