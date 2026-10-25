"""Tests for scheduled Telegram reminder delivery and startup configuration."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from database.db import DatabaseManager
from database.models import Task
from services.task_service import TaskService
from services.telegram_automation import enable_automatic_reminders
from services.telegram_scheduler import check_upcoming_tasks


class TestTelegramScheduler(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "scheduler.db")
        self.db = DatabaseManager(self.db_path)
        self.task_service = TaskService(self.db)
        self.now = datetime.now().replace(second=0, microsecond=0)
        self.task_id = self.task_service.create_task(Task(
            title="Scheduled reminder test",
            scheduled_date=self.now.date().isoformat(),
            start_time=(self.now + timedelta(minutes=6)).strftime("%H:%M"),
            end_time=(self.now + timedelta(minutes=36)).strftime("%H:%M"),
            repeat_type="None",
            reminder_minutes=0,
        ))
        with self.db.transaction() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?);",
                [
                    ("telegram_auto_enabled", "1"),
                    ("telegram_auto_provider", "ollama"),
                    ("telegram_auto_model", "llama3.2"),
                    ("telegram_auto_ollama_url", "http://localhost:11434"),
                    ("user_name", "Test User"),
                ],
            )

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("services.telegram_scheduler.get_automation_credentials")
    @patch("services.telegram_scheduler.send_telegram_message")
    @patch("services.telegram_scheduler.generate_study_message", return_value="Upcoming task!")
    def test_sends_once_inside_ten_minute_window(
        self, generate_message, send_message, get_credentials
    ):
        get_credentials.return_value = {
            "telegram_bot_token": "bot-token",
            "telegram_chat_id": "chat-id",
            "groq_api_key": "",
        }

        sent = check_upcoming_tasks(self.db, self.now)
        self.assertEqual(sent, 1)
        self.assertEqual(check_upcoming_tasks(self.db, self.now), 0)
        generate_message.assert_called_once()
        self.assertEqual(generate_message.call_args.args[2], "llama3.2")
        self.assertEqual(generate_message.call_args.args[5][0].task_id, self.task_id)
        self.assertEqual(generate_message.call_args.args[6], "Test User")
        send_message.assert_called_once_with("bot-token", "chat-id", "Upcoming task!")

        with self.db.transaction() as conn:
            attempt = conn.execute(
                "SELECT status FROM telegram_reminder_attempts WHERE task_id = ?;",
                (self.task_id,),
            ).fetchone()
        self.assertEqual(attempt["status"], "sent")

    @patch("services.telegram_scheduler.get_automation_credentials")
    @patch("services.telegram_scheduler.send_telegram_message")
    @patch("services.telegram_scheduler.generate_study_message")
    def test_does_not_send_outside_reminder_window(
        self, generate_message, send_message, get_credentials
    ):
        get_credentials.return_value = {
            "telegram_bot_token": "bot-token",
            "telegram_chat_id": "chat-id",
            "groq_api_key": "",
        }
        too_early = self.now - timedelta(minutes=5)

        self.assertEqual(check_upcoming_tasks(self.db, too_early), 0)
        generate_message.assert_not_called()
        send_message.assert_not_called()

    @patch("services.telegram_scheduler.get_automation_credentials")
    @patch("services.telegram_scheduler.send_telegram_message", side_effect=RuntimeError("network unavailable"))
    @patch("services.telegram_scheduler.generate_study_message", return_value="Upcoming task!")
    def test_failed_delivery_is_recorded_and_retried_after_delay(
        self, generate_message, send_message, get_credentials
    ):
        get_credentials.return_value = {
            "telegram_bot_token": "bot-token",
            "telegram_chat_id": "chat-id",
            "groq_api_key": "",
        }
        with self.assertLogs(level="ERROR"):
            self.assertEqual(check_upcoming_tasks(self.db, self.now), 0)

        self.assertEqual(check_upcoming_tasks(self.db, self.now + timedelta(seconds=30)), 0)
        self.assertEqual(send_message.call_count, 1)
        with self.assertLogs(level="ERROR"):
            self.assertEqual(check_upcoming_tasks(self.db, self.now + timedelta(minutes=2)), 0)
        self.assertEqual(send_message.call_count, 2)

        with self.db.transaction() as conn:
            attempt = conn.execute(
                "SELECT status FROM telegram_reminder_attempts WHERE task_id = ?;",
                (self.task_id,),
            ).fetchone()
        self.assertEqual(attempt["status"], "failed")
        self.assertEqual(generate_message.call_count, 2)

    @patch("services.telegram_automation.register_background_scheduler")
    @patch("services.telegram_automation.save_automation_credentials")
    @patch("services.telegram_automation._require_windows_scheduler")
    def test_enable_saves_configuration_and_registers_scheduler(
        self, require_windows, save_credentials, register_scheduler
    ):
        enable_automatic_reminders(
            self.db,
            "groq",
            "llama-3.3-70b-versatile",
            "http://localhost:11434",
            "bot-token",
            "chat-id",
            "groq-key",
        )
        save_credentials.assert_called_once_with("bot-token", "chat-id", "groq-key")
        register_scheduler.assert_called_once_with(self.db.db_path)
        with self.db.transaction() as conn:
            settings = {
                row["key"]: row["value"]
                for row in conn.execute("SELECT key, value FROM settings")
            }
        self.assertEqual(settings["telegram_auto_enabled"], "1")
        self.assertEqual(settings["telegram_auto_provider"], "groq")


if __name__ == "__main__":
    unittest.main()
