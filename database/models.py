"""
StudyFlow Data Models
Dataclasses representing core entities in the application:
Task, TaskCompletion, Category, StreakInfo, and AppSettings.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class Category:
    category_id: Optional[int] = None
    name: str = "General"
    color: str = "#6366F1"  # Modern Indigo
    icon: str = "bookmark"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Task:
    task_id: Optional[int] = None
    title: str = ""
    description: str = ""
    category_id: Optional[int] = None
    category_name: str = "General"
    category_color: str = "#6366F1"
    priority: str = "Medium"  # Low, Medium, High, Critical
    scheduled_date: str = ""  # YYYY-MM-DD (Base/start date)
    end_date: str = ""        # YYYY-MM-DD (Optional end date for date ranges / limits)
    custom_dates: str = ""    # JSON-encoded list of specific dates (e.g. '["2026-09-01", "2026-09-05"]')
    start_time: str = "09:00"  # HH:MM (24-hour)
    end_time: str = "10:00"  # HH:MM (24-hour)
    repeat_type: str = "None"  # None, Date Range, Daily, Weekly, Weekdays, Custom Dates
    reminder_minutes: int = 15  # Minutes before start_time (0 = disabled)
    created_at: str = ""
    is_active: bool = True

    def get_custom_dates_list(self) -> List[str]:
        """Returns parsed list of custom date strings."""
        if not self.custom_dates:
            return []
        try:
            dates = json.loads(self.custom_dates)
            if isinstance(dates, list):
                return sorted(list(set(str(d) for d in dates)))
        except Exception:
            pass
        return []

    def set_custom_dates_list(self, dates: List[str]):
        """Serializes list of custom dates into JSON string."""
        clean_dates = sorted(list(set(str(d).strip() for d in dates if d.strip())))
        self.custom_dates = json.dumps(clean_dates)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskCompletion:
    completion_id: Optional[int] = None
    task_id: int = 0
    completion_date: str = ""  # YYYY-MM-DD
    completed_at: str = ""  # ISO timestamp
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StreakInfo:
    task_id: Optional[int] = None
    total_completed_days: int = 0
    current_streak: int = 0
    best_streak: int = 0
    last_completed_date: Optional[str] = None
    completion_history: List[str] = field(default_factory=list)  # list of dates

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskInstance:
    """Represents a task for a specific target date, including completion status and streak metrics."""
    task: Task
    target_date: str
    is_completed: bool = False
    completed_at: Optional[str] = None
    streak_info: Optional[StreakInfo] = None

    @property
    def task_id(self) -> Optional[int]:
        return self.task.task_id

    @property
    def title(self) -> str:
        return self.task.title

    @property
    def description(self) -> str:
        return self.task.description

    @property
    def category_name(self) -> str:
        return self.task.category_name

    @property
    def category_color(self) -> str:
        return self.task.category_color

    @property
    def priority(self) -> str:
        return self.task.priority

    @property
    def start_time(self) -> str:
        return self.task.start_time

    @property
    def end_time(self) -> str:
        return self.task.end_time

    @property
    def scheduled_date(self) -> str:
        return self.task.scheduled_date

    @property
    def end_date(self) -> str:
        return self.task.end_date

    @property
    def repeat_type(self) -> str:
        return self.task.repeat_type

    @property
    def custom_dates(self) -> str:
        return self.task.custom_dates

    @property
    def reminder_minutes(self) -> int:
        return self.task.reminder_minutes


@dataclass
class AppSettings:
    user_name: str = "Student"
    theme: str = "dark"  # dark, light
    sound_enabled: bool = True
    default_reminder_min: int = 15

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
