"""
StudyFlow Master Window (FR-15)
Main application window featuring responsive sidebar navigation, top header bar
with live clock, stacked page views, floating notification toasts, and theme switching.
"""

from typing import Optional, List
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QApplication
)
from PySide6.QtCore import Qt, QTimer

from database.db import get_db
from services.task_service import TaskService
from services.streak_service import StreakService
from services.stats_service import StatsService
from services.reminder_service import ReminderService
from services.export_service import ExportService

from ui.styles import get_stylesheet
from ui.views.dashboard_view import DashboardView
from ui.views.calendar_view import CalendarView
from ui.views.timetable_view import TimetableView
from ui.views.task_list_view import TaskListView
from ui.views.analytics_view import AnalyticsView
from ui.views.settings_view import SettingsView
from ui.dialogs.task_dialog import TaskDialog
from ui.components.toast import ToastNotification
from utils.date_helpers import format_date_display, today_date, today_str


class MainWindow(QMainWindow):
    """Master Application Window for StudyFlow."""

    def __init__(self, db_path: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("StudyFlow — Smart Calendar & Timetable Manager")
        self.setMinimumSize(1150, 750)
        self.resize(1280, 820)

        # Initialize Data & Services
        self.db = get_db(db_path)
        self.task_service = TaskService(self.db)
        self.streak_service = StreakService(self.db)
        self.stats_service = StatsService(self.db)
        self.export_service = ExportService(self.db)
        self.reminder_service = ReminderService(self.db, self)

        # Load Settings
        self._load_app_settings()

        # Build UI Structure
        self._init_ui()
        self._apply_theme(self.current_theme)

        # Start background reminder service
        self.reminder_service.reminder_triggered.connect(self._on_reminder_triggered)
        self.reminder_service.start()

    def _load_app_settings(self):
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings;")
            settings = {r["key"]: r["value"] for r in cursor.fetchall()}

        self.user_name = settings.get("user_name", "Student")
        self.current_theme = settings.get("theme", "dark")

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_h_layout = QHBoxLayout(central_widget)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        self.sidebar = self._build_sidebar()
        main_h_layout.addWidget(self.sidebar)

        # 2. Right Content Column (Header + Stacked Pages)
        right_column = QWidget()
        right_v_layout = QVBoxLayout(right_column)
        right_v_layout.setContentsMargins(0, 0, 0, 0)
        right_v_layout.setSpacing(0)

        # Header Bar
        self.header = self._build_header()
        right_v_layout.addWidget(self.header)

        # Stacked Pages
        self.stack = QStackedWidget()
        self._init_views()
        right_v_layout.addWidget(self.stack, stretch=1)

        main_h_layout.addWidget(right_column, stretch=1)

        # Setup Live Clock Timer
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start()

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebarWidget")
        sidebar.setFixedWidth(230)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(8)

        # Brand / Logo Header
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(4, 0, 4, 16)
        brand_layout.setSpacing(10)

        logo_icon = QLabel("⚡")
        logo_icon.setStyleSheet("""
            QLabel {
                font-size: 20px;
                background-color: #6366F1;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        brand_layout.addWidget(logo_icon)

        brand_title = QLabel("StudyFlow")
        brand_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #F8FAFC; letter-spacing: 0.5px; background: transparent;")
        brand_layout.addWidget(brand_title)
        brand_layout.addStretch()

        layout.addLayout(brand_layout)

        # Navigation Buttons
        self.nav_buttons: List[QPushButton] = []
        nav_items = [
            ("🏠  Dashboard", 0),
            ("📅  Calendar", 1),
            ("🕐  Timetable", 2),
            ("📋  Tasks", 3),
            ("📊  Analytics", 4),
            ("⚙  Settings", 5),
        ]

        for label, index in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("active", "true" if index == 0 else "false")
            btn.clicked.connect(lambda _, idx=index: self._navigate_to(idx))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        # Theme Toggle Button in Sidebar Footer
        self.theme_toggle_btn = QPushButton("🌙 Dark Mode")
        self.theme_toggle_btn.setObjectName("secondaryButton")
        self.theme_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.theme_toggle_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_toggle_btn)

        return sidebar

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("headerBar")
        header.setFixedHeight(64)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(16)

        # Live Clock
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("color: #64748B; font-size: 13px; font-weight: 500; background: transparent;")
        self._update_clock()
        layout.addWidget(self.clock_label)

        layout.addStretch()

        # "+ Quick Add" Primary Button
        quick_add_btn = QPushButton("+ New Task")
        quick_add_btn.setObjectName("primaryButton")
        quick_add_btn.setCursor(Qt.PointingHandCursor)
        quick_add_btn.clicked.connect(self._quick_add_task)
        layout.addWidget(quick_add_btn)

        # User Profile Badge
        self.profile_pill = QLabel(f"👤  {self.user_name}")
        self.profile_pill.setStyleSheet("""
            QLabel {
                background-color: rgba(99, 102, 241, 0.15);
                color: #6366F1;
                font-weight: 600;
                font-size: 12px;
                border-radius: 8px;
                padding: 6px 12px;
            }
        """)
        layout.addWidget(self.profile_pill)

        return header

    def _init_views(self):
        # 0. Dashboard
        self.dashboard_view = DashboardView(
            self.task_service, self.stats_service, self.streak_service, self.user_name, self
        )
        self.dashboard_view.task_updated.connect(self._refresh_all_views)
        self.stack.addWidget(self.dashboard_view)

        # 1. Calendar
        self.calendar_view = CalendarView(self.task_service, self)
        self.calendar_view.task_updated.connect(self._refresh_all_views)
        self.stack.addWidget(self.calendar_view)

        # 2. Timetable
        self.timetable_view = TimetableView(self.task_service, self)
        self.timetable_view.task_updated.connect(self._refresh_all_views)
        self.stack.addWidget(self.timetable_view)

        # 3. Task List
        self.task_list_view = TaskListView(self.task_service, self.streak_service, self)
        self.task_list_view.task_updated.connect(self._refresh_all_views)
        self.stack.addWidget(self.task_list_view)

        # 4. Analytics
        self.analytics_view = AnalyticsView(self.stats_service, self)
        self.stack.addWidget(self.analytics_view)

        # 5. Settings
        self.settings_view = SettingsView(
            self.db, self.export_service, self.user_name, self.current_theme, self
        )
        self.settings_view.theme_changed.connect(self._apply_theme)
        self.settings_view.user_name_changed.connect(self._on_user_name_changed)
        self.settings_view.data_reset_requested.connect(self._refresh_all_views)
        self.stack.addWidget(self.settings_view)

    def _navigate_to(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            is_active = (i == index)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().polish(btn)

        # Auto refresh active view
        if index == 0:
            self.dashboard_view.refresh_data()
        elif index == 1:
            self.calendar_view.refresh_calendar()
        elif index == 2:
            self.timetable_view.refresh_timetable()
        elif index == 3:
            self.task_list_view.refresh_tasks()
        elif index == 4:
            self.analytics_view.refresh_analytics()

    def _refresh_all_views(self):
        """Refreshes data across all view tabs."""
        self.dashboard_view.refresh_data()
        self.calendar_view.refresh_calendar()
        self.timetable_view.refresh_timetable()
        self.task_list_view.refresh_tasks()
        self.analytics_view.refresh_analytics()

    def _update_clock(self):
        now = datetime.now()
        time_str = now.strftime("%I:%M:%S %p")
        date_str = format_date_display(now.date(), "full")
        self.clock_label.setText(f"📅 {date_str}   •   🕐 {time_str}")

    def _quick_add_task(self):
        dlg = TaskDialog(self.task_service, default_date=today_str(), parent=self)
        if dlg.exec() == TaskDialog.Accepted:
            self._refresh_all_views()

    def _on_user_name_changed(self, new_name: str):
        self.user_name = new_name
        self.profile_pill.setText(f"👤  {new_name}")
        self.dashboard_view.set_user_name(new_name)

    def _apply_theme(self, theme_name: str):
        self.current_theme = theme_name
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_stylesheet(theme_name))

        if theme_name == "dark":
            self.theme_toggle_btn.setText("🌙 Dark Mode")
        else:
            self.theme_toggle_btn.setText("☀️ Light Mode")

        self._refresh_all_views()

    def _toggle_theme(self):
        new_theme = "light" if self.current_theme == "dark" else "dark"
        with self.db.transaction() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('theme', ?);", (new_theme,))
        self._apply_theme(new_theme)

    def _on_reminder_triggered(self, task_instance, minutes_remaining: int):
        """Displays floating toast notification on bottom right of the window."""
        msg = f"{task_instance.title} is scheduled in {minutes_remaining} minutes ({task_instance.start_time})."
        toast = ToastNotification(
            title="Task Reminder",
            message=msg,
            task_id=task_instance.task_id,
            duration_ms=10000,
            parent=self
        )
        toast.mark_done_requested.connect(self._on_toast_mark_done)

        margin_x = 24
        margin_y = 24
        toast.move(self.width() - toast.width() - margin_x, self.height() - toast.height() - margin_y)
        toast.show()

    def _on_toast_mark_done(self, task_id: int):
        self.task_service.toggle_task_completion(task_id, today_date())
        self._refresh_all_views()
