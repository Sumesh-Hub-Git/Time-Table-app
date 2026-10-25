"""Unit tests for Statistics and Export Services."""
import unittest
import os
import tempfile
import json
import csv
from datetime import date
from database.db import DatabaseManager
from services.task_service import TaskService
from services.stats_service import StatsService
from services.export_service import ExportService
from database.models import Task


class TestStatsAndExport(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_studyflow.db")
        self.db = DatabaseManager(self.db_path)
        self.task_service = TaskService(self.db)
        self.stats_service = StatsService(self.db)
        self.export_service = ExportService(self.db)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_stats_calculations(self):
        today_s = self.stats_service.get_today_stats()
        self.assertIn("total_tasks", today_s)
        self.assertIn("completed_tasks", today_s)
        self.assertIn("completion_percentage", today_s)

        productivity = self.stats_service.get_overall_productivity()
        self.assertIn("overall_percentage", productivity)
        self.assertIn("current_streak", productivity)
        self.assertIn("best_streak", productivity)
        self.assertIn("most_productive_day", productivity)

    def test_export_csv(self):
        csv_path = os.path.join(self.temp_dir, "export.csv")
        success = self.export_service.export_tasks_to_csv(csv_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(csv_path))

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertIn("Title", header)

    def test_export_json(self):
        json_path = os.path.join(self.temp_dir, "export.json")
        success = self.export_service.export_all_to_json(json_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(json_path))

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["application"], "StudyFlow")
            self.assertIn("tasks", data)
            self.assertIn("categories", data)


if __name__ == "__main__":
    unittest.main()
