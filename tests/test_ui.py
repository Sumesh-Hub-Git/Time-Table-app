"""Headless UI and Integration Unit Tests."""
import unittest
import os
import tempfile
import shutil

# Run in offscreen mode for automated headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from database.db import DatabaseManager
from services.task_service import TaskService
from services.streak_service import StreakService
from services.stats_service import StatsService
from services.export_service import ExportService
from ui.main_window import MainWindow
from ui.views.dashboard_view import DashboardView
from ui.views.calendar_view import CalendarView
from ui.views.timetable_view import TimetableView
from ui.views.task_list_view import TaskListView
from ui.views.analytics_view import AnalyticsView
from ui.views.settings_view import SettingsView


class TestStudyFlowUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create single QApplication instance for tests
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_ui_studyflow.db")
        self.db = DatabaseManager(self.db_path)
        self.task_service = TaskService(self.db)
        self.streak_service = StreakService(self.db)
        self.stats_service = StatsService(self.db)
        self.export_service = ExportService(self.db)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_main_window_initialization(self):
        window = MainWindow(db_path=self.db_path)
        self.assertIsNotNone(window)
        self.assertEqual(window.stack.count(), 6)
        window.close()

    def test_dashboard_view_refresh(self):
        view = DashboardView(self.task_service, self.stats_service, self.streak_service, "TestUser")
        view.refresh_data()
        self.assertIn("TestUser", view.greeting_label.text())

    def test_calendar_view_navigation(self):
        cal = CalendarView(self.task_service)
        init_month = cal.current_month
        cal._next_month()
        expected = (init_month % 12) + 1
        self.assertEqual(cal.current_month, expected)
        cal._prev_month()
        self.assertEqual(cal.current_month, init_month)

    def test_timetable_view_modes(self):
        tt = TimetableView(self.task_service)
        tt._set_mode("weekly")
        self.assertEqual(tt.view_mode, "weekly")
        tt._set_mode("daily")
        self.assertEqual(tt.view_mode, "daily")

    def test_task_list_view_search(self):
        tl = TaskListView(self.task_service, self.streak_service)
        tl.search_input.setText("Discrete")
        tl.refresh_tasks()
        self.assertGreater(tl.tasks_layout.count(), 0)


if __name__ == "__main__":
    unittest.main()
