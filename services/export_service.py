"""
StudyFlow Data Backup and Export Service
Provides capabilities to:
- Export tasks to CSV format
- Export complete app data (tasks + categories + completions) to JSON format
- Backup SQLite database to file
- Restore SQLite database from backup file
"""

import csv
import json
import shutil
import os
from typing import Optional, Dict, Any
from database.db import DatabaseManager, get_db


class ExportService:
    """Handles data import, export, and backup operations."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()

    def export_tasks_to_csv(self, file_path: str) -> bool:
        """Exports all tasks with category names and priority to a CSV file."""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.task_id, t.title, t.description, c.name as category,
                       t.priority, t.scheduled_date, t.end_date, t.custom_dates,
                       t.start_time, t.end_time, t.repeat_type, t.reminder_minutes,
                       t.created_at, t.is_active
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.category_id
                ORDER BY t.task_id ASC;
            """)
            rows = cursor.fetchall()

        if not rows:
            return False

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Task ID", "Title", "Description", "Category", "Priority",
                "Start / Scheduled Date", "End Date", "Custom Dates",
                "Start Time", "End Time", "Repeat Option",
                "Reminder (min)", "Created At", "Is Active"
            ])
            for r in rows:
                writer.writerow([
                    r["task_id"], r["title"], r["description"], r["category"] or "General",
                    r["priority"], r["scheduled_date"], r["end_date"], r["custom_dates"],
                    r["start_time"], r["end_time"], r["repeat_type"],
                    r["reminder_minutes"], r["created_at"], r["is_active"]
                ])
        return True

    def export_all_to_json(self, file_path: str) -> bool:
        """Exports all categories, tasks, and completion history to a formatted JSON file."""
        with self.db.transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM categories;")
            categories = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM tasks;")
            tasks = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM task_completions;")
            completions = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM settings;")
            settings = {r["key"]: r["value"] for r in cursor.fetchall()}

        data: Dict[str, Any] = {
            "application": "StudyFlow",
            "version": "1.0",
            "categories": categories,
            "tasks": tasks,
            "task_completions": completions,
            "settings": settings
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True

    def backup_database(self, dest_path: str) -> bool:
        """Creates a snapshot copy of the SQLite database file."""
        if not os.path.exists(self.db.db_path):
            return False
        shutil.copy2(self.db.db_path, dest_path)
        return True

    def restore_database(self, source_path: str) -> bool:
        """Restores the database from a backup file."""
        if not os.path.exists(source_path):
            return False
        shutil.copy2(source_path, self.db.db_path)
        self.db.init_db()
        return True

    def reset_database(self) -> bool:
        """Clears all tasks and completions, resetting to default seed state."""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM task_completions;")
            cursor.execute("DELETE FROM tasks;")
            cursor.execute("DELETE FROM categories;")
            self.db._seed_default_categories(cursor)
            self.db._seed_sample_tasks(cursor)
        return True
