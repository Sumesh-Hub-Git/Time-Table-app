"""Polling engine for automatic task reminders sent to Telegram."""

import ctypes
import logging
import os
import time
from ctypes import wintypes
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from database.db import DatabaseManager, get_db
from services.ai_telegram_service import generate_study_message, send_telegram_message
from services.task_service import TaskService
from services.telegram_automation import get_automation_credentials


REMINDER_LEAD_MINUTES = 10
RETRY_DELAY = timedelta(minutes=1)
POLL_INTERVAL_SECONDS = 15
SCHEDULER_MUTEX_NAME = "Local\\StudyFlowTelegramReminders"


def _read_settings(db: DatabaseManager) -> dict[str, str]:
    with db.transaction() as conn:
        rows = conn.execute("SELECT key, value FROM settings;").fetchall()
    return {row["key"]: row["value"] for row in rows}


def _claim_reminder(
    db: DatabaseManager,
    task_id: int,
    reminder_date: date,
    now: datetime,
) -> bool:
    """Atomically claim an occurrence, suppressing duplicates and rapid retries."""
    reminder_date_str = reminder_date.isoformat()
    with db.transaction() as conn:
        conn.execute("BEGIN IMMEDIATE;")
        row = conn.execute(
            """
            SELECT status, last_attempt_at FROM telegram_reminder_attempts
            WHERE task_id = ? AND reminder_date = ?;
            """,
            (task_id, reminder_date_str),
        ).fetchone()
        if row:
            if row["status"] == "sent":
                return False
            try:
                last_attempt = datetime.fromisoformat(row["last_attempt_at"])
            except ValueError:
                last_attempt = datetime.min
            if now - last_attempt < RETRY_DELAY:
                return False
            conn.execute(
                """
                UPDATE telegram_reminder_attempts
                SET status = 'sending', last_attempt_at = ?, sent_at = NULL
                WHERE task_id = ? AND reminder_date = ?;
                """,
                (now.isoformat(), task_id, reminder_date_str),
            )
        else:
            conn.execute(
                """
                INSERT INTO telegram_reminder_attempts
                    (task_id, reminder_date, status, last_attempt_at)
                VALUES (?, ?, 'sending', ?);
                """,
                (task_id, reminder_date_str, now.isoformat()),
            )
        return True


def _finish_attempt(
    db: DatabaseManager,
    task_id: int,
    reminder_date: date,
    *,
    sent: bool,
    now: datetime,
) -> None:
    with db.transaction() as conn:
        conn.execute(
            """
            UPDATE telegram_reminder_attempts
            SET status = ?, last_attempt_at = ?, sent_at = ?
            WHERE task_id = ? AND reminder_date = ?;
            """,
            (
                "sent" if sent else "failed",
                now.isoformat(),
                now.isoformat() if sent else None,
                task_id,
                reminder_date.isoformat(),
            ),
        )


def check_upcoming_tasks(
    db: Optional[DatabaseManager] = None,
    now: Optional[datetime] = None,
) -> int:
    """Send AI-generated Telegram reminders for tasks starting within 10 minutes."""
    database = db or get_db()
    current = now or datetime.now()
    settings = _read_settings(database)
    if settings.get("telegram_auto_enabled") != "1":
        return 0

    credentials = get_automation_credentials()
    bot_token = credentials["telegram_bot_token"]
    chat_id = credentials["telegram_chat_id"]
    provider = settings.get("telegram_auto_provider", "")
    api_key = credentials["groq_api_key"] if provider == "groq" else ""
    model = settings.get("telegram_auto_model", "")
    ollama_url = settings.get("telegram_auto_ollama_url", "")
    user_name = settings.get("user_name", "Student")

    if not bot_token or not chat_id:
        logging.error("Automatic Telegram reminders are enabled, but credentials are missing.")
        return 0
    if provider not in {"groq", "ollama"} or not model:
        logging.error("Automatic Telegram reminders have invalid AI provider settings.")
        return 0
    if provider == "groq" and not api_key:
        logging.error("Automatic Groq reminders are enabled, but the API key is missing.")
        return 0

    task_service = TaskService(database)
    instances = task_service.get_tasks_for_date(current.date())
    sent_count = 0

    for instance in instances:
        if instance.is_completed or instance.task_id is None:
            continue
        try:
            start_time = datetime.strptime(instance.start_time, "%H:%M").time()
        except ValueError:
            logging.error("Skipping task %s with invalid start time.", instance.task_id)
            continue
        starts_at = datetime.combine(current.date(), start_time)
        reminder_at = starts_at - timedelta(minutes=REMINDER_LEAD_MINUTES)
        if not reminder_at <= current < starts_at:
            continue
        if not _claim_reminder(database, instance.task_id, current.date(), current):
            continue

        try:
            message = generate_study_message(
                provider,
                api_key,
                model,
                ollama_url,
                current.date(),
                [instance],
                user_name,
            )
            if datetime.now() >= starts_at:
                raise RuntimeError("The AI response arrived after the task start time; reminder not sent.")
            send_telegram_message(bot_token, chat_id, message)
        except Exception:
            _finish_attempt(
                database, instance.task_id, current.date(), sent=False, now=datetime.now()
            )
            logging.exception("Could not send Telegram reminder for task %s.", instance.task_id)
        else:
            _finish_attempt(
                database, instance.task_id, current.date(), sent=True, now=datetime.now()
            )
            sent_count += 1

    return sent_count


def _acquire_single_instance_mutex():
    if os.name != "nt":
        return None
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, False, SCHEDULER_MUTEX_NAME)
    if not handle:
        raise OSError(ctypes.get_last_error(), "Could not create scheduler mutex.")
    if ctypes.get_last_error() == 183:
        kernel32.CloseHandle(handle)
        return None
    return kernel32, handle


def run_forever(db_path: Optional[str] = None):
    """Run the hidden logon process until automatic reminders are disabled."""
    if os.name != "nt":
        raise RuntimeError("The background Telegram scheduler currently requires Windows.")
    log_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StudyFlow"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_dir / "telegram_automation.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    mutex = _acquire_single_instance_mutex()
    if mutex is None:
        logging.info("Another StudyFlow Telegram scheduler is already running.")
        return

    kernel32, handle = mutex
    try:
        database = get_db(db_path) if db_path else get_db()
        while True:
            if _read_settings(database).get("telegram_auto_enabled") != "1":
                logging.info("Automatic Telegram reminders are disabled; stopping scheduler.")
                return
            try:
                check_upcoming_tasks(database)
            except Exception:
                logging.exception("Unexpected failure while checking scheduled reminders.")
            time.sleep(POLL_INTERVAL_SECONDS)
    finally:
        kernel32.CloseHandle(handle)
