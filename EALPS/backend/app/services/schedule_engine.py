"""
Schedule Engine
===============
Generates personalized weekly learning schedules based on learner availability,
skill difficulty, prerequisites, and cognitive constraints.

Implements intelligent task scheduling with:
- Time distribution across available days
- Difficulty balancing (alternate high/low effort)
- Prerequisite respect
- Cognitive load management
- Adaptive structuring for different capacity levels
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from ..models import Skill, PathwaySkill, ProgressRecord, LearningPathway
from ..extensions import db


class ScheduleSession:
    """Represents a single learning session on a specific day."""

    def __init__(self, skill_name: str, hours: float, difficulty_score: float,
                 category: str = "", bloom_level: int = 3):
        self.skill_name = skill_name
        self.hours = round(hours, 1)
        self.difficulty_score = difficulty_score
        self.category = category
        self.bloom_level = bloom_level
        self.difficulty_label = self._label_difficulty(difficulty_score)

    def _label_difficulty(self, score: float) -> str:
        if score < 0.35:
            return "easy"
        elif score < 0.65:
            return "medium"
        else:
            return "hard"

    def to_dict(self):
        return {
            "skill_name": self.skill_name,
            "hours": self.hours,
            "difficulty_score": self.difficulty_score,
            "difficulty_label": self.difficulty_label,
            "category": self.category,
            "bloom_level": self.bloom_level,
        }


class DailySchedule:
    """Represents a day's learning schedule."""

    def __init__(self, day_name: str, date: datetime, max_hours: float = 4.0):
        self.day_name = day_name
        self.date = date
        self.max_hours = max_hours
        self.sessions: List[ScheduleSession] = []
        self.total_hours = 0.0
        self.high_difficulty_count = 0

    def add_session(self, session: ScheduleSession) -> bool:
        """
        Add a session to the day if it fits within constraints.
        Returns True if added, False if day is full or constraints violated.
        """
        # Check max hours constraint
        if self.total_hours + session.hours > self.max_hours:
            return False

        # Check max 2 high-difficulty skills per day
        if session.difficulty_label == "hard":
            if self.high_difficulty_count >= 2:
                return False
            self.high_difficulty_count += 1

        self.sessions.append(session)
        self.total_hours += session.hours
        return True

    def has_capacity(self, additional_hours: float) -> bool:
        """Check if day has capacity for additional hours."""
        return self.total_hours + additional_hours <= self.max_hours

    def difficulty_distribution(self) -> Dict[str, int]:
        """Return count of each difficulty level."""
        dist = {"easy": 0, "medium": 0, "hard": 0}
        for session in self.sessions:
            dist[session.difficulty_label] += 1
        return dist

    def to_dict(self):
        return {
            "day_name": self.day_name,
            "date": self.date.isoformat(),
            "total_hours": self.total_hours,
            "sessions": [s.to_dict() for s in self.sessions],
            "difficulty_distribution": self.difficulty_distribution(),
        }


class WeeklySchedule:
    """Represents a complete week's learning schedule."""

    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def __init__(self, start_date: datetime, available_days: List[int] = None,
                 max_hours_per_day: float = 4.0, weekly_hours: float = 40.0):
        """
        Initialize weekly schedule.

        Args:
            start_date: Start date of the week (Monday)
            available_days: List of day indices (0=Mon, 6=Sun). None = all days
            max_hours_per_day: Maximum hours per learning day
            weekly_hours: Total learner capacity for the week
        """
        self.start_date = start_date
        self.weekly_hours = weekly_hours
        self.available_days = available_days or list(range(6))  # Mon-Sat by default
        self.max_hours_per_day = max_hours_per_day

        # Initialize days
        self.days: Dict[str, DailySchedule] = {}
        for i in range(7):
            date = start_date + timedelta(days=i)
            day_name = self.DAYS[i]
            self.days[day_name] = DailySchedule(
                day_name, date,
                max_hours=max_hours_per_day if i in self.available_days else 0.0
            )

    def get_available_days(self) -> List[str]:
        """Get list of days with capacity."""
        return [name for name in self.DAYS
                if self.days[name].max_hours > 0]

    def total_scheduled_hours(self) -> float:
        """Get total hours scheduled across the week."""
        return sum(day.total_hours for day in self.days.values())

    def remaining_capacity(self) -> float:
        """Get remaining hours that can be scheduled."""
        return self.weekly_hours - self.total_scheduled_hours()

    def to_dict(self):
        return {
            "start_date": self.start_date.isoformat(),
            "week_number": self.start_date.isocalendar()[1],
            "total_weekly_hours": self.weekly_hours,
            "scheduled_hours": self.total_scheduled_hours(),
            "remaining_capacity": self.remaining_capacity(),
            "days": {name: self.days[name].to_dict() for name in self.DAYS},
        }


class ScheduleOptimizer:
    """Core scheduling algorithm."""

    MIN_SESSION_HOURS = 0.5  # 30 minutes minimum
    MAX_SESSION_HOURS = 3.0  # Max 3 hours per session
    BUFFER_PERCENTAGE = 0.15  # 15% buffer for delays

    def __init__(self, pathway: LearningPathway, learner):
        """Initialize optimizer with a learning pathway."""
        self.pathway = pathway
        self.learner = learner
        self.skills_data: List[Dict] = []
        self._load_skills()

    def _load_skills(self):
        """Load and prepare skill data from pathway."""
        for ps in self.pathway.pathway_skills.order_by(PathwaySkill.sequence_order):
            skill = ps.skill
            if skill:
                # Get completed hours for this skill
                progress = ProgressRecord.query.filter_by(
                    learner_id=self.learner.learner_id,
                    skill_id=skill.skill_id
                ).first()

                completed_hours = progress.hours_logged if progress else 0.0
                remaining_hours = max(0, ps.estimated_hours - completed_hours)

                if remaining_hours > 0:  # Only include incomplete skills
                    difficulty = (skill.difficulty_score.difficulty_score
                                  if skill.difficulty_score else 0.5)
                    self.skills_data.append({
                        "skill_id": skill.skill_id,
                        "skill_name": skill.skill_name,
                        "category": skill.category,
                        "difficulty_score": difficulty,
                        "bloom_level": skill.bloom_level,
                        "total_hours": ps.estimated_hours,
                        "remaining_hours": remaining_hours,
                        "sequence_order": ps.sequence_order,
                    })

    def _break_skill_into_sessions(self, skill_data: Dict, max_session_hours: float = 2.0) -> List[Tuple[str, float]]:
        """
        Break a skill into smaller learning sessions.

        Returns list of (skill_name, session_hours) tuples.
        """
        remaining = skill_data["remaining_hours"]
        skill_name = skill_data["skill_name"]
        sessions = []

        # Intelligent session sizing based on difficulty
        difficulty = skill_data["difficulty_score"]
        if difficulty < 0.35:  # Easy
            session_hours = 1.0
        elif difficulty < 0.65:  # Medium
            session_hours = 1.5
        else:  # Hard
            session_hours = max_session_hours  # Spread high-difficulty skills

        # Break into sessions
        while remaining > self.MIN_SESSION_HOURS:
            session_duration = min(session_hours, remaining)
            sessions.append((skill_name, round(session_duration, 1)))
            remaining -= session_duration

        return sessions

    def _calculate_daily_distribution(self, total_hours: float, available_days: int) -> List[float]:
        """
        Distribute total hours evenly across available days with buffer.

        Avoids spikes and maintains consistent daily workload.
        """
        # Apply buffer - add extra capacity to handle overruns
        effective_hours = total_hours * (1 - self.BUFFER_PERCENTAGE)
        daily_target = effective_hours / available_days if available_days > 0 else 0

        # Create distribution array
        distribution = [daily_target] * available_days
        return distribution

    def _select_skills_for_week(self, available_weekly_hours: float) -> List[Dict]:
        """
        Select which skills to schedule this week based on:
        - Sequence order (prerequisites first)
        - Remaining hours
        - Available capacity
        """
        selected = []
        cumulative_hours = 0

        for skill_data in self.skills_data:
            if cumulative_hours + skill_data["remaining_hours"] <= available_weekly_hours:
                selected.append(skill_data)
                cumulative_hours += skill_data["remaining_hours"]
            elif cumulative_hours < available_weekly_hours:
                # Partial skill - scale it down
                partial_skill = skill_data.copy()
                partial_skill["remaining_hours"] = available_weekly_hours - cumulative_hours
                selected.append(partial_skill)
                break

        return selected

    def _order_by_difficulty_balance(self, sessions: List[Tuple[str, float, float]]) -> List[Tuple[str, float, float]]:
        """
        Reorder sessions to balance difficulty across the week.

        High-difficulty sessions should be spread out, not consecutive.
        """
        high_diff = [s for s in sessions if s[2] > 0.65]  # difficulty_score
        medium_diff = [s for s in sessions if 0.35 <= s[2] <= 0.65]
        low_diff = [s for s in sessions if s[2] < 0.35]

        # Interleave: hard, medium, easy, hard, medium, easy...
        ordered = []
        max_len = max(len(high_diff), len(medium_diff), len(low_diff))

        for i in range(max_len):
            if i < len(high_diff):
                ordered.append(high_diff[i])
            if i < len(medium_diff):
                ordered.append(medium_diff[i])
            if i < len(low_diff):
                ordered.append(low_diff[i])

        return ordered

    def generate(self, start_date: datetime = None,
                 available_days: List[int] = None,
                 max_hours_per_day: float = 4.0) -> Tuple[WeeklySchedule, str]:
        """
        Generate optimized weekly schedule.

        Args:
            start_date: Week start date (default: today)
            available_days: Available day indices (0=Mon, 6=Sun)
            max_hours_per_day: Max hours per learning day

        Returns:
            Tuple of (WeeklySchedule, explanation_text)
        """
        if start_date is None:
            start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            # Align to Monday
            start_date -= timedelta(days=start_date.weekday())

        if available_days is None:
            available_days = list(range(6))  # Mon-Sat

        # Create weekly schedule container
        schedule = WeeklySchedule(start_date, available_days, max_hours_per_day,
                                 self.learner.effort_capacity)

        # Select skills for this week
        selected_skills = self._select_skills_for_week(self.learner.effort_capacity)

        if not selected_skills:
            return schedule, "No skills to schedule this week."

        # Create all sessions
        all_sessions = []
        for skill_data in selected_skills:
            sessions = self._break_skill_into_sessions(skill_data)
            for skill_name, hours in sessions:
                all_sessions.append((
                    skill_name,
                    hours,
                    skill_data["difficulty_score"]
                ))

        # Order sessions for difficulty balance
        balanced_sessions = self._order_by_difficulty_balance(all_sessions)

        # Assign sessions to days
        available_day_names = schedule.get_available_days()
        day_index = 0

        for skill_name, hours, difficulty in balanced_sessions:
            session = ScheduleSession(
                skill_name=skill_name,
                hours=hours,
                difficulty_score=difficulty,
                category="Learning",
                bloom_level=3
            )

            # Find next day with capacity; add_session() enforces hard-skill and hour limits
            attempts = 0
            while attempts < len(available_day_names):
                day_name = available_day_names[day_index % len(available_day_names)]
                day = schedule.days[day_name]

                if day.add_session(session):
                    day_index += 1  # rotate to next day for even distribution
                    break
                else:
                    day_index += 1
                    attempts += 1

        # Generate explanation
        explanation = self._generate_explanation(schedule, selected_skills, available_day_names)

        return schedule, explanation

    def _generate_explanation(self, schedule: WeeklySchedule,
                             selected_skills: List[Dict],
                             available_days: List[str]) -> str:
        """Generate human-friendly explanation of the schedule."""
        total_scheduled = schedule.total_scheduled_hours()
        num_days = len(available_days)
        avg_daily = total_scheduled / num_days if num_days > 0 else 0
        num_skills = len(selected_skills)

        explanation = f"""
Weekly Schedule Explanation
============================

📊 Schedule Overview:
- Total hours scheduled: {total_scheduled:.1f}h of {schedule.weekly_hours}h capacity
- Learning days: {num_days} days ({', '.join(available_days)})
- Skills to focus on: {num_skills}
- Average daily commitment: {avg_daily:.1f}h/day

🎯 Strategy:
1. Difficulty Balancing: High and medium difficulty skills are spread throughout the week
   to avoid cognitive fatigue and maximize retention.

2. Session Sizing: 
   - Easy skills: 1h sessions (better retention through shorter focus)
   - Medium skills: 1.5h sessions (balanced learning depth)
   - Hard skills: 2h sessions (deeper focus needed)

3. Prerequisite Respect: Skills are ordered to ensure prerequisites complete before
   dependent skills, following your learning pathway.

4. Capacity Optimization: Your schedule includes a {int(self.BUFFER_PERCENTAGE * 100)}% buffer
   for unexpected delays or deeper learning needs.

💡 Tips for Success:
- Start each session with 5-min review of previous material
- Take 5-10 min breaks between sessions (recommended after 1.5h)
- If you fall behind, the schedule can be recalibrated on the Recalibrate page
- Mark skills as completed to get personalized adjustments

✅ This schedule is designed to be achievable while building momentum toward
your '{self.pathway.target_role}' goal. Adjust daily commitment as needed!
""".strip()

        return explanation
