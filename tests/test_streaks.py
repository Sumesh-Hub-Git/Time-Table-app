"""Unit tests for Streak Calculation Service."""
import unittest
import os
import tempfile
from datetime import date, timedelta
from database.db import DatabaseManager
from services.streak_service import StreakService
from services.task_service import TaskService
from database.models import Task


class TestStreakService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_studyflow.db")
        self.db = DatabaseManager(self.db_path)
        self.streak_service = StreakService(self.db)
        self.task_service = TaskService(self.db)

        # Clear sample data to start clean
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM task_completions;")
            conn.execute("DELETE FROM tasks;")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_streak(self):
        streak_info = self.streak_service.calculate_task_streak(999)
        self.assertEqual(streak_info.total_completed_days, 0)
        self.assertEqual(streak_info.current_streak, 0)
        self.assertEqual(streak_info.best_streak, 0)

    def test_consecutive_streak(self):
        task = Task(title="Test Task", scheduled_date="2026-08-01", repeat_type="Daily")
        task_id = self.task_service.create_task(task)

        today = date.today()
        # Mark completed for today and past 4 days (5 days total)
        for i in range(5):
            d = today - timedelta(days=i)
            self.task_service.toggle_task_completion(task_id, d)

        streak_info = self.streak_service.calculate_task_streak(task_id)
        self.assertEqual(streak_info.total_completed_days, 5)
        self.assertEqual(streak_info.current_streak, 5)
        self.assertEqual(streak_info.best_streak, 5)

    def test_broken_streak_calculation(self):
        task = Task(title="Test Task 2", scheduled_date="2026-08-01", repeat_type="Daily")
        task_id = self.task_service.create_task(task)

        today = date.today()
        # Best streak: 4 days in the past (days 6, 5, 4, 3)
        # Gap on day 2
        # Current streak: 2 days (yesterday and today)
        dates_to_complete = [
            today - timedelta(days=6),
            today - timedelta(days=5),
            today - timedelta(days=4),
            today - timedelta(days=3),
            # Missed day 2
            today - timedelta(days=1),
            today,
        ]
        for d in dates_to_complete:
            self.task_service.toggle_task_completion(task_id, d)

        streak_info = self.streak_service.calculate_task_streak(task_id)
        self.assertEqual(streak_info.total_completed_days, 6)
        self.assertEqual(streak_info.current_streak, 2)
        self.assertEqual(streak_info.best_streak, 4)


if __name__ == "__main__":
    unittest.main()
