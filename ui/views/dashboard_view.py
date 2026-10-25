"""
StudyFlow Dashboard View (FR-01)
Central hub displaying today's progress, live greeting, metric stat cards,
interactive today's schedule, and 14-day completion trend.
"""

from typing import Optional
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from services.task_service import TaskService
from services.stats_service import StatsService
from services.streak_service import StreakService
from ui.components.stat_card import StatCard
from ui.components.task_card import TaskCard
from ui.components.chart_widgets import CompletionTrendChart
from ui.dialogs.task_dialog import TaskDialog
from ui.dialogs.confirm_dialog import ask_confirm
from utils.date_helpers import today_date, today_str, format_date_display, get_greeting


class DashboardView(QWidget):
    """Main Dashboard View displaying today's progress and schedule."""

    task_updated = Signal()  # Emitted when a task is completed, edited, or created

    def __init__(
        self,
        task_service: TaskService,
        stats_service: StatsService,
        streak_service: StreakService,
        user_name: str = "Student",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.task_service = task_service
        self.stats_service = stats_service
        self.streak_service = streak_service
        self.user_name = user_name

        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(28, 24, 28, 24)
        self.main_layout.setSpacing(20)

        # 1. Welcome Greeting Header
        self._build_header()

        # 2. Today's Progress Bar Banner
        self._build_progress_banner()

        # 3. Metric Stat Cards Row
        self._build_stat_cards()

        # 4. Today's Schedule Section
        self._build_schedule_section()

        # 5. Weekly Trend
        self._build_weekly_trend()

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

    def _build_header(self):
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self.greeting_label = QLabel(f"{get_greeting()}, {self.user_name}")
        self.greeting_label.setObjectName("pageTitle")

        self.date_label = QLabel(format_date_display(today_date(), "full"))
        self.date_label.setObjectName("pageSubtitle")

        title_box.addWidget(self.greeting_label)
        title_box.addWidget(self.date_label)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # "+ Schedule Task" Quick Button
        add_btn = QPushButton("+ Schedule Task")
        add_btn.setObjectName("primaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._open_create_task_dialog)
        header_layout.addWidget(add_btn)

        self.main_layout.addLayout(header_layout)

    def _build_progress_banner(self):
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("cardFrame")
        layout = QVBoxLayout(self.progress_frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        # Top line: Title and % badge
        top_row = QHBoxLayout()
        title = QLabel("Today's Progress")
        title.setStyleSheet("font-size: 15px; font-weight: 700; background: transparent;")
        top_row.addWidget(title)
        top_row.addStretch()

        self.percent_badge = QLabel("0%")
        self.percent_badge.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: 800;
                color: #6366F1;
                background-color: rgba(99, 102, 241, 0.15);
                border-radius: 6px;
                padding: 3px 10px;
            }
        """)
        top_row.addWidget(self.percent_badge)
        layout.addLayout(top_row)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        layout.addWidget(self.progress_bar)

        # Sub-pills: Completed / Pending / Total
        pills_row = QHBoxLayout()
        pills_row.setSpacing(14)

        self.done_pill = QLabel("✓ 0 Completed")
        self.done_pill.setStyleSheet("color: #10B981; font-weight: 600; font-size: 12px; background: transparent;")

        self.pending_pill = QLabel("○ 0 Pending")
        self.pending_pill.setStyleSheet("color: #F59E0B; font-weight: 600; font-size: 12px; background: transparent;")

        self.total_pill = QLabel("Total: 0 Tasks")
        self.total_pill.setStyleSheet("color: #64748B; font-weight: 500; font-size: 12px; background: transparent;")

        pills_row.addWidget(self.done_pill)
        pills_row.addWidget(self.pending_pill)
        pills_row.addWidget(self.total_pill)
        pills_row.addStretch()
        layout.addLayout(pills_row)

        self.main_layout.addWidget(self.progress_frame)

    def _build_stat_cards(self):
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        self.streak_card = StatCard("Current Streak", "0 Days", "Consecutive days active", "🔥", "#F59E0B")
        self.best_streak_card = StatCard("Best Streak", "0 Days", "Longest unbroken streak", "⭐", "#EC4899")
        self.total_done_card = StatCard("All-Time Done", "0", "Total completed tasks", "✓", "#10B981")
        self.today_tasks_card = StatCard("Today's Tasks", "0", "Scheduled for today", "📋", "#6366F1")

        cards_layout.addWidget(self.streak_card)
        cards_layout.addWidget(self.best_streak_card)
        cards_layout.addWidget(self.total_done_card)
        cards_layout.addWidget(self.today_tasks_card)

        self.main_layout.addLayout(cards_layout)

    def _build_schedule_section(self):
        section_box = QVBoxLayout()
        section_box.setSpacing(12)

        # Section Header
        sec_header = QHBoxLayout()
        sec_title = QLabel("Today's Schedule & Timetable")
        sec_title.setObjectName("sectionTitle")
        sec_header.addWidget(sec_title)
        sec_header.addStretch()

        section_box.addLayout(sec_header)

        # Container for task cards
        self.tasks_container = QVBoxLayout()
        self.tasks_container.setSpacing(10)
        section_box.addLayout(self.tasks_container)

        self.main_layout.addLayout(section_box)

    def _build_weekly_trend(self):
        trend_frame = QFrame()
        trend_frame.setObjectName("cardFrame")
        layout = QVBoxLayout(trend_frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        t_title = QLabel("14-Day Activity Trend")
        t_title.setObjectName("sectionTitle")
        layout.addWidget(t_title)

        self.trend_chart = CompletionTrendChart()
        layout.addWidget(self.trend_chart)

        self.main_layout.addWidget(trend_frame)

    def refresh_data(self):
        """Refreshes metrics, today's schedule, and trend charts."""
        today = today_date()
        today_s = self.stats_service.get_today_stats(today)
        productivity = self.stats_service.get_overall_productivity()

        # Update greeting
        self.greeting_label.setText(f"{get_greeting()}, {self.user_name}")

        # Update Progress Banner
        pct = today_s["completion_percentage"]
        self.progress_bar.setValue(pct)
        self.percent_badge.setText(f"{pct}%")
        self.done_pill.setText(f"✓ {today_s['completed_tasks']} Completed")
        self.pending_pill.setText(f"○ {today_s['pending_tasks']} Pending")
        self.total_pill.setText(f"Total: {today_s['total_tasks']} Tasks")

        # Update Stat Cards
        self.streak_card.set_value(f"{productivity['current_streak']} Days")
        self.best_streak_card.set_value(f"{productivity['best_streak']} Days")
        self.total_done_card.set_value(str(productivity["total_completions"]))
        self.today_tasks_card.set_value(str(today_s["total_tasks"]))

        # Populate Today's Tasks
        while self.tasks_container.count() > 0:
            item = self.tasks_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        instances = self.task_service.get_tasks_for_date(today)
        if not instances:
            empty_lbl = QLabel("🎉 No tasks scheduled for today. Take a break or schedule a task!")
            empty_lbl.setStyleSheet("color: #64748B; font-size: 13px; padding: 20px; background: transparent;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.tasks_container.addWidget(empty_lbl)
        else:
            for inst in instances:
                card = TaskCard(inst)
                card.completion_toggled.connect(self._on_task_completion_toggled)
                card.edit_requested.connect(self._on_task_edit)
                card.delete_requested.connect(self._on_task_delete)
                self.tasks_container.addWidget(card)

        # Update Chart
        trend_data = self.stats_service.get_completion_trend(14)
        self.trend_chart.set_data(trend_data)

    def _on_task_completion_toggled(self, task_id: int, is_completed: bool):
        self.task_service.toggle_task_completion(task_id, today_date())
        self.refresh_data()
        self.task_updated.emit()

    def _open_create_task_dialog(self):
        dlg = TaskDialog(self.task_service, default_date=today_str(), parent=self)
        if dlg.exec() == TaskDialog.Accepted:
            self.refresh_data()
            self.task_updated.emit()

    def _on_task_edit(self, task_id: int):
        task = self.task_service.get_task_by_id(task_id)
        if task:
            dlg = TaskDialog(self.task_service, task=task, parent=self)
            if dlg.exec() == TaskDialog.Accepted:
                self.refresh_data()
                self.task_updated.emit()

    def _on_task_delete(self, task_id: int):
        task = self.task_service.get_task_by_id(task_id)
        if task:
            if ask_confirm(self, "Delete Task", "Are you sure you want to delete this task?", task.title):
                self.task_service.delete_task(task_id)
                self.refresh_data()
                self.task_updated.emit()

    def set_user_name(self, name: str):
        self.user_name = name
        self.greeting_label.setText(f"{get_greeting()}, {self.user_name}")
