"""
StudyFlow Confirmation Dialog
Modern styled confirmation dialog for deleting tasks, resetting data,
or performing irreversible operations.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget
)
from PySide6.QtCore import Qt


class ConfirmDialog(QDialog):
    """Custom modal dialog for action confirmation."""

    def __init__(
        self,
        title: str = "Confirm Action",
        message: str = "Are you sure you want to proceed?",
        item_name: str = "",
        confirm_text: str = "Delete",
        is_danger: bool = True,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(380, 200)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title & Icon
        header_layout = QHBoxLayout()
        icon_lbl = QLabel("⚠️" if is_danger else "ℹ️")
        icon_lbl.setStyleSheet("font-size: 20px; background: transparent;")
        header_layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; background: transparent;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Message
        msg_text = message
        if item_name:
            msg_text += f'\n\n"{item_name}"'
        msg_lbl = QLabel(msg_text)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #64748B; font-size: 13px; background: transparent;")
        layout.addWidget(msg_lbl)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton(confirm_text)
        confirm_btn.setObjectName("dangerButton" if is_danger else "primaryButton")
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)


def ask_confirm(
    parent: Optional[QWidget],
    title: str,
    message: str,
    item_name: str = "",
    confirm_text: str = "Delete",
    is_danger: bool = True
) -> bool:
    """Helper function to show confirmation dialog and return True if accepted."""
    dialog = ConfirmDialog(title, message, item_name, confirm_text, is_danger, parent)
    return dialog.exec() == QDialog.Accepted
