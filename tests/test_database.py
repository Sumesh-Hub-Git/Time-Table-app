"""Unit tests for Database and Models."""
import unittest
import os
import tempfile
from database.db import DatabaseManager
from database.models import Task, Category, TaskCompletion


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_studyflow.db")
        self.db = DatabaseManager(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tables_created(self):
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row["name"] for row in cursor.fetchall()]
            self.assertIn("categories", tables)
            self.assertIn("tasks", tables)
            self.assertIn("task_completions", tables)
            self.assertIn("settings", tables)

    def test_default_categories_seeded(self):
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM categories;")
            count = cursor.fetchone()["count"]
            self.assertGreater(count, 0)

    def test_seed_sample_tasks_uses_existing_task_ids(self):
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM task_completions;")
            cursor.execute("DELETE FROM tasks;")
            cursor.execute("INSERT INTO tasks (task_id, title, description, category_id, priority, scheduled_date, start_time, end_time, repeat_type, reminder_minutes, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                           (42, "Custom task", "Example", 1, "High", "2026-08-31", "09:00", "10:00", "None", 15, "2026-08-31T00:00:00", 1))
            cursor.execute("INSERT INTO tasks (task_id, title, description, category_id, priority, scheduled_date, start_time, end_time, repeat_type, reminder_minutes, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                           (73, "Second task", "Example 2", 1, "Medium", "2026-08-31", "11:00", "12:00", "None", 15, "2026-08-31T00:00:00", 1))

            self.db._seed_sample_tasks(cursor)

            count = cursor.execute("SELECT COUNT(*) as count FROM task_completions;").fetchone()["count"]
            self.assertGreater(count, 0)
            bad_fk = cursor.execute("SELECT COUNT(*) as count FROM task_completions tc LEFT JOIN tasks t ON t.task_id = tc.task_id WHERE t.task_id IS NULL;").fetchone()["count"]
            self.assertEqual(bad_fk, 0)


if __name__ == "__main__":
    unittest.main()
