"""
StudyFlow Task Service
Core business logic for task management, recurring schedule resolution,
Date Range & Custom Dates execution, completion state toggling, and queries.
"""

from datetime import datetime, date
import sqlite3
from typing import List, Optional, Dict, Any, Tuple
from database.models import Task, TaskCompletion, TaskInstance, Category
from database.db import DatabaseManager, get_db
from services.streak_service import StreakService
from utils.date_helpers import parse_date, today_date, today_str


class TaskService:
    """Service for managing tasks, categories, and schedules."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()
        self.streak_service = StreakService(self.db)

    # ---------------------------------------------------------
    # Task CRUD Operations
    # ---------------------------------------------------------

    def create_task(self, task: Task) -> int:
        """Creates a new task and returns the generated task_id."""
        if not task.created_at:
            task.created_at = datetime.now().isoformat()
        if not task.scheduled_date:
            task.scheduled_date = today_str()

        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (
                    title, description, category_id, priority, scheduled_date,
                    end_date, custom_dates, start_time, end_time, repeat_type,
                    reminder_minutes, created_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                task.title.strip(),
                task.description.strip(),
                task.category_id,
                task.priority,
                task.scheduled_date,
                task.end_date or "",
                task.custom_dates or "",
                task.start_time,
                task.end_time,
                task.repeat_type,
                task.reminder_minutes,
                task.created_at,
                1 if task.is_active else 0
            ))
            task_id = cursor.lastrowid
            task.task_id = task_id
            return task_id

    def update_task(self, task: Task) -> bool:
        """Updates an existing task."""
        if not task.task_id:
            return False

        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks SET
                    title = ?,
                    description = ?,
                    category_id = ?,
                    priority = ?,
                    scheduled_date = ?,
                    end_date = ?,
                    custom_dates = ?,
                    start_time = ?,
                    end_time = ?,
                    repeat_type = ?,
                    reminder_minutes = ?,
                    is_active = ?
                WHERE task_id = ?;
            """, (
                task.title.strip(),
                task.description.strip(),
                task.category_id,
                task.priority,
                task.scheduled_date,
                task.end_date or "",
                task.custom_dates or "",
                task.start_time,
                task.end_time,
                task.repeat_type,
                task.reminder_minutes,
                1 if task.is_active else 0,
                task.task_id
            ))
            return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        """Deletes a task and its completion records (via CASCADE)."""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE task_id = ?;", (task_id,))
            return cursor.rowcount > 0

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Retrieves a single task with populated category info."""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.*, c.name as category_name, c.color as category_color
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.category_id
                WHERE t.task_id = ?;
            """, (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_task(row)

    def get_all_tasks(self, include_inactive: bool = False) -> List[Task]:
        """Returns all registered tasks in the system."""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            query = """
                SELECT t.*, c.name as category_name, c.color as category_color
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.category_id
            """
            if not include_inactive:
                query += " WHERE t.is_active = 1"
            query += " ORDER BY t.start_time ASC, t.title ASC;"

            cursor.execute(query)
            rows = cursor.fetchall()
            return [self._row_to_task(row) for row in rows]

    # ---------------------------------------------------------
    # Schedule Resolution & Date Queries
    # ---------------------------------------------------------

    def is_task_scheduled_on_date(self, task: Task, target_d: date) -> bool:
        """
        Determines whether a single, date-range, recurring, or custom-dates task
        applies to target_d.
        """
        if not task.is_active:
            return False

        repeat = (task.repeat_type or "None").strip()

        # 1. Custom / Specific Dates Mode
        if repeat == "Custom Dates":
            custom_list = task.get_custom_dates_list()
            return target_d.isoformat() in custom_list

        # 2. Date Range or Standard Recurring
        try:
            base_date = parse_date(task.scheduled_date)
        except Exception:
            return False

        # Task cannot appear before its initial scheduled start date
        if target_d < base_date:
            return False

        # If an end_date is specified, task cannot appear after end_date
        if task.end_date:
            try:
                end_d = parse_date(task.end_date)
                if target_d > end_d:
                    return False
            except Exception:
                pass

        if repeat in ["None", "Single Date"]:
            return target_d == base_date
        elif repeat in ["Date Range", "Daily"]:
            return True
        elif repeat == "Weekdays":
            # Monday=0 ... Friday=4, Saturday=5, Sunday=6
            return target_d.weekday() < 5
        elif repeat == "Weekly":
            # Same day of the week as base date
            return target_d.weekday() == base_date.weekday()

        return False

    def get_tasks_for_date(self, target_date: str | date) -> List[TaskInstance]:
        """
        Returns all task instances scheduled for target_date along with
        their completion status on that date and streak counters.
        """
        target_d = parse_date(target_date)
        target_str = target_d.isoformat()

        all_tasks = self.get_all_tasks(include_inactive=False)
        scheduled_tasks = [t for t in all_tasks if self.is_task_scheduled_on_date(t, target_d)]

        # Fetch completion records for this date
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT task_id, completed_at, notes
                FROM task_completions
                WHERE completion_date = ?;
            """, (target_str,))
            completions = {row["task_id"]: row for row in cursor.fetchall()}

        instances: List[TaskInstance] = []
        for task in scheduled_tasks:
            is_done = task.task_id in completions
            completed_at = completions[task.task_id]["completed_at"] if is_done else None
            streak_info = self.streak_service.calculate_task_streak(task.task_id)

            instances.append(TaskInstance(
                task=task,
                target_date=target_str,
                is_completed=is_done,
                completed_at=completed_at,
                streak_info=streak_info
            ))

        # Sort by start_time
        instances.sort(key=lambda x: (x.start_time, x.title))
        return instances

    def toggle_task_completion(self, task_id: int, target_date: str | date, notes: str = "") -> bool:
        """
        Toggles completion of a task on target_date.
        Returns True if task is now completed, False if it was set back to pending.
        """
        target_str = parse_date(target_date).isoformat()
        now_str = datetime.now().isoformat()

        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT completion_id
                FROM task_completions
                WHERE task_id = ? AND completion_date = ?;
            """, (task_id, target_str))
            existing = cursor.fetchone()

            if existing:
                # Mark as Pending (Remove completion)
                cursor.execute("""
                    DELETE FROM task_completions
                    WHERE task_id = ? AND completion_date = ?;
                """, (task_id, target_str))
                return False
            else:
                # Mark as Done (Insert completion)
                cursor.execute("""
                    INSERT INTO task_completions (task_id, completion_date, completed_at, notes)
                    VALUES (?, ?, ?, ?);
                """, (task_id, target_str, now_str, notes))
                return True

    def get_month_task_indicators(self, year: int, month: int) -> Dict[str, Dict[str, Any]]:
        """
        Generates day-by-day task summary indicators for calendar widget.
        Returns { 'YYYY-MM-DD': { 'total': int, 'completed': int, 'status': 'completed'|'partial'|'pending'|'none' } }
        """
        import calendar
        _, num_days = calendar.monthrange(year, month)
        all_tasks = self.get_all_tasks(include_inactive=False)

        month_start_str = f"{year:04d}-{month:02d}-01"
        month_end_str = f"{year:04d}-{month:02d}-{num_days:02d}"

        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT task_id, completion_date
                FROM task_completions
                WHERE completion_date >= ? AND completion_date <= ?;
            """, (month_start_str, month_end_str))
            rows = cursor.fetchall()
            completions_by_date: Dict[str, set] = {}
            for r in rows:
                c_date = r["completion_date"]
                if c_date not in completions_by_date:
                    completions_by_date[c_date] = set()
                completions_by_date[c_date].add(r["task_id"])

        result: Dict[str, Dict[str, Any]] = {}
        for day in range(1, num_days + 1):
            d_obj = date(year, month, day)
            d_str = d_obj.isoformat()

            scheduled = [t for t in all_tasks if self.is_task_scheduled_on_date(t, d_obj)]
            total = len(scheduled)
            done_set = completions_by_date.get(d_str, set())
            completed_count = sum(1 for t in scheduled if t.task_id in done_set)

            if total == 0:
                status = "none"
            elif completed_count == total:
                status = "completed"
            elif completed_count > 0:
                status = "partial"
            else:
                status = "pending"

            result[d_str] = {
                "total": total,
                "completed": completed_count,
                "status": status
            }

        return result

    # ---------------------------------------------------------
    # Search & Filter
    # ---------------------------------------------------------

    def search_tasks(
        self,
        query: str = "",
        category_id: Optional[int] = None,
        priority: Optional[str] = None,
        target_date: Optional[str | date] = None,
        status_filter: str = "All"
    ) -> List[TaskInstance]:
        """
        Flexible search and multi-filtering across task title, description, category, and priority.
        If target_date is not provided, returns all active tasks in the app instead of only today's list.
        """
        if target_date is not None:
            d = parse_date(target_date)
            instances = self.get_tasks_for_date(d)
        else:
            all_tasks = self.get_all_tasks(include_inactive=False)
            today_instances = {inst.task_id: inst for inst in self.get_tasks_for_date(today_date())}
            instances = []
            for task in all_tasks:
                today_match = today_instances.get(task.task_id)
                streak_info = self.streak_service.calculate_task_streak(task.task_id)
                instances.append(TaskInstance(
                    task=task,
                    target_date=task.scheduled_date,
                    is_completed=bool(today_match and today_match.is_completed),
                    completed_at=(today_match.completed_at if today_match else None),
                    streak_info=streak_info,
                ))

        filtered = []
        q_lower = query.strip().lower()

        for inst in instances:
            # Query match on title, description, or category
            if q_lower:
                match_title = q_lower in inst.title.lower()
                match_desc = q_lower in inst.description.lower()
                match_cat = q_lower in inst.category_name.lower()
                if not (match_title or match_desc or match_cat):
                    continue

            # Category filter
            if category_id is not None and inst.task.category_id != category_id:
                continue

            # Priority filter
            if priority and priority != "All" and inst.priority.lower() != priority.lower():
                continue

            # Status filter
            if status_filter == "Completed" and not inst.is_completed:
                continue
            if status_filter == "Pending" and inst.is_completed:
                continue

            filtered.append(inst)

        return filtered

    # ---------------------------------------------------------
    # Categories Operations
    # ---------------------------------------------------------

    def get_all_categories(self) -> List[Category]:
        """Returns all categories ordered by name."""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories ORDER BY name ASC;")
            rows = cursor.fetchall()
            return [Category(
                category_id=r["category_id"],
                name=r["name"],
                color=r["color"],
                icon=r["icon"]
            ) for r in rows]

    def create_category(self, name: str, color: str = "#6366F1", icon: str = "bookmark") -> int:
        """Creates a new category."""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO categories (name, color, icon)
                VALUES (?, ?, ?);
            """, (name.strip(), color.strip(), icon.strip()))
            return cursor.lastrowid

    def update_category(self, category: Category) -> bool:
        """Updates category name, color, and icon."""
        if not category.category_id:
            return False
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE categories SET name = ?, color = ?, icon = ?
                WHERE category_id = ?;
            """, (category.name.strip(), category.color.strip(), category.icon.strip(), category.category_id))
            return cursor.rowcount > 0

    def delete_category(self, category_id: int) -> bool:
        """Deletes a category and detaches tasks."""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM categories WHERE category_id = ?;", (category_id,))
            return cursor.rowcount > 0

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        keys = row.keys()
        return Task(
            task_id=row["task_id"],
            title=row["title"],
            description=row["description"] or "",
            category_id=row["category_id"],
            category_name=row["category_name"] if "category_name" in keys and row["category_name"] else "General",
            category_color=row["category_color"] if "category_color" in keys and row["category_color"] else "#6366F1",
            priority=row["priority"] or "Medium",
            scheduled_date=row["scheduled_date"],
            end_date=row["end_date"] if "end_date" in keys and row["end_date"] else "",
            custom_dates=row["custom_dates"] if "custom_dates" in keys and row["custom_dates"] else "",
            start_time=row["start_time"] or "09:00",
            end_time=row["end_time"] or "10:00",
            repeat_type=row["repeat_type"] or "None",
            reminder_minutes=row["reminder_minutes"] if row["reminder_minutes"] is not None else 15,
            created_at=row["created_at"] or "",
            is_active=bool(row["is_active"])
        )
