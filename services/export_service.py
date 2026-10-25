"""
StudyFlow Data Backup and Export Service
Provides capabilities to:
- Export tasks to CSV format
- Export complete app data (tasks + categories + completions) to JSON format
- Merge task CSV exports or complete JSON exports into the local database
- Backup SQLite database to file
- Restore SQLite database from backup file
"""

import csv
import json
import shutil
import os
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
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

    def import_data(self, file_path: str) -> Dict[str, int]:
        """Merge a StudyFlow JSON backup or task CSV export into the database."""
        extension = os.path.splitext(file_path)[1].lower()
        if extension == ".json":
            categories, tasks, completions = self._read_json_import(file_path)
        elif extension == ".csv":
            categories, tasks, completions = [], self._read_csv_import(file_path), []
        else:
            raise ValueError("Choose a StudyFlow JSON backup or task CSV export.")

        imported_categories = 0
        imported_tasks = 0
        imported_completions = 0
        source_task_ids: Dict[int, int] = {}

        with self.db.transaction() as conn:
            cursor = conn.cursor()
            category_names: Dict[int, str] = {}
            for category in categories:
                name = category["name"].strip()
                cursor.execute(
                    "INSERT OR IGNORE INTO categories (name, color, icon) VALUES (?, ?, ?);",
                    (name, category.get("color") or "#6366F1", category.get("icon") or "bookmark"),
                )
                imported_categories += cursor.rowcount
                if category.get("category_id") is not None:
                    category_names[int(category["category_id"])] = name

            cursor.execute("SELECT category_id, name FROM categories;")
            local_categories = {row["name"]: row["category_id"] for row in cursor.fetchall()}
            category_id_by_name = dict(local_categories)

            for task in tasks:
                source_category_id = task.pop("_source_category_id", None)
                category_name = category_names.get(source_category_id, task.pop("_category_name", "General"))
                if category_name not in category_id_by_name:
                    cursor.execute(
                        "INSERT OR IGNORE INTO categories (name, color, icon) VALUES (?, ?, ?);",
                        (category_name, "#6366F1", "bookmark"),
                    )
                    imported_categories += cursor.rowcount
                    cursor.execute("SELECT category_id FROM categories WHERE name = ?;", (category_name,))
                    category_id_by_name[category_name] = cursor.fetchone()["category_id"]

                values = {
                    "title": task["title"].strip(),
                    "description": task.get("description") or "",
                    "category_id": category_id_by_name[category_name],
                    "priority": task.get("priority") or "Medium",
                    "scheduled_date": task["scheduled_date"],
                    "end_date": task.get("end_date") or "",
                    "custom_dates": task.get("custom_dates") or "",
                    "start_time": task.get("start_time") or "09:00",
                    "end_time": task.get("end_time") or "10:00",
                    "repeat_type": task.get("repeat_type") or "None",
                    "reminder_minutes": task.get("reminder_minutes", 15),
                    "created_at": task.get("created_at") or datetime.now().isoformat(),
                    "is_active": task.get("is_active", 1),
                }
                cursor.execute(
                    """
                    SELECT task_id FROM tasks
                    WHERE title = ? AND scheduled_date = ? AND start_time = ? AND end_time = ?
                      AND repeat_type = ? AND end_date = ? AND custom_dates = ?
                      AND category_id IS ?;
                    """,
                    (
                        values["title"], values["scheduled_date"], values["start_time"],
                        values["end_time"], values["repeat_type"], values["end_date"],
                        values["custom_dates"], values["category_id"],
                    ),
                )
                existing = cursor.fetchone()
                if existing:
                    local_task_id = existing["task_id"]
                else:
                    cursor.execute(
                        """
                        INSERT INTO tasks (
                            title, description, category_id, priority, scheduled_date,
                            end_date, custom_dates, start_time, end_time, repeat_type,
                            reminder_minutes, created_at, is_active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        tuple(values[key] for key in (
                            "title", "description", "category_id", "priority", "scheduled_date",
                            "end_date", "custom_dates", "start_time", "end_time", "repeat_type",
                            "reminder_minutes", "created_at", "is_active",
                        )),
                    )
                    local_task_id = cursor.lastrowid
                    imported_tasks += 1

                if task.get("task_id") is not None:
                    source_task_ids[int(task["task_id"])] = local_task_id

            for completion in completions:
                local_task_id = source_task_ids.get(int(completion["task_id"]))
                if local_task_id is None:
                    raise ValueError(
                        f"Completion refers to task ID {completion['task_id']}, which is missing from the import."
                    )
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO task_completions
                        (task_id, completion_date, completed_at, notes)
                    VALUES (?, ?, ?, ?);
                    """,
                    (
                        local_task_id,
                        completion["completion_date"],
                        completion.get("completed_at") or datetime.now().isoformat(),
                        completion.get("notes") or "",
                    ),
                )
                imported_completions += cursor.rowcount

        return {
            "categories": imported_categories,
            "tasks": imported_tasks,
            "completions": imported_completions,
        }

    @staticmethod
    def _read_json_import(file_path: str) -> Tuple[List[dict], List[dict], List[dict]]:
        try:
            with open(file_path, "r", encoding="utf-8-sig") as source:
                data = json.load(source)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON file: {exc.msg}") from exc
        if not isinstance(data, dict) or data.get("application") != "StudyFlow":
            raise ValueError("The JSON file is not a StudyFlow data export.")

        categories = data.get("categories", [])
        tasks = data.get("tasks", [])
        completions = data.get("task_completions", [])
        if not all(isinstance(items, list) for items in (categories, tasks, completions)):
            raise ValueError("The JSON backup has an invalid data structure.")
        for category in categories:
            if not isinstance(category, dict) or not str(category.get("name", "")).strip():
                raise ValueError("Every imported category must have a name.")
        for task in tasks:
            if not isinstance(task, dict):
                raise ValueError("The JSON backup contains an invalid task.")
            if not str(task.get("title", "")).strip() or not task.get("scheduled_date"):
                raise ValueError("Every imported task must have a title and scheduled date.")
        for completion in completions:
            if not isinstance(completion, dict) or completion.get("task_id") is None:
                raise ValueError("The JSON backup contains an invalid completion record.")
            if not completion.get("completion_date"):
                raise ValueError("Every completion record must have a completion date.")

        return (
            [dict(category) for category in categories],
            [
                {
                    **task,
                    "_source_category_id": task.get("category_id"),
                }
                for task in tasks
            ],
            [dict(completion) for completion in completions],
        )

    @staticmethod
    def _read_csv_import(file_path: str) -> List[dict]:
        required_headers = {"Title", "Start / Scheduled Date"}
        tasks: List[dict] = []
        with open(file_path, "r", newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames or not required_headers.issubset(reader.fieldnames):
                raise ValueError("The CSV must be a StudyFlow task export with Title and Start / Scheduled Date columns.")
            for row_number, row in enumerate(reader, start=2):
                title = (row.get("Title") or "").strip()
                scheduled_date = (row.get("Start / Scheduled Date") or "").strip()
                if not title or not scheduled_date:
                    raise ValueError(f"CSV row {row_number} needs a title and scheduled date.")
                try:
                    reminder_minutes = int(row.get("Reminder (min)") or 15)
                    task_id = int(row["Task ID"]) if row.get("Task ID") else None
                except ValueError as exc:
                    raise ValueError(f"CSV row {row_number} has an invalid task ID or reminder value.") from exc
                active_value = (row.get("Is Active") or "1").strip().lower()
                tasks.append({
                    "task_id": task_id,
                    "_category_name": (row.get("Category") or "General").strip() or "General",
                    "title": title,
                    "description": row.get("Description") or "",
                    "priority": row.get("Priority") or "Medium",
                    "scheduled_date": scheduled_date,
                    "end_date": row.get("End Date") or "",
                    "custom_dates": row.get("Custom Dates") or "",
                    "start_time": row.get("Start Time") or "09:00",
                    "end_time": row.get("End Time") or "10:00",
                    "repeat_type": row.get("Repeat Option") or "None",
                    "reminder_minutes": reminder_minutes,
                    "created_at": row.get("Created At") or "",
                    "is_active": 1 if active_value in {"1", "true", "yes"} else 0,
                })
        return tasks

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
