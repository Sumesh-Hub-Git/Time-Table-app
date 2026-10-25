"""
StudyFlow Category Manager Dialog
Allows creating, editing, and managing task categories with custom colors.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QWidget, QListWidget,
    QListWidgetItem, QColorDialog, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database.models import Category
from services.task_service import TaskService


PRESET_COLORS = [
    "#6366F1", "#EC4899", "#EF4444", "#8B5CF6",
    "#10B981", "#F59E0B", "#3B82F6", "#14B8A6",
    "#06B6D4", "#84CC16", "#F97316", "#64748B"
]


class CategoryDialog(QDialog):
    """Category Manager Modal Dialog."""

    def __init__(self, task_service: TaskService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.task_service = task_service
        self.selected_color = "#6366F1"

        self.setWindowTitle("Manage Categories")
        self.setFixedSize(440, 480)
        self.setModal(True)

        self._init_ui()
        self._load_categories()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title
        title_lbl = QLabel("Task Categories")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; background: transparent;")
        layout.addWidget(title_lbl)

        # List of existing categories (styles inherited from master QSS)
        self.cat_list = QListWidget()
        layout.addWidget(self.cat_list)

        # Form: Add New Category
        add_frame = QFrame()
        add_frame.setObjectName("cardFrame")
        add_layout = QVBoxLayout(add_frame)
        add_layout.setContentsMargins(12, 12, 12, 12)
        add_layout.setSpacing(10)

        add_title = QLabel("Add New Category")
        add_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #64748B; background: transparent;")
        add_layout.addWidget(add_title)

        input_row = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Category Name (e.g. Laboratory)")
        input_row.addWidget(self.name_input, stretch=1)

        # Color picker button
        self.color_btn = QPushButton("● Color")
        self.color_btn.setCursor(Qt.PointingHandCursor)
        self._update_color_btn()
        self.color_btn.clicked.connect(self._pick_color)
        input_row.addWidget(self.color_btn)

        add_layout.addLayout(input_row)

        # Color Swatches
        swatch_layout = QHBoxLayout()
        swatch_layout.setSpacing(6)
        for c in PRESET_COLORS[:8]:
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c};
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 11px;
                }}
                QPushButton:hover {{
                    border: 2px solid #FFFFFF;
                }}
            """)
            btn.clicked.connect(lambda _, col=c: self._set_color(col))
            swatch_layout.addWidget(btn)
        swatch_layout.addStretch()
        add_layout.addLayout(swatch_layout)

        add_btn = QPushButton("+ Add Category")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._add_category)
        add_layout.addWidget(add_btn)

        layout.addWidget(add_frame)

        # Bottom row: Delete & Close
        bottom_layout = QHBoxLayout()
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self._delete_selected)
        bottom_layout.addWidget(delete_btn)

        bottom_layout.addStretch()

        close_btn = QPushButton("Done")
        close_btn.setObjectName("secondaryButton")
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)

        layout.addLayout(bottom_layout)

    def _update_color_btn(self):
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.selected_color}33;
                color: {self.selected_color};
                border: 1px solid {self.selected_color};
                border-radius: 8px;
                font-weight: bold;
                padding: 6px 12px;
            }}
        """)

    def _set_color(self, color_hex: str):
        self.selected_color = color_hex
        self._update_color_btn()

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self.selected_color), self, "Choose Category Color")
        if color.isValid():
            self._set_color(color.name())

    def _load_categories(self):
        self.cat_list.clear()
        categories = self.task_service.get_all_categories()
        for cat in categories:
            item = QListWidgetItem(f"●  {cat.name}")
            item.setForeground(QColor(cat.color))
            item.setData(Qt.UserRole, cat.category_id)
            self.cat_list.addItem(item)

    def _add_category(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a category name.")
            return

        try:
            self.task_service.create_category(name, self.selected_color)
            self.name_input.clear()
            self._load_categories()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create category: {e}")

    def _delete_selected(self):
        curr = self.cat_list.currentItem()
        if not curr:
            QMessageBox.information(self, "Select Category", "Please select a category to delete.")
            return

        cat_id = curr.data(Qt.UserRole)
        self.task_service.delete_category(cat_id)
        self._load_categories()
