"""
StudyFlow Reminder & Notification Engine
Monitors upcoming scheduled tasks using a background QTimer and emits
signals to trigger in-app toast alerts when tasks are approaching.
"""

from datetime import datetime, date
from typing import Set, Optional
from PySide6.QtCore import QObject, QTimer, Signal
from database.models import TaskInstance
from database.db import DatabaseManager, get_db
from services.task_service import TaskService
from utils.date_helpers import today_date, parse_date, time_to_minutes


class ReminderService(QObject):
    """Monitors scheduled tasks and triggers reminder signals."""

    # Signal emits: (task_instance, minutes_until_start)
    reminder_triggered = Signal(object, int)

    def __init__(self, db: Optional[DatabaseManager] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.db = db or get_db()
        self.task_service = TaskService(self.db)
        self.notified_tasks_today: Set[int] = set()
        self._current_tracked_date: date = today_date()

        self.timer = QTimer(self)
        self.timer.setInterval(30000)  # Check every 30 seconds
        self.timer.timeout.connect(self.check_upcoming_reminders)

    def start(self):
        """Starts the reminder timer and performs initial check."""
        self.timer.start()
        self.check_upcoming_reminders()

    def stop(self):
        """Stops the reminder timer."""
        self.timer.stop()

    def check_upcoming_reminders(self):
        """Checks if any pending tasks for today are approaching their reminder window."""
        today = today_date()

        # Reset notified set on new day rollover
        if today != self._current_tracked_date:
            self.notified_tasks_today.clear()
            self._current_tracked_date = today

        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute

        # Get all tasks for today
        instances = self.task_service.get_tasks_for_date(today)

        for inst in instances:
            # Skip if already completed, reminders disabled, or already notified today
            if inst.is_completed or inst.reminder_minutes <= 0:
                continue
            if inst.task_id in self.notified_tasks_today:
                continue

            task_start_min = time_to_minutes(inst.start_time)
            mins_remaining = task_start_min - current_minutes

            # Trigger reminder if within the reminder window (e.g. 0 <= mins_remaining <= reminder_minutes)
            if 0 <= mins_remaining <= inst.reminder_minutes:
                self.notified_tasks_today.add(inst.task_id)
                self.reminder_triggered.emit(inst, mins_remaining)
