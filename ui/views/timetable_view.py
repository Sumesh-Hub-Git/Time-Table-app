"""
StudyFlow Timetable View (FR-03)
Provides both a Daily Time-Blocked Schedule (07:00 - 22:00)
and a Weekly Timetable Matrix (Mon - Sun) with category colors and completion toggles.
"""

from typing import Optional, List
from datetime import date, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from services.task_service import TaskService
from database.models import TaskInstance
from ui.components.task_card import TaskCard
from ui.dialogs.task_dialog import TaskDialog
from ui.dialogs.confirm_dialog import ask_confirm
from utils.date_helpers import (
    today_date, format_date_display,
    get_week_dates
)


class TimetableView(QWidget):
    """Timetable View supporting Daily and Weekly modes."""

    task_updated = Signal()

    def __init__(self, task_service: TaskService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.task_service = task_service
        self.current_date = today_date()
        self.view_mode = "daily"  # "daily" or "weekly"

        self._init_ui()
        self.refresh_timetable()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Header Bar: Title, Date Navigator, Mode Switcher, + Add Slot
        header_layout = QHBoxLayout()

        # Title & Subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.page_title = QLabel("Timetable")
        self.page_title.setObjectName("pageTitle")
        self.date_subtitle = QLabel()
        self.date_subtitle.setObjectName("pageSubtitle")
        title_box.addWidget(self.page_title)
        title_box.addWidget(self.date_subtitle)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Mode Toggle Buttons (Daily vs Weekly)
        mode_frame = QFrame()
        mode_frame.setObjectName("cardFrame")
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(4, 4, 4, 4)
        mode_layout.setSpacing(4)

        self.daily_btn = QPushButton("Daily Schedule")
        self.daily_btn.setObjectName("navButton")
        self.daily_btn.setProperty("active", "true")
        self.daily_btn.clicked.connect(lambda: self._set_mode("daily"))

        self.weekly_btn = QPushButton("Weekly Matrix")
        self.weekly_btn.setObjectName("navButton")
        self.weekly_btn.setProperty("active", "false")
        self.weekly_btn.clicked.connect(lambda: self._set_mode("weekly"))

        mode_layout.addWidget(self.daily_btn)
        mode_layout.addWidget(self.weekly_btn)
        header_layout.addWidget(mode_frame)

        # Date Navigator
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(6)

        prev_btn = QPushButton("◀")
        prev_btn.setObjectName("secondaryButton")
        prev_btn.setFixedSize(36, 36)
        prev_btn.clicked.connect(self._prev_period)
        nav_layout.addWidget(prev_btn)

        today_btn = QPushButton("Today")
        today_btn.setObjectName("secondaryButton")
        today_btn.clicked.connect(self._go_today)
        nav_layout.addWidget(today_btn)

        next_btn = QPushButton("▶")
        next_btn.setObjectName("secondaryButton")
        next_btn.setFixedSize(36, 36)
        next_btn.clicked.connect(self._next_period)
        nav_layout.addWidget(next_btn)

        header_layout.addLayout(nav_layout)

        # Add Task Button
        add_btn = QPushButton("+ Add Class / Task")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._add_task)
        header_layout.addWidget(add_btn)

        main_layout.addLayout(header_layout)

        # Content Area Container
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.content_container, stretch=1)

    def _set_mode(self, mode: str):
        self.view_mode = mode
        self.daily_btn.setProperty("active", "true" if mode == "daily" else "false")
        self.weekly_btn.setProperty("active", "true" if mode == "weekly" else "false")
        self.daily_btn.style().polish(self.daily_btn)
        self.weekly_btn.style().polish(self.weekly_btn)
        self.refresh_timetable()

    def refresh_timetable(self):
        # Clear content container
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.view_mode == "daily":
            self.date_subtitle.setText(format_date_display(self.current_date, "full"))
            self._render_daily_view()
        else:
            week_dates = get_week_dates(self.current_date)
            start_str = week_dates[0].strftime("%d %b")
            end_str = week_dates[6].strftime("%d %b %Y")
            self.date_subtitle.setText(f"Week of {start_str} – {end_str}")
            self._render_weekly_view(week_dates)

    def _render_daily_view(self):
        """Renders hourly time-blocked daily schedule."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        instances = self.task_service.get_tasks_for_date(self.current_date)

        if not instances:
            empty_frame = QFrame()
            empty_frame.setObjectName("cardFrame")
            ef_layout = QVBoxLayout(empty_frame)
            ef_layout.setContentsMargins(40, 40, 40, 40)
            empty_lbl = QLabel("No classes or tasks scheduled for this day.")
            empty_lbl.setStyleSheet("color: #64748B; font-size: 14px; background: transparent;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            ef_layout.addWidget(empty_lbl)
            layout.addWidget(empty_frame)
        else:
            for inst in instances:
                card = TaskCard(inst)
                card.completion_toggled.connect(self._on_task_completion_toggled)
                card.edit_requested.connect(self._on_task_edit)
                card.delete_requested.connect(self._on_task_delete)
                layout.addWidget(card)

        layout.addStretch()
        scroll.setWidget(container)
        self.content_layout.addWidget(scroll)

    def _render_weekly_view(self, week_dates: List[date]):
        """Renders 7-column weekly matrix view."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setSpacing(8)

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for col_idx, (d, d_name) in enumerate(zip(week_dates, day_names)):
            is_today = (d == today_date())

            # Column Container Frame
            col_frame = QFrame()
            col_frame.setObjectName("cardFrame")
            col_layout = QVBoxLayout(col_frame)
            col_layout.setContentsMargins(10, 10, 10, 10)
            col_layout.setSpacing(8)

            # Column Header
            col_header = QVBoxLayout()
            col_header.setSpacing(2)

            name_lbl = QLabel(d_name[:3].upper())
            name_lbl.setStyleSheet("font-weight: bold; color: #6366F1; font-size: 11px; background: transparent;")
            col_header.addWidget(name_lbl, alignment=Qt.AlignCenter)

            date_lbl = QLabel(d.strftime("%d %b"))
            date_color = "#6366F1" if is_today else "inherit"
            date_lbl.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {date_color}; background: transparent;")
            col_header.addWidget(date_lbl, alignment=Qt.AlignCenter)

            col_layout.addLayout(col_header)

            # Divider line
            div = QFrame()
            div.setFrameShape(QFrame.HLine)
            div.setObjectName("elevatedCard")
            div.setFixedHeight(1)
            col_layout.addWidget(div)

            # Tasks for this date
            day_instances = self.task_service.get_tasks_for_date(d)
            if not day_instances:
                empty = QLabel("—")
                empty.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
                empty.setAlignment(Qt.AlignCenter)
                col_layout.addWidget(empty)
            else:
                for inst in day_instances:
                    slot_card = QFrame()
                    slot_card.setObjectName("elevatedCard")
                    slot_card.setStyleSheet(f"""
                        QFrame#elevatedCard {{
                            border-left: 3px solid {inst.category_color or '#6366F1'};
                            border-radius: 8px;
                            padding: 4px;
                        }}
                    """)
                    sl_layout = QVBoxLayout(slot_card)
                    sl_layout.setContentsMargins(6, 6, 6, 6)
                    sl_layout.setSpacing(2)

                    time_lbl = QLabel(f"{inst.start_time} – {inst.end_time}")
                    time_lbl.setStyleSheet("color: #64748B; font-size: 10px; background: transparent;")
                    sl_layout.addWidget(time_lbl)

                    title_style = "color: #94A3B8; text-decoration: line-through;" if inst.is_completed else "font-weight: bold;"
                    title_lbl = QLabel(inst.title)
                    title_lbl.setWordWrap(True)
                    title_lbl.setStyleSheet(f"{title_style} font-size: 11px; background: transparent;")
                    sl_layout.addWidget(title_lbl)

                    cat_lbl = QLabel(f"● {inst.category_name}")
                    cat_lbl.setStyleSheet(f"color: {inst.category_color or '#6366F1'}; font-size: 9px; font-weight: 600; background: transparent;")
                    sl_layout.addWidget(cat_lbl)

                    col_layout.addWidget(slot_card)

            col_layout.addStretch()
            grid.addWidget(col_frame, 0, col_idx)

        scroll.setWidget(container)
        self.content_layout.addWidget(scroll)

    def _prev_period(self):
        if self.view_mode == "daily":
            self.current_date -= timedelta(days=1)
        else:
            self.current_date -= timedelta(days=7)
        self.refresh_timetable()

    def _next_period(self):
        if self.view_mode == "daily":
            self.current_date += timedelta(days=1)
        else:
            self.current_date += timedelta(days=7)
        self.refresh_timetable()

    def _go_today(self):
        self.current_date = today_date()
        self.refresh_timetable()

    def _add_task(self):
        dlg = TaskDialog(self.task_service, default_date=self.current_date.isoformat(), parent=self)
        if dlg.exec() == TaskDialog.Accepted:
            self.refresh_timetable()
            self.task_updated.emit()

    def _on_task_completion_toggled(self, task_id: int, is_completed: bool):
        self.task_service.toggle_task_completion(task_id, self.current_date)
        self.refresh_timetable()
        self.task_updated.emit()

    def _on_task_edit(self, task_id: int):
        task = self.task_service.get_task_by_id(task_id)
        if task:
            dlg = TaskDialog(self.task_service, task=task, parent=self)
            if dlg.exec() == TaskDialog.Accepted:
                self.refresh_timetable()
                self.task_updated.emit()

    def _on_task_delete(self, task_id: int):
        task = self.task_service.get_task_by_id(task_id)
        if task:
            if ask_confirm(self, "Delete Task", "Are you sure you want to delete this task?", task.title):
                self.task_service.delete_task(task_id)
                self.refresh_timetable()
                self.task_updated.emit()
