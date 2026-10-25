"""Unit tests for Task Service, Date Range, and Custom Dates Scheduling."""
import unittest
import os
import tempfile
import json
from datetime import date, timedelta
from database.db import DatabaseManager
from services.task_service import TaskService
from database.models import Task


class TestTaskService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_studyflow.db")
        self.db = DatabaseManager(self.db_path)
        self.task_service = TaskService(self.db)

        with self.db.transaction() as conn:
            conn.execute("DELETE FROM task_completions;")
            conn.execute("DELETE FROM tasks;")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_and_get_task(self):
        task = Task(
            title="Mathematics",
            description="Integration by parts",
            priority="High",
            scheduled_date="2026-08-31",
            start_time="09:00",
            end_time="10:30",
            repeat_type="None"
        )
        task_id = self.task_service.create_task(task)
        self.assertIsNotNone(task_id)

        retrieved = self.task_service.get_task_by_id(task_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, "Mathematics")
        self.assertEqual(retrieved.priority, "High")

    def test_daily_recurring_expansion(self):
        today = date.today()
        task = Task(
            title="Daily Revision",
            scheduled_date=(today - timedelta(days=5)).isoformat(),
            repeat_type="Daily"
        )
        task_id = self.task_service.create_task(task)

        instances = self.task_service.get_tasks_for_date(today)
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].task_id, task_id)
        self.assertFalse(instances[0].is_completed)

        # Toggle completion
        completed_state = self.task_service.toggle_task_completion(task_id, today)
        self.assertTrue(completed_state)

        updated_instances = self.task_service.get_tasks_for_date(today)
        self.assertTrue(updated_instances[0].is_completed)

    def test_weekday_recurring_logic(self):
        task = Task(
            title="Weekday Class",
            scheduled_date="2026-08-01",
            repeat_type="Weekdays"
        )
        # Check Monday (2026-08-03) -> weekday 0 -> should be True
        mon = date(2026, 8, 3)
        self.assertTrue(self.task_service.is_task_scheduled_on_date(task, mon))

        # Check Saturday (2026-08-08) -> weekday 5 -> should be False
        sat = date(2026, 8, 8)
        self.assertFalse(self.task_service.is_task_scheduled_on_date(task, sat))

    def test_date_range_scheduling(self):
        task = Task(
            title="Workshop Project",
            scheduled_date="2026-09-01",
            end_date="2026-09-05",
            repeat_type="Date Range"
        )
        task_id = self.task_service.create_task(task)

        # Before start date -> False
        self.assertFalse(self.task_service.is_task_scheduled_on_date(task, date(2026, 8, 31)))
        # Inside range -> True
        self.assertTrue(self.task_service.is_task_scheduled_on_date(task, date(2026, 9, 1)))
        self.assertTrue(self.task_service.is_task_scheduled_on_date(task, date(2026, 9, 3)))
        self.assertTrue(self.task_service.is_task_scheduled_on_date(task, date(2026, 9, 5)))
        # After end date -> False
        self.assertFalse(self.task_service.is_task_scheduled_on_date(task, date(2026, 9, 6)))

    def test_custom_dates_scheduling(self):
        task = Task(
            title="Specific Exam Days",
            repeat_type="Custom Dates"
        )
        task.set_custom_dates_list(["2026-09-02", "2026-09-07", "2026-09-15"])
        task_id = self.task_service.create_task(task)

        retrieved = self.task_service.get_task_by_id(task_id)
        self.assertEqual(retrieved.get_custom_dates_list(), ["2026-09-02", "2026-09-07", "2026-09-15"])

        # Should match exact dates
        self.assertTrue(self.task_service.is_task_scheduled_on_date(retrieved, date(2026, 9, 2)))
        self.assertTrue(self.task_service.is_task_scheduled_on_date(retrieved, date(2026, 9, 7)))
        self.assertTrue(self.task_service.is_task_scheduled_on_date(retrieved, date(2026, 9, 15)))

        # Should NOT match other dates
        self.assertFalse(self.task_service.is_task_scheduled_on_date(retrieved, date(2026, 9, 1)))
        self.assertFalse(self.task_service.is_task_scheduled_on_date(retrieved, date(2026, 9, 3)))
        self.assertFalse(self.task_service.is_task_scheduled_on_date(retrieved, date(2026, 9, 8)))

    def test_recurring_with_end_date_limit(self):
        task = Task(
            title="Finite Daily Task",
            scheduled_date="2026-09-01",
            end_date="2026-09-10",
            repeat_type="Daily"
        )
        self.assertTrue(self.task_service.is_task_scheduled_on_date(task, date(2026, 9, 5)))
        self.assertTrue(self.task_service.is_task_scheduled_on_date(task, date(2026, 9, 10)))
        self.assertFalse(self.task_service.is_task_scheduled_on_date(task, date(2026, 9, 11)))

    def test_search_tasks_returns_all_tasks_when_no_date_filter_is_given(self):
        task_a = Task(
            title="Alpha Task",
            scheduled_date="2026-09-01",
            repeat_type="None"
        )
        task_b = Task(
            title="Beta Task",
            scheduled_date="2026-09-10",
            repeat_type="None"
        )

        self.task_service.create_task(task_a)
        self.task_service.create_task(task_b)

        all_instances = self.task_service.search_tasks(query="", status_filter="All")
        self.assertEqual(len(all_instances), 2)
        titles = {inst.title for inst in all_instances}
        self.assertIn("Alpha Task", titles)
        self.assertIn("Beta Task", titles)


if __name__ == "__main__":
    unittest.main()
