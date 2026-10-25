"""Unit tests for Statistics and Export Services."""
import unittest
import os
import tempfile
import json
import csv
import io
from datetime import date
from unittest.mock import patch
from urllib.error import HTTPError
from database.db import DatabaseManager
from services.task_service import TaskService
from services.stats_service import StatsService
from services.export_service import ExportService
from services.ai_telegram_service import (
    generate_study_message,
    list_available_models,
    send_telegram_message,
    _post_json,
)
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

    def test_json_import_merges_tasks_and_completions_idempotently(self):
        study_category_id = next(
            category.category_id
            for category in self.task_service.get_all_categories()
            if category.name == "Study"
        )
        task = Task(
            title="Import round-trip test",
            category_id=study_category_id,
            scheduled_date=date.today().isoformat(),
            start_time="21:00",
            end_time="21:30",
            repeat_type="None",
        )
        task_id = self.task_service.create_task(task)
        self.task_service.toggle_task_completion(task_id, date.today())

        export_path = os.path.join(self.temp_dir, "roundtrip.json")
        self.export_service.export_all_to_json(export_path)

        imported = self.export_service.import_data(export_path)
        self.assertEqual(imported, {"categories": 0, "tasks": 0, "completions": 0})

        second_db_path = os.path.join(self.temp_dir, "second_studyflow.db")
        second_db = DatabaseManager(second_db_path)
        second_export_service = ExportService(second_db)
        imported = second_export_service.import_data(export_path)
        self.assertEqual(imported["tasks"], 1)
        self.assertEqual(imported["completions"], 1)
        imported_again = second_export_service.import_data(export_path)
        self.assertEqual(imported_again, {"categories": 0, "tasks": 0, "completions": 0})

    def test_csv_import_adds_new_task(self):
        csv_path = os.path.join(self.temp_dir, "tasks.csv")
        self.export_service.export_tasks_to_csv(csv_path)

        with open(csv_path, "a", newline="", encoding="utf-8") as source:
            writer = csv.writer(source)
            writer.writerow([
                99999, "CSV import test", "Imported from CSV", "Study", "High",
                date.today().isoformat(), "", "", "21:00", "21:30", "None",
                15, "2026-01-01T00:00:00", 1,
            ])

        imported = self.export_service.import_data(csv_path)
        self.assertEqual(imported["tasks"], 1)
        matching_tasks = [
            task for task in self.task_service.get_all_tasks()
            if task.title == "CSV import test"
        ]
        self.assertEqual(len(matching_tasks), 1)

    def test_ai_message_generation_and_telegram_send(self):
        with patch(
            "services.ai_telegram_service._post_json",
            return_value={"choices": [{"message": {"content": "Ready for a focused study day!"}}]},
        ) as post_json:
            message = generate_study_message(
                "groq", "secret", "test-model", "", date.today(), [], "Avery"
            )
        self.assertEqual(message, "Ready for a focused study day!")
        self.assertEqual(post_json.call_args.args[0], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(post_json.call_args.args[2]["Authorization"], "Bearer secret")
        self.assertIn("Avery", post_json.call_args.args[1]["messages"][1]["content"])

        with patch(
            "services.ai_telegram_service._post_json",
            return_value={"ok": True},
        ) as post_json:
            send_telegram_message("bot-token", "chat-123", message)
        self.assertIn("bot-token", post_json.call_args.args[0])
        self.assertEqual(post_json.call_args.args[1]["chat_id"], "chat-123")

    def test_cloudflare_1010_error_has_actionable_guidance(self):
        response = HTTPError(
            "https://api.groq.com",
            403,
            "Forbidden",
            {},
            io.BytesIO(b"Cloudflare error 1010: Access denied"),
        )
        with patch("services.ai_telegram_service.urlopen", side_effect=response) as urlopen:
            with self.assertRaisesRegex(RuntimeError, "Ollama \\(Local\\) provider"):
                _post_json(
                    "https://api.groq.com/openai/v1/chat/completions",
                    {},
                    service_name="Groq",
                )
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), "StudyFlow/1.0")

    def test_list_models_for_groq_and_ollama(self):
        with patch(
            "services.ai_telegram_service._get_json",
            return_value={"data": [{"id": "model-z"}, {"id": "model-a"}]},
        ) as get_json:
            groq_models = list_available_models("groq", "test-key", "")
        self.assertEqual(groq_models, ["model-a", "model-z"])
        self.assertEqual(get_json.call_args.args[0], "https://api.groq.com/openai/v1/models")

        with patch(
            "services.ai_telegram_service._get_json",
            return_value={"models": [{"name": "qwen2.5"}, {"name": "llama3.2"}]},
        ) as get_json:
            ollama_models = list_available_models("ollama", "", "http://localhost:11434")
        self.assertEqual(ollama_models, ["llama3.2", "qwen2.5"])
        self.assertEqual(get_json.call_args.args[0], "http://localhost:11434/api/tags")


if __name__ == "__main__":
    unittest.main()
