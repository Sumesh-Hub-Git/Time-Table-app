"""
StudyFlow Statistics & Analytics Engine
Calculates productivity metrics, completion rates, category distributions,
day-of-week trends, and timeline data for visualizations.
"""

from datetime import date, timedelta
from typing import Dict, Any, List, Optional
import calendar
from database.db import DatabaseManager, get_db
from services.streak_service import StreakService
from services.task_service import TaskService
from utils.date_helpers import parse_date, today_date, today_str, get_past_n_days


class StatsService:
    """Service providing aggregated analytics and productivity metrics."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()
        self.streak_service = StreakService(self.db)
        self.task_service = TaskService(self.db)

    def get_today_stats(self, target_date: Optional[str | date] = None) -> Dict[str, Any]:
        """Calculates task summary statistics for a given day (defaults to today)."""
        d = parse_date(target_date) if target_date else today_date()
        instances = self.task_service.get_tasks_for_date(d)

        total = len(instances)
        completed = sum(1 for inst in instances if inst.is_completed)
        pending = total - completed
        percent = int(round((completed / total * 100))) if total > 0 else 0

        return {
            "date": d.isoformat(),
            "total_tasks": total,
            "completed_tasks": completed,
            "pending_tasks": pending,
            "completion_percentage": percent
        }

    def get_overall_productivity(self) -> Dict[str, Any]:
        """
        Calculates all-time aggregate productivity statistics, streaks,
        most productive day of the week, and top subject/category.
        """
        global_streak = self.streak_service.get_global_streak()

        with self.db.transaction() as conn:
            cursor = conn.cursor()

            # Total completions all time
            cursor.execute("SELECT COUNT(*) as total_completions FROM task_completions;")
            total_completions = cursor.fetchone()["total_completions"]

            # Day of week completions breakdown (0=Monday ... 6=Sunday in Python)
            cursor.execute("SELECT completion_date FROM task_completions;")
            comp_dates = cursor.fetchall()

            day_counts = {i: 0 for i in range(7)}
            for r in comp_dates:
                try:
                    dt = parse_date(r["completion_date"])
                    day_counts[dt.weekday()] += 1
                except Exception:
                    pass

            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            most_productive_idx = max(day_counts, key=day_counts.get) if total_completions > 0 else 0
            most_productive_day = day_names[most_productive_idx] if total_completions > 0 else "N/A"

            # Top category / subject
            cursor.execute("""
                SELECT c.name as cat_name, c.color as cat_color, COUNT(tc.completion_id) as count
                FROM task_completions tc
                JOIN tasks t ON tc.task_id = t.task_id
                LEFT JOIN categories c ON t.category_id = c.category_id
                GROUP BY c.name
                ORDER BY count DESC
                LIMIT 1;
            """)
            top_cat_row = cursor.fetchone()
            top_category = top_cat_row["cat_name"] if top_cat_row and top_cat_row["cat_name"] else "General"

            # Top task / subject
            cursor.execute("""
                SELECT t.title, COUNT(tc.completion_id) as count
                FROM task_completions tc
                JOIN tasks t ON tc.task_id = t.task_id
                GROUP BY t.task_id
                ORDER BY count DESC
                LIMIT 1;
            """)
            top_task_row = cursor.fetchone()
            top_subject = top_task_row["title"] if top_task_row else "N/A"

        # Calculate average 14-day completion percentage
        past_14 = get_past_n_days(14)
        total_14 = 0
        done_14 = 0
        for d in past_14:
            s = self.get_today_stats(d)
            total_14 += s["total_tasks"]
            done_14 += s["completed_tasks"]

        overall_percentage = int(round((done_14 / total_14 * 100))) if total_14 > 0 else (100 if total_completions > 0 else 0)

        # Get today's stats for current pending
        today_s = self.get_today_stats()

        return {
            "overall_percentage": overall_percentage,
            "total_completions": total_completions,
            "tasks_completed_today": today_s["completed_tasks"],
            "tasks_pending_today": today_s["pending_tasks"],
            "current_streak": global_streak["current_streak"],
            "best_streak": global_streak["best_streak"],
            "total_completed_days": global_streak["total_completed_days"],
            "most_productive_day": most_productive_day,
            "top_category": top_category,
            "top_subject": top_subject
        }

    def get_completion_trend(self, days: int = 14) -> List[Dict[str, Any]]:
        """Returns time-series daily completion data for chart visualization."""
        date_list = get_past_n_days(days)
        trend = []

        for d in date_list:
            stats = self.get_today_stats(d)
            trend.append({
                "date": d.isoformat(),
                "day_name": d.strftime("%a"),
                "short_date": d.strftime("%d %b"),
                "day_num": d.strftime("%d"),
                "total": stats["total_tasks"],
                "completed": stats["completed_tasks"],
                "pending": stats["pending_tasks"],
                "percentage": stats["completion_percentage"]
            })

        return trend

    def get_category_distribution(self) -> List[Dict[str, Any]]:
        """Returns completion count and percentages grouped by category for donut/pie charts."""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(c.name, 'General') as name,
                       COALESCE(c.color, '#6366F1') as color,
                       COUNT(tc.completion_id) as count
                FROM task_completions tc
                JOIN tasks t ON tc.task_id = t.task_id
                LEFT JOIN categories c ON t.category_id = c.category_id
                GROUP BY c.category_id
                ORDER BY count DESC;
            """)
            rows = cursor.fetchall()

        total_completions = sum(r["count"] for r in rows)
        if total_completions == 0:
            return []

        distribution = []
        for r in rows:
            cnt = r["count"]
            pct = round((cnt / total_completions * 100), 1)
            distribution.append({
                "name": r["name"],
                "color": r["color"],
                "count": cnt,
                "percentage": pct
            })

        return distribution

    def get_day_of_week_analysis(self) -> List[Dict[str, Any]]:
        """Returns completion distribution across all 7 days of the week."""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT completion_date FROM task_completions;")
            rows = cursor.fetchall()

        day_counts = [0] * 7
        for r in rows:
            try:
                dt = parse_date(r["completion_date"])
                day_counts[dt.weekday()] += 1
            except Exception:
                pass

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        full_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        max_count = max(day_counts) if day_counts else 1
        max_count = max(max_count, 1)

        result = []
        for i in range(7):
            result.append({
                "day_idx": i,
                "short_name": day_names[i],
                "full_name": full_names[i],
                "count": day_counts[i],
                "intensity": round(day_counts[i] / max_count, 2)
            })

        return result
