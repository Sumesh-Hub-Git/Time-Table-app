"""
StudyFlow Task List & Management View (FR-04, FR-05, FR-06, FR-07, FR-14)
Searchable, filterable task manager with category & priority filters,
streak badges, detailed task history dialog, and CRUD actions.
"""

from typing import Optional
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QScrollArea,
    QFrame, QDialog, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from services.task_service import TaskService
from services.streak_service import StreakService
from ui.components.task_card import TaskCard
from ui.dialogs.task_dialog import TaskDialog
from ui.dialogs.confirm_dialog import ask_confirm
from utils.date_helpers import today_date, format_date_display


class TaskHistoryDialog(QDialog):
    """Modal displaying full completion history and streak statistics for a specific task."""

    def __init__(self, task_title: str, streak_service: StreakService, task_id: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(f"Completion History: {task_title}")
        self.setFixedSize(420, 460)
        self.setModal(True)

        streak_info = streak_service.calculate_task_streak(task_id)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title_lbl = QLabel(task_title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; background: transparent;")
        layout.addWidget(title_lbl)

        # Stats summary row
        stats_frame = QFrame()
        stats_frame.setObjectName("cardFrame")
        s_layout = QHBoxLayout(stats_frame)
        s_layout.setContentsMargins(12, 10, 12, 10)

        c1 = QLabel(f"🔥 {streak_info.total_completed_days}\nTotal Days")
        c1.setAlignment(Qt.AlignCenter)
        c1.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px; background: transparent;")

        c2 = QLabel(f"⚡ {streak_info.current_streak}\nCurrent Streak")
        c2.setAlignment(Qt.AlignCenter)
        c2.setStyleSheet("color: #F59E0B; font-weight: bold; font-size: 12px; background: transparent;")

        c3 = QLabel(f"⭐ {streak_info.best_streak}\nBest Streak")
        c3.setAlignment(Qt.AlignCenter)
        c3.setStyleSheet("color: #6366F1; font-weight: bold; font-size: 12px; background: transparent;")

        s_layout.addWidget(c1)
        s_layout.addWidget(c2)
        s_layout.addWidget(c3)
        layout.addWidget(stats_frame)

        # History list
        hist_lbl = QLabel("Completed Dates:")
        hist_lbl.setStyleSheet("font-weight: bold; color: #64748B; font-size: 12px; background: transparent;")
        layout.addWidget(hist_lbl)

        list_widget = QListWidget()
        if streak_info.completion_history:
            for d_str in reversed(streak_info.completion_history):
                item = QListWidgetItem(f"✓  {format_date_display(d_str, 'full')}")
                item.setForeground(QColor("#10B981"))
                list_widget.addItem(item)
        else:
            item = QListWidgetItem("No completions recorded yet.")
            item.setForeground(QColor("#64748B"))
            list_widget.addItem(item)

        layout.addWidget(list_widget)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondaryButton")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)


class TaskListView(QWidget):
    """Searchable & filterable Task Management View."""

    task_updated = Signal()

    def __init__(self, task_service: TaskService, streak_service: StreakService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.task_service = task_service
        self.streak_service = streak_service

        self._init_ui()
        self.refresh_tasks()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Header Row
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        page_title = QLabel("Task Manager")
        page_title.setObjectName("pageTitle")

        subtitle = QLabel("Search, organize, track streaks, and manage all your tasks")
        subtitle.setObjectName("pageSubtitle")

        title_box.addWidget(page_title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        add_btn = QPushButton("+ New Task")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._create_task)
        header.addWidget(add_btn)

        main_layout.addLayout(header)

        # Filter & Search Toolbar
        filter_frame = QFrame()
        filter_frame.setObjectName("cardFrame")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(14, 12, 14, 12)
        filter_layout.setSpacing(12)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search tasks by title, description, or subject...")
        self.search_input.textChanged.connect(self.refresh_tasks)
        filter_layout.addWidget(self.search_input, stretch=2)

        # Status Filter
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All Statuses", "Pending", "Completed"])
        self.status_combo.currentTextChanged.connect(self.refresh_tasks)
        filter_layout.addWidget(self.status_combo)

        # Category Filter
        self.cat_combo = QComboBox()
        self.cat_combo.addItem("All Categories", None)
        self.cat_combo.currentIndexChanged.connect(self.refresh_tasks)
        filter_layout.addWidget(self.cat_combo)

        # Priority Filter
        self.pri_combo = QComboBox()
        self.pri_combo.addItems(["All Priorities", "Low", "Medium", "High", "Critical"])
        self.pri_combo.currentTextChanged.connect(self.refresh_tasks)
        filter_layout.addWidget(self.pri_combo)

        main_layout.addWidget(filter_frame)

        # Scrollable Task List
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.tasks_layout = QVBoxLayout(container)
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setSpacing(10)
        scroll.setWidget(container)

        main_layout.addWidget(scroll, stretch=1)

    def _populate_categories(self):
        current_data = self.cat_combo.currentData()
        self.cat_combo.blockSignals(True)
        self.cat_combo.clear()
        self.cat_combo.addItem("All Categories", None)

        categories = self.task_service.get_all_categories()
        for cat in categories:
            self.cat_combo.addItem(f"● {cat.name}", cat.category_id)

        if current_data is not None:
            idx = self.cat_combo.findData(current_data)
            if idx >= 0:
                self.cat_combo.setCurrentIndex(idx)
        self.cat_combo.blockSignals(False)

    def refresh_tasks(self):
        self._populate_categories()

        while self.tasks_layout.count() > 0:
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        query = self.search_input.text()
        status_filter = self.status_combo.currentText()
        if status_filter == "All Statuses":
            status_filter = "All"

        category_id = self.cat_combo.currentData()
        priority = self.pri_combo.currentText()
        if priority == "All Priorities":
            priority = "All"

        instances = self.task_service.search_tasks(
            query=query,
            category_id=category_id,
            priority=priority,
            target_date=None,
            status_filter=status_filter
        )

        if not instances:
            empty_frame = QFrame()
            empty_frame.setObjectName("cardFrame")
            ef_layout = QVBoxLayout(empty_frame)
            ef_layout.setContentsMargins(40, 40, 40, 40)
            empty_lbl = QLabel("No tasks match your filter criteria.")
            empty_lbl.setStyleSheet("color: #64748B; font-size: 14px; background: transparent;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            ef_layout.addWidget(empty_lbl)
            self.tasks_layout.addWidget(empty_frame)
        else:
            for inst in instances:
                card = TaskCard(inst)
                card.completion_toggled.connect(self._on_task_completion_toggled)
                card.edit_requested.connect(self._on_task_edit)
                card.delete_requested.connect(self._on_task_delete)

                # Add a "View History / Streaks" button to card actions
                hist_btn = QPushButton("🔥 History")
                hist_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(245, 158, 11, 0.15);
                        color: #D97706;
                        border: 1px solid rgba(245, 158, 11, 0.3);
                        border-radius: 6px;
                        font-size: 11px;
                        font-weight: 700;
                        padding: 4px 8px;
                    }
                    QPushButton:hover {
                        background-color: rgba(245, 158, 11, 0.25);
                    }
                """)
                task_id = inst.task_id
                title = inst.title
                hist_btn.clicked.connect(lambda _, t_id=task_id, t_title=title: self._show_task_history(t_title, t_id))
                card.layout().addWidget(hist_btn)

                self.tasks_layout.addWidget(card)

        self.tasks_layout.addStretch()

    def _show_task_history(self, title: str, task_id: int):
        dlg = TaskHistoryDialog(title, self.streak_service, task_id, self)
        dlg.exec()

    def _create_task(self):
        dlg = TaskDialog(self.task_service, parent=self)
        if dlg.exec() == TaskDialog.Accepted:
            self.refresh_tasks()
            self.task_updated.emit()

    def _on_task_edit(self, task_id: int):
        task = self.task_service.get_task_by_id(task_id)
        if task:
            dlg = TaskDialog(self.task_service, task=task, parent=self)
            if dlg.exec() == TaskDialog.Accepted:
                self.refresh_tasks()
                self.task_updated.emit()

    def _on_task_delete(self, task_id: int):
        task = self.task_service.get_task_by_id(task_id)
        if task:
            if ask_confirm(self, "Delete Task", "Are you sure you want to delete this task?", task.title):
                self.task_service.delete_task(task_id)
                self.refresh_tasks()
                self.task_updated.emit()

    def _on_task_completion_toggled(self, task_id: int, is_completed: bool):
        self.task_service.toggle_task_completion(task_id, today_date())
        self.refresh_tasks()
        self.task_updated.emit()
