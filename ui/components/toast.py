"""
StudyFlow Floating Toast Notification Component
Displays non-blocking popup alerts for task reminders, streak updates,
and completion milestones with actionable buttons.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor


class ToastNotification(QFrame):
    """Floating Toast alert widget with actionable buttons."""

    dismissed = Signal()
    mark_done_requested = Signal(int)  # task_id

    def __init__(
        self,
        title: str,
        message: str,
        task_id: Optional[int] = None,
        duration_ms: int = 8000,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.task_id = task_id
        self.duration_ms = duration_ms

        self.setObjectName("cardFrame")

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

        self.setFixedWidth(360)
        self._init_ui(title, message)

        # Auto-dismiss timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.duration_ms)
        self.timer.timeout.connect(self._dismiss)
        self.timer.start()

    def _init_ui(self, title: str, message: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header row
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        icon_lbl = QLabel("🔔")
        icon_lbl.setStyleSheet("font-size: 16px; background: transparent;")
        header.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 13px; background: transparent;")
        header.addWidget(title_lbl)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748B;
                border: none;
                font-size: 12px;
                font-weight: bold;
                padding: 2px 6px;
            }
            QPushButton:hover {
                color: #EF4444;
            }
        """)
        close_btn.clicked.connect(self._dismiss)
        header.addWidget(close_btn)

        layout.addLayout(header)

        # Message text
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        layout.addWidget(msg_lbl)

        # Action buttons (if task_id is present)
        if self.task_id is not None:
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.addStretch()

            done_btn = QPushButton("✓ Mark as Done")
            done_btn.setObjectName("primaryButton")
            done_btn.setStyleSheet("font-size: 11px; padding: 4px 10px;")
            done_btn.clicked.connect(self._on_mark_done)
            btn_layout.addWidget(done_btn)

            dismiss_btn = QPushButton("Dismiss")
            dismiss_btn.setObjectName("secondaryButton")
            dismiss_btn.setStyleSheet("font-size: 11px; padding: 4px 10px;")
            dismiss_btn.clicked.connect(self._dismiss)
            btn_layout.addWidget(dismiss_btn)

            layout.addLayout(btn_layout)

    def _dismiss(self):
        self.timer.stop()
        self.dismissed.emit()
        self.deleteLater()

    def _on_mark_done(self):
        if self.task_id is not None:
            self.mark_done_requested.emit(self.task_id)
        self._dismiss()
