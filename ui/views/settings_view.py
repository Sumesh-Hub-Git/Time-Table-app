"""
StudyFlow Settings View (FR-15, Section 26)
Configuration interface for:
- User profile & display name
- Dark / Light Theme switching
- Reminder & notification preferences
- CSV / JSON data export
- SQLite database backup & restore
- Application & technology info for project submission
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox,
    QScrollArea, QFrame, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from services.export_service import ExportService
from database.db import DatabaseManager
from ui.dialogs.confirm_dialog import ask_confirm


class SettingsView(QWidget):
    """Application Configuration, Themes, and Data Backup/Export View."""

    theme_changed = Signal(str)  # "dark" or "light"
    user_name_changed = Signal(str)
    data_reset_requested = Signal()

    def __init__(
        self,
        db: DatabaseManager,
        export_service: ExportService,
        user_name: str = "Student",
        current_theme: str = "dark",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.db = db
        self.export_service = export_service
        self.user_name = user_name
        self.current_theme = current_theme

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # Header
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        page_title = QLabel("Settings & Preferences")
        page_title.setObjectName("pageTitle")
        subtitle = QLabel("Personalize your interface, manage reminders, and export data backups")
        subtitle.setObjectName("pageSubtitle")
        title_box.addWidget(page_title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # 1. User Profile Frame
        profile_frame = self._create_card("User Profile")
        pf_layout = QVBoxLayout(profile_frame)
        pf_layout.setContentsMargins(18, 16, 18, 16)
        pf_layout.setSpacing(12)

        name_row = QHBoxLayout()
        name_lbl = QLabel("Display Name:")
        name_lbl.setStyleSheet("font-weight: 600; width: 120px; background: transparent;")
        self.name_input = QLineEdit(self.user_name)
        self.name_input.setPlaceholderText("Enter your name")

        save_name_btn = QPushButton("Save Name")
        save_name_btn.setObjectName("primaryButton")
        save_name_btn.clicked.connect(self._save_user_name)

        name_row.addWidget(name_lbl)
        name_row.addWidget(self.name_input, stretch=1)
        name_row.addWidget(save_name_btn)
        pf_layout.addLayout(name_row)
        layout.addWidget(profile_frame)

        # 2. Appearance & Theme Frame
        theme_frame = self._create_card("Appearance & Theme")
        tf_layout = QVBoxLayout(theme_frame)
        tf_layout.setContentsMargins(18, 16, 18, 16)
        tf_layout.setSpacing(12)

        theme_row = QHBoxLayout()
        t_lbl = QLabel("Theme Mode:")
        t_lbl.setStyleSheet("font-weight: 600; width: 120px; background: transparent;")

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("🌙 Dark Theme (Modern Slate / Obsidian)", "dark")
        self.theme_combo.addItem("☀️ Light Theme (Clean Crisp Minimal)", "light")
        self.theme_combo.currentIndexChanged.connect(self._on_theme_selection)

        theme_row.addWidget(t_lbl)
        theme_row.addWidget(self.theme_combo, stretch=1)
        tf_layout.addLayout(theme_row)
        layout.addWidget(theme_frame)

        # 3. Data Backup & Export Frame (Section 26)
        backup_frame = self._create_card("Data Backup & Export")
        bf_layout = QVBoxLayout(backup_frame)
        bf_layout.setContentsMargins(18, 16, 18, 16)
        bf_layout.setSpacing(14)

        b_desc = QLabel("Export your schedules and completion statistics or create full database backups.")
        b_desc.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        bf_layout.addWidget(b_desc)

        btn_grid = QHBoxLayout()
        btn_grid.setSpacing(10)

        csv_btn = QPushButton("📄 Export Tasks (CSV)")
        csv_btn.setObjectName("secondaryButton")
        csv_btn.clicked.connect(self._export_csv)

        json_btn = QPushButton("📦 Export All Data (JSON)")
        json_btn.setObjectName("secondaryButton")
        json_btn.clicked.connect(self._export_json)

        backup_btn = QPushButton("💾 Backup Database")
        backup_btn.setObjectName("secondaryButton")
        backup_btn.clicked.connect(self._backup_db)

        restore_btn = QPushButton("🔄 Restore Database")
        restore_btn.setObjectName("secondaryButton")
        restore_btn.clicked.connect(self._restore_db)

        btn_grid.addWidget(csv_btn)
        btn_grid.addWidget(json_btn)
        btn_grid.addWidget(backup_btn)
        btn_grid.addWidget(restore_btn)
        bf_layout.addLayout(btn_grid)

        # Reset sample data
        reset_row = QHBoxLayout()
        reset_row.setContentsMargins(0, 8, 0, 0)
        reset_lbl = QLabel("Reset to initial demonstration state with sample timetable data:")
        reset_lbl.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")

        reset_btn = QPushButton("Reset Sample Data")
        reset_btn.setObjectName("dangerButton")
        reset_btn.clicked.connect(self._reset_sample_data)

        reset_row.addWidget(reset_lbl)
        reset_row.addStretch()
        reset_row.addWidget(reset_btn)
        bf_layout.addLayout(reset_row)

        layout.addWidget(backup_frame)

        # 4. About & Project Info Frame
        about_frame = self._create_card("About StudyFlow")
        af_layout = QVBoxLayout(about_frame)
        af_layout.setContentsMargins(18, 16, 18, 16)
        af_layout.setSpacing(8)

        app_title = QLabel("StudyFlow — Smart Calendar & Timetable Manager")
        app_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #6366F1; background: transparent;")

        app_info = QLabel(
            "Version 1.0  •  Built with Python 3.14, PySide6 (Qt) & SQLite\n"
            "Academic Desktop Productivity System for Task Scheduling, Habit Streaks & Analytics."
        )
        app_info.setStyleSheet("color: #64748B; font-size: 12px; line-height: 1.4; background: transparent;")

        af_layout.addWidget(app_title)
        af_layout.addWidget(app_info)
        layout.addWidget(about_frame)

        layout.addStretch()
        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

    def _create_card(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("cardFrame")
        return frame

    def _load_settings(self):
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings;")
            settings = {r["key"]: r["value"] for r in cursor.fetchall()}

        if "user_name" in settings:
            self.user_name = settings["user_name"]
            self.name_input.setText(self.user_name)

        if "theme" in settings:
            idx = self.theme_combo.findData(settings["theme"])
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)

    def _save_user_name(self):
        name = self.name_input.text().strip()
        if not name:
            name = "Student"
        self.user_name = name

        with self.db.transaction() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('user_name', ?);", (name,))

        self.user_name_changed.emit(name)
        QMessageBox.information(self, "Saved", f"Display name updated to: {name}")

    def _on_theme_selection(self):
        theme_val = self.theme_combo.currentData()
        with self.db.transaction() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('theme', ?);", (theme_val,))
        self.theme_changed.emit(theme_val)

    def _export_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Tasks to CSV", "studyflow_tasks.csv", "CSV Files (*.csv)")
        if file_path:
            success = self.export_service.export_tasks_to_csv(file_path)
            if success:
                QMessageBox.information(self, "Export Successful", f"Tasks exported to:\n{file_path}")
            else:
                QMessageBox.warning(self, "Export Failed", "No tasks found to export.")

    def _export_json(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export All Data to JSON", "studyflow_backup.json", "JSON Files (*.json)")
        if file_path:
            success = self.export_service.export_all_to_json(file_path)
            if success:
                QMessageBox.information(self, "Export Successful", f"All data exported to:\n{file_path}")
            else:
                QMessageBox.warning(self, "Export Failed", "Could not export data.")

    def _backup_db(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Backup Database", "studyflow_backup.db", "SQLite Database (*.db)")
        if file_path:
            success = self.export_service.backup_database(file_path)
            if success:
                QMessageBox.information(self, "Backup Complete", f"Database backed up successfully to:\n{file_path}")
            else:
                QMessageBox.warning(self, "Backup Failed", "Could not create database backup.")

    def _restore_db(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Restore Database", "", "SQLite Database (*.db)")
        if file_path:
            if ask_confirm(self, "Restore Database", "Restoring will replace all current data with the backup file. Proceed?", is_danger=True):
                success = self.export_service.restore_database(file_path)
                if success:
                    QMessageBox.information(self, "Restore Complete", "Database restored successfully! Refreshing data...")
                    self.data_reset_requested.emit()
                else:
                    QMessageBox.critical(self, "Restore Failed", "Failed to restore database from selected file.")

    def _reset_sample_data(self):
        if ask_confirm(self, "Reset Sample Data", "This will reset all tasks and streaks back to the default sample dataset. Proceed?", is_danger=True):
            self.export_service.reset_database()
            QMessageBox.information(self, "Reset Complete", "Sample data re-initialized successfully!")
            self.data_reset_requested.emit()
