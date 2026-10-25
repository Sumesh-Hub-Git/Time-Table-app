"""
StudyFlow Stat Card Component
A reusable card widget displaying a key metric (e.g. Current Streak, Total Completed,
Today's Tasks) with icon, value, label, and progress or subtext.
"""

from typing import Optional
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt


class StatCard(QFrame):
    """Modern UI Card displaying a metric value with label and icon."""

    def __init__(
        self,
        title: str,
        value: str | int,
        subtitle: str = "",
        icon: str = "📊",
        accent_color: str = "#6366F1",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.accent_color = accent_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        # Header row: Title + Icon badge
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("statLabel")

        self.icon_badge = QLabel(icon)
        self.icon_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {accent_color}22;
                color: {accent_color};
                font-size: 16px;
                border-radius: 8px;
                padding: 4px 8px;
            }}
        """)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.icon_badge)

        # Value row
        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("statValue")

        # Subtitle / trend
        self.sub_label = QLabel(subtitle)
        self.sub_label.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        if not subtitle:
            self.sub_label.hide()

        layout.addLayout(header_layout)
        layout.addWidget(self.value_label)
        layout.addWidget(self.sub_label)

    def set_value(self, value: str | int, subtitle: Optional[str] = None):
        """Updates the card metric and optional subtitle."""
        self.value_label.setText(str(value))
        if subtitle is not None:
            self.sub_label.setText(subtitle)
            self.sub_label.setVisible(bool(subtitle))
