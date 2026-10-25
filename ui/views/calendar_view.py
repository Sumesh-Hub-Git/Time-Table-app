"""
StudyFlow Monthly Calendar View (FR-02)
Interactive monthly calendar grid with task status indicators (completed,
partial, pending), month navigation, and split day detail view.
"""

from typing import Optional, Dict, Any, List
from datetime import date
import calendar
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGridLayout, QFrame, QScrollArea,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from services.task_service import TaskService
from ui.components.task_card import TaskCard
from ui.dialogs.task_dialog import TaskDialog
from ui.dialogs.confirm_dialog import ask_confirm
from ui.components.chart_widgets import _is_dark_theme
from utils.date_helpers import (
    today_date, format_date_display,
    get_month_grid
)


class CalendarDayCell(QFrame):
    """Interactive calendar day cell displaying day number and task status pills."""

    clicked = Signal(date)

    def __init__(self, day_date: date, is_current_month: bool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.day_date = day_date
        self.is_current_month = is_current_month
        self.is_selected = False
        self.is_today = (day_date == today_date())
        self.status = "none"  # "none", "completed", "partial", "pending"
        self.task_count = 0
        self.done_count = 0

        self.setObjectName("cardFrame")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(45, 55)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._init_ui()
        self._update_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Day Number Row
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.num_label = QLabel(str(self.day_date.day))
        self.num_label.setStyleSheet("font-weight: bold; font-size: 13px; background: transparent;")
        header.addWidget(self.num_label)
        header.addStretch()

        if self.is_today:
            today_badge = QLabel("Today")
            today_badge.setStyleSheet("""
                QLabel {
                    background-color: #6366F1;
                    color: #FFFFFF;
                    font-size: 9px;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 1px 4px;
                }
            """)
            header.addWidget(today_badge)

        layout.addLayout(header)

        # Task Indicator Pill with smooth rounded corners
        self.indicator_pill = QLabel("")
        self.indicator_pill.setAlignment(Qt.AlignCenter)
        self.indicator_pill.setFixedHeight(18)
        layout.addWidget(self.indicator_pill)
        layout.addStretch()

    def set_data(self, status: str, total: int, completed: int, is_selected: bool = False):
        self.status = status
        self.task_count = total
        self.done_count = completed
        self.is_selected = is_selected

        if total > 0:
            if status == "completed":
                self.indicator_pill.setText(f"✓ {completed}/{total}")
                self.indicator_pill.setStyleSheet("""
                    QLabel {
                        background-color: rgba(16, 185, 129, 0.18);
                        color: #10B981;
                        font-size: 10px;
                        font-weight: bold;
                        border-radius: 6px;
                        padding: 1px 6px;
                    }
                """)
            elif status == "partial":
                self.indicator_pill.setText(f"◐ {completed}/{total}")
                self.indicator_pill.setStyleSheet("""
                    QLabel {
                        background-color: rgba(245, 158, 11, 0.18);
                        color: #F59E0B;
                        font-size: 10px;
                        font-weight: bold;
                        border-radius: 6px;
                        padding: 1px 6px;
                    }
                """)
            else:  # pending
                self.indicator_pill.setText(f"● {total} tasks")
                self.indicator_pill.setStyleSheet("""
                    QLabel {
                        background-color: rgba(99, 102, 241, 0.18);
                        color: #6366F1;
                        font-size: 10px;
                        font-weight: bold;
                        border-radius: 6px;
                        padding: 1px 6px;
                    }
                """)
            self.indicator_pill.show()
        else:
            self.indicator_pill.setText("")
            self.indicator_pill.hide()

        self._update_style()

    def _update_style(self):
        is_dark = _is_dark_theme(self)
        if is_dark:
            bg = "#1E293B" if self.is_current_month else "#0F172A"
            text_col = "#F8FAFC" if self.is_current_month else "#475569"
            border_col = "#6366F1" if self.is_selected else ("#818CF8" if self.is_today else "#334155")
        else:
            bg = "#FFFFFF" if self.is_current_month else "#F1F5F9"
            text_col = "#0F172A" if self.is_current_month else "#94A3B8"
            border_col = "#4F46E5" if self.is_selected else ("#6366F1" if self.is_today else "#CBD5E1")

        border_w = "2px" if (self.is_selected or self.is_today) else "1px"

        self.num_label.setStyleSheet(f"color: {text_col}; font-weight: bold; font-size: 12px; background: transparent;")
        self.setStyleSheet(f"""
            QFrame#cardFrame {{
                background-color: {bg};
                border: {border_w} solid {border_col};
                border-radius: 10px;
            }}
            QFrame#cardFrame:hover {{
                border: 2px solid #818CF8;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.day_date)


class CalendarView(QWidget):
    """Full Monthly Calendar View with split day detail view."""

    task_updated = Signal()

    def __init__(self, task_service: TaskService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.task_service = task_service

        today = today_date()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_date = today

        self.day_cells: List[CalendarDayCell] = []

        self._init_ui()
        self.refresh_calendar()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(18)

        # Left Panel: Calendar Grid (2/3 width)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)

        # Header: Month/Year & Controls
        cal_header = QHBoxLayout()
        self.month_label = QLabel()
        self.month_label.setObjectName("pageTitle")
        cal_header.addWidget(self.month_label)
        cal_header.addStretch()

        prev_btn = QPushButton("◀ Prev")
        prev_btn.setObjectName("secondaryButton")
        prev_btn.clicked.connect(self._prev_month)
        cal_header.addWidget(prev_btn)

        today_btn = QPushButton("Today")
        today_btn.setObjectName("secondaryButton")
        today_btn.clicked.connect(self._go_today)
        cal_header.addWidget(today_btn)

        next_btn = QPushButton("Next ▶")
        next_btn.setObjectName("secondaryButton")
        next_btn.clicked.connect(self._next_month)
        cal_header.addWidget(next_btn)

        left_layout.addLayout(cal_header)

        # Legend Bar
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(12)
        legend_lbl = QLabel("Legend:")
        legend_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600; background: transparent;")
        legend_layout.addWidget(legend_lbl)

        lbl_done = QLabel("✓ All Completed")
        lbl_done.setStyleSheet("color: #10B981; font-size: 11px; font-weight: bold; background: transparent;")
        legend_layout.addWidget(lbl_done)

        lbl_part = QLabel("◐ Partially Done")
        lbl_part.setStyleSheet("color: #F59E0B; font-size: 11px; font-weight: bold; background: transparent;")
        legend_layout.addWidget(lbl_part)

        lbl_pend = QLabel("● Scheduled")
        lbl_pend.setStyleSheet("color: #6366F1; font-size: 11px; font-weight: bold; background: transparent;")
        legend_layout.addWidget(lbl_pend)

        legend_layout.addStretch()
        left_layout.addLayout(legend_layout)

        # Weekdays Row Header
        days_header = QHBoxLayout()
        days_header.setSpacing(6)
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for name in day_names:
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #64748B; font-weight: bold; font-size: 12px; padding: 4px; background: transparent;")
            days_header.addWidget(lbl, stretch=1)
        left_layout.addLayout(days_header)

        # Grid of Days
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(6)
        left_layout.addLayout(self.grid_layout, stretch=1)

        main_layout.addWidget(left_widget, stretch=3)

        # Right Panel: Selected Day Task Details (1/3 width)
        right_frame = QFrame()
        right_frame.setObjectName("cardFrame")
        right_frame.setMinimumWidth(320)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(14)

        # Side Header
        self.side_date_title = QLabel()
        self.side_date_title.setObjectName("sectionTitle")
        right_layout.addWidget(self.side_date_title)

        self.side_summary = QLabel()
        self.side_summary.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        right_layout.addWidget(self.side_summary)

        # Add Task Button for selected date
        self.add_for_day_btn = QPushButton("+ Add Task for this date")
        self.add_for_day_btn.setObjectName("primaryButton")
        self.add_for_day_btn.clicked.connect(self._add_task_for_selected_date)
        right_layout.addWidget(self.add_for_day_btn)

        # Scrollable Task List for selected day
        day_scroll = QScrollArea()
        day_scroll.setWidgetResizable(True)
        day_scroll_container = QWidget()
        self.side_tasks_layout = QVBoxLayout(day_scroll_container)
        self.side_tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.side_tasks_layout.setSpacing(8)
        day_scroll.setWidget(day_scroll_container)
        right_layout.addWidget(day_scroll, stretch=1)

        main_layout.addWidget(right_frame, stretch=2)

    def refresh_calendar(self):
        """Rebuilds the monthly grid and refreshes day indicator pills."""
        month_name = calendar.month_name[self.current_month]
        self.month_label.setText(f"{month_name} {self.current_year}")

        # Clear existing grid cells
        while self.grid_layout.count() > 0:
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.day_cells.clear()

        # Fetch month indicator map
        indicators = self.task_service.get_month_task_indicators(self.current_year, self.current_month)

        # Generate weeks grid
        weeks = get_month_grid(self.current_year, self.current_month)

        for row_idx, week in enumerate(weeks):
            for col_idx, d in enumerate(week):
                is_curr_m = (d.month == self.current_month)
                cell = CalendarDayCell(d, is_curr_m)
                cell.clicked.connect(self._on_day_clicked)

                d_str = d.isoformat()
                ind = indicators.get(d_str, {"status": "none", "total": 0, "completed": 0})
                is_sel = (d == self.selected_date)
                cell.set_data(ind["status"], ind["total"], ind["completed"], is_sel)

                self.grid_layout.addWidget(cell, row_idx, col_idx)
                self.day_cells.append(cell)

        self._refresh_side_panel()

    def _refresh_side_panel(self):
        """Populates the side panel with tasks for the selected date."""
        self.side_date_title.setText(format_date_display(self.selected_date, "full"))

        while self.side_tasks_layout.count() > 0:
            item = self.side_tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        instances = self.task_service.get_tasks_for_date(self.selected_date)
        total = len(instances)
        completed = sum(1 for inst in instances if inst.is_completed)

        self.side_summary.setText(f"{completed} of {total} tasks completed")

        if not instances:
            empty_lbl = QLabel("No tasks scheduled for this date.")
            empty_lbl.setStyleSheet("color: #64748B; font-size: 12px; padding: 20px; background: transparent;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.side_tasks_layout.addWidget(empty_lbl)
        else:
            for inst in instances:
                card = TaskCard(inst)
                card.completion_toggled.connect(self._on_task_completion_toggled)
                card.edit_requested.connect(self._on_task_edit)
                card.delete_requested.connect(self._on_task_delete)
                self.side_tasks_layout.addWidget(card)

    def _on_day_clicked(self, clicked_date: date):
        self.selected_date = clicked_date
        for cell in self.day_cells:
            cell.is_selected = (cell.day_date == self.selected_date)
            cell._update_style()
        self._refresh_side_panel()

    def _prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.refresh_calendar()

    def _next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.refresh_calendar()

    def _go_today(self):
        today = today_date()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_date = today
        self.refresh_calendar()

    def _on_task_completion_toggled(self, task_id: int, is_completed: bool):
        self.task_service.toggle_task_completion(task_id, self.selected_date)
        self.refresh_calendar()
        self.task_updated.emit()

    def _add_task_for_selected_date(self):
        dlg = TaskDialog(self.task_service, default_date=self.selected_date.isoformat(), parent=self)
        if dlg.exec() == TaskDialog.Accepted:
            self.refresh_calendar()
            self.task_updated.emit()

    def _on_task_edit(self, task_id: int):
        task = self.task_service.get_task_by_id(task_id)
        if task:
            dlg = TaskDialog(self.task_service, task=task, parent=self)
            if dlg.exec() == TaskDialog.Accepted:
                self.refresh_calendar()
                self.task_updated.emit()

    def _on_task_delete(self, task_id: int):
        task = self.task_service.get_task_by_id(task_id)
        if task:
            if ask_confirm(self, "Delete Task", "Are you sure you want to delete this task?", task.title):
                self.task_service.delete_task(task_id)
                self.refresh_calendar()
                self.task_updated.emit()
