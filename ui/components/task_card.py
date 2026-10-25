"""
StudyFlow Task Card Component
Interactive card widget representing a single task instance on a specific date.
Includes complete/pending checkbox, time pill, category pill, priority tag,
streak counter badge, and edit/delete actions.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from database.models import TaskInstance
from ui.styles import PRIORITY_COLORS
from utils.date_helpers import format_time_12h, format_date_display


class TaskCard(QFrame):
    """Interactive task card with completion toggle and details."""

    # Signals
    completion_toggled = Signal(int, bool)  # task_id, is_completed
    edit_requested = Signal(int)           # task_id
    delete_requested = Signal(int)         # task_id

    def __init__(self, task_instance: TaskInstance, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.instance = task_instance
        self.task_id = task_instance.task_id or 0
        self.is_completed = task_instance.is_completed

        self.setObjectName("cardFrame")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self._init_ui()
        self._update_visual_state()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(14)

        # Left: Completion Toggle Button (Circular check)
        self.check_btn = QPushButton()
        self.check_btn.setFixedSize(28, 28)
        self.check_btn.setCursor(Qt.PointingHandCursor)
        self.check_btn.clicked.connect(self._on_check_clicked)
        main_layout.addWidget(self.check_btn, alignment=Qt.AlignVCenter)

        # Center: Task Details (Title, Description, Pills)
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(4)

        # Top row: Time + Priority + Repeat + Streak
        badge_layout = QHBoxLayout()
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setSpacing(8)

        # Time Pill
        time_text = f"🕐 {format_time_12h(self.instance.start_time)} – {format_time_12h(self.instance.end_time)}"
        self.time_label = QLabel(time_text)
        self.time_label.setStyleSheet("""
            QLabel {
                color: #64748B;
                font-size: 11px;
                font-weight: 600;
                background: transparent;
            }
        """)
        badge_layout.addWidget(self.time_label)

        # Category Pill (Pill with rounded curves)
        cat_color = self.instance.category_color or "#6366F1"
        self.cat_pill = QLabel(f"● {self.instance.category_name}")
        self.cat_pill.setStyleSheet(f"""
            QLabel {{
                background-color: {cat_color}22;
                color: {cat_color};
                font-size: 11px;
                font-weight: 600;
                border-radius: 6px;
                padding: 2px 8px;
            }}
        """)
        badge_layout.addWidget(self.cat_pill)

        # Priority Pill (Pill with rounded curves)
        p_info = PRIORITY_COLORS.get(self.instance.priority, PRIORITY_COLORS["Medium"])
        self.priority_pill = QLabel(self.instance.priority)
        self.priority_pill.setStyleSheet(f"""
            QLabel {{
                background-color: {p_info['bg']};
                color: {p_info['color']};
                font-size: 10px;
                font-weight: 700;
                border-radius: 6px;
                padding: 2px 8px;
            }}
        """)
        badge_layout.addWidget(self.priority_pill)

        # Repeat / Date Range / Custom Dates Pill
        if self.instance.repeat_type and self.instance.repeat_type not in ["None", "Single Date"]:
            r_type = self.instance.repeat_type
            if r_type == "Date Range":
                s_str = format_date_display(self.instance.scheduled_date, "medium") if self.instance.scheduled_date else ""
                e_str = format_date_display(self.instance.end_date, "medium") if self.instance.end_date else ""
                pill_text = f"📅 Range: {s_str} – {e_str}"
            elif r_type == "Custom Dates":
                num_dates = len(self.instance.task.get_custom_dates_list())
                pill_text = f"🗓️ {num_dates} Specific Dates"
            elif self.instance.end_date:
                e_str = format_date_display(self.instance.end_date, "medium")
                pill_text = f"🔄 {r_type} (until {e_str})"
            else:
                pill_text = f"🔄 {r_type}"

            repeat_pill = QLabel(pill_text)
            repeat_pill.setStyleSheet("""
                QLabel {
                    background-color: rgba(99, 102, 241, 0.12);
                    color: #6366F1;
                    font-size: 10px;
                    font-weight: 600;
                    border-radius: 6px;
                    padding: 2px 8px;
                }
            """)
            badge_layout.addWidget(repeat_pill)

        # Streak Pill
        if self.instance.streak_info and self.instance.streak_info.total_completed_days > 0:
            streak = self.instance.streak_info
            streak_text = f"🔥 {streak.total_completed_days}d"
            if streak.current_streak > 1:
                streak_text += f" ({streak.current_streak} streak)"
            self.streak_pill = QLabel(streak_text)
            self.streak_pill.setStyleSheet("""
                QLabel {
                    background-color: rgba(245, 158, 11, 0.15);
                    color: #D97706;
                    font-size: 11px;
                    font-weight: 700;
                    border-radius: 6px;
                    padding: 2px 8px;
                }
            """)
            badge_layout.addWidget(self.streak_pill)

        badge_layout.addStretch()
        center_layout.addLayout(badge_layout)

        # Title (Theme-aware without hardcoded color)
        self.title_label = QLabel(self.instance.title)
        self.title_label.setWordWrap(True)
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        center_layout.addWidget(self.title_label)

        # Description (if any)
        if self.instance.description:
            self.desc_label = QLabel(self.instance.description)
            self.desc_label.setWordWrap(True)
            self.desc_label.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
            center_layout.addWidget(self.desc_label)

        main_layout.addLayout(center_layout, stretch=1)

        # Right: Action Buttons (Edit & Delete)
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)

        self.edit_btn = QPushButton("✎")
        self.edit_btn.setObjectName("iconButton")
        self.edit_btn.setToolTip("Edit Task")
        self.edit_btn.setFixedSize(28, 28)
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.task_id))
        actions_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setObjectName("iconButton")
        self.delete_btn.setToolTip("Delete Task")
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.task_id))
        actions_layout.addWidget(self.delete_btn)

        main_layout.addLayout(actions_layout)

    def _update_visual_state(self):
        """Updates check button icon, colors, and title strike-through."""
        if self.is_completed:
            self.check_btn.setText("✓")
            self.check_btn.setStyleSheet("""
                QPushButton {
                    background-color: #10B981;
                    color: #FFFFFF;
                    border: 2px solid #10B981;
                    border-radius: 14px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #059669;
                    border-color: #059669;
                }
            """)
            self.title_label.setStyleSheet("color: #94A3B8; text-decoration: line-through; background: transparent;")
        else:
            self.check_btn.setText("")
            self.check_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: transparent;
                    border: 2px solid #94A3B8;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    border-color: #6366F1;
                    background-color: rgba(99, 102, 241, 0.1);
                }
            """)
            self.title_label.setStyleSheet("text-decoration: none; background: transparent;")

    def _on_check_clicked(self):
        """Toggles the completed state and emits signal."""
        self.is_completed = not self.is_completed
        self._update_visual_state()
        self.completion_toggled.emit(self.task_id, self.is_completed)
