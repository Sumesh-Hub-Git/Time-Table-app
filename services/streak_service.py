"""
StudyFlow Streak Calculation Service
Implements algorithms for:
- Total completion days counter
- Current consecutive streak calculation
- Best streak calculation (longest consecutive chain)
- Task completion history retrieval
- Global overall productivity streak
"""

from datetime import date, timedelta
from typing import List, Set, Optional, Dict, Any
from database.models import StreakInfo
from database.db import DatabaseManager, get_db
from utils.date_helpers import parse_date, today_date


class StreakService:
    """Service dedicated to calculating completion counters and streaks."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()

    def get_task_completion_dates(self, task_id: int) -> List[date]:
        """Returns sorted list of unique completed date objects for a specific task."""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT completion_date
                FROM task_completions
                WHERE task_id = ?
                ORDER BY completion_date ASC;
            """, (task_id,))
            rows = cursor.fetchall()
            return [parse_date(row["completion_date"]) for row in rows]

    def calculate_task_streak(self, task_id: int) -> StreakInfo:
        """Calculates total completed days, current streak, best streak, and history for a task."""
        completed_dates = self.get_task_completion_dates(task_id)
        if not completed_dates:
            return StreakInfo(
                task_id=task_id,
                total_completed_days=0,
                current_streak=0,
                best_streak=0,
                last_completed_date=None,
                completion_history=[]
            )

        total_days = len(completed_dates)
        date_set = set(completed_dates)
        sorted_dates = sorted(completed_dates)
        last_date = sorted_dates[-1]

        # Calculate Best Streak
        best_streak = 0
        current_sequence = 0
        prev_date: Optional[date] = None

        for d in sorted_dates:
            if prev_date is None:
                current_sequence = 1
            elif (d - prev_date).days == 1:
                current_sequence += 1
            elif (d - prev_date).days == 0:
                # Same day duplicate guard
                pass
            else:
                current_sequence = 1

            if current_sequence > best_streak:
                best_streak = current_sequence
            prev_date = d

        # Calculate Current Streak
        # Current streak looks backwards from today (if completed today)
        # OR from yesterday (if today is still in progress and not yet completed).
        today = today_date()
        yesterday = today - timedelta(days=1)

        current_streak = 0
        check_date = None

        if today in date_set:
            check_date = today
        elif yesterday in date_set:
            check_date = yesterday

        if check_date is not None:
            streak_count = 0
            curr = check_date
            while curr in date_set:
                streak_count += 1
                curr = curr - timedelta(days=1)
            current_streak = streak_count

        return StreakInfo(
            task_id=task_id,
            total_completed_days=total_days,
            current_streak=current_streak,
            best_streak=best_streak,
            last_completed_date=last_date.isoformat() if last_date else None,
            completion_history=[d.isoformat() for d in sorted_dates]
        )

    def get_global_streak(self) -> Dict[str, Any]:
        """
        Calculates global streaks across all user tasks.
        A day counts as active if at least one task was completed on that date.
        """
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT completion_date
                FROM task_completions
                ORDER BY completion_date ASC;
            """)
            rows = cursor.fetchall()
            completed_dates = [parse_date(row["completion_date"]) for row in rows]

        if not completed_dates:
            return {
                "total_completed_days": 0,
                "current_streak": 0,
                "best_streak": 0,
                "last_active_date": None
            }

        total_days = len(completed_dates)
        date_set = set(completed_dates)
        sorted_dates = sorted(completed_dates)

        # Best Streak
        best_streak = 0
        current_sequence = 0
        prev_date: Optional[date] = None

        for d in sorted_dates:
            if prev_date is None:
                current_sequence = 1
            elif (d - prev_date).days == 1:
                current_sequence += 1
            elif (d - prev_date).days == 0:
                pass
            else:
                current_sequence = 1

            if current_sequence > best_streak:
                best_streak = current_sequence
            prev_date = d

        # Current Streak
        today = today_date()
        yesterday = today - timedelta(days=1)

        current_streak = 0
        check_date = None
        if today in date_set:
            check_date = today
        elif yesterday in date_set:
            check_date = yesterday

        if check_date is not None:
            streak_count = 0
            curr = check_date
            while curr in date_set:
                streak_count += 1
                curr = curr - timedelta(days=1)
            current_streak = streak_count

        return {
            "total_completed_days": total_days,
            "current_streak": current_streak,
            "best_streak": best_streak,
            "last_active_date": sorted_dates[-1].isoformat() if sorted_dates else None
        }
