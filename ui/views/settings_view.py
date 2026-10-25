"""StudyFlow settings, data portability, and AI Telegram integration UI."""

import sqlite3
from datetime import date
from typing import Callable, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QPlainTextEdit,
    QScrollArea, QFrame, QFileDialog, QMessageBox, QFormLayout
)
from PySide6.QtCore import Signal, QThread
from services.export_service import ExportService
from services.ai_telegram_service import (
    DEFAULT_GROQ_MODEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_URL,
    GROQ_MODEL_SUGGESTIONS,
    OLLAMA_MODEL_SUGGESTIONS,
    generate_study_message,
    list_available_models,
    send_telegram_message,
)
from database.db import DatabaseManager
from services.task_service import TaskService
from services.telegram_automation import (
    disable_automatic_reminders,
    enable_automatic_reminders,
    get_automation_credentials,
)
from ui.dialogs.confirm_dialog import ask_confirm


class _BackgroundOperation(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, operation: Callable[[], object], parent=None):
        super().__init__(parent)
        self.operation = operation

    def run(self):
        try:
            result = self.operation()
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(result)


class SettingsView(QWidget):
    """Application Configuration, Themes, and Data Backup/Export View."""

    theme_changed = Signal(str)  # "dark" or "light"
    user_name_changed = Signal(str)
    data_changed = Signal()

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
        self.task_service = TaskService(db)
        self.user_name = user_name
        self.current_theme = current_theme
        self._worker: Optional[_BackgroundOperation] = None

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

        import_btn = QPushButton("📥 Import Data (CSV / JSON)")
        import_btn.setObjectName("secondaryButton")
        import_btn.clicked.connect(self._import_data)
        bf_layout.addWidget(import_btn)

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

        # 4. AI-generated Telegram update
        telegram_frame = self._create_card("AI Study Update → Telegram")
        telegram_layout = QVBoxLayout(telegram_frame)
        telegram_layout.setContentsMargins(18, 16, 18, 16)
        telegram_layout.setSpacing(12)

        privacy_note = QLabel(
            "Manual messages use credentials entered in this window. Enabling automation stores its credentials "
            "in the Windows Credential Manager so reminders can run while the app is closed. "
            "Groq sends schedule details to its cloud API; Ollama uses your configured local server."
        )
        privacy_note.setWordWrap(True)
        privacy_note.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        telegram_layout.addWidget(privacy_note)

        self.ai_provider_form = QFormLayout()
        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItem("Groq (Cloud)", "groq")
        self.ai_provider_combo.addItem("Ollama (Local)", "ollama")
        self.ai_provider_combo.currentIndexChanged.connect(self._update_ai_provider_fields)
        self.ai_provider_form.addRow("AI provider:", self.ai_provider_combo)

        self.groq_api_key_input = QLineEdit()
        self.groq_api_key_input.setEchoMode(QLineEdit.Password)
        self.groq_api_key_input.setPlaceholderText("Enter Groq API key")
        self.ai_provider_form.addRow("Groq API key:", self.groq_api_key_input)

        self.ai_model_combo = QComboBox()
        self.ai_model_combo.setEditable(True)
        self.ai_provider_form.addRow("Model:", self.ai_model_combo)

        self.refresh_models_btn = QPushButton("Refresh available models")
        self.refresh_models_btn.setObjectName("secondaryButton")
        self.refresh_models_btn.clicked.connect(self._refresh_available_models)
        self.ai_provider_form.addRow("", self.refresh_models_btn)

        self.ollama_url_input = QLineEdit(DEFAULT_OLLAMA_URL)
        self.ollama_url_input.setPlaceholderText(DEFAULT_OLLAMA_URL)
        self.ai_provider_form.addRow("Ollama server URL:", self.ollama_url_input)
        telegram_layout.addLayout(self.ai_provider_form)

        self.telegram_bot_token_input = QLineEdit()
        self.telegram_bot_token_input.setEchoMode(QLineEdit.Password)
        self.telegram_bot_token_input.setPlaceholderText("Enter Telegram bot token")
        self.telegram_chat_id_input = QLineEdit()
        self.telegram_chat_id_input.setPlaceholderText("Enter Telegram chat ID")
        telegram_layout.addWidget(QLabel("Telegram bot token:"))
        telegram_layout.addWidget(self.telegram_bot_token_input)
        telegram_layout.addWidget(QLabel("Telegram chat ID:"))
        telegram_layout.addWidget(self.telegram_chat_id_input)

        self.generate_message_btn = QPushButton("Generate Today's Study Update")
        self.generate_message_btn.setObjectName("primaryButton")
        self.generate_message_btn.clicked.connect(self._generate_ai_message)
        telegram_layout.addWidget(self.generate_message_btn)

        self.generated_message_input = QPlainTextEdit()
        self.generated_message_input.setPlaceholderText("Your generated update will appear here for review and editing.")
        self.generated_message_input.setMinimumHeight(110)
        telegram_layout.addWidget(self.generated_message_input)

        self.send_telegram_btn = QPushButton("Send Message to Telegram")
        self.send_telegram_btn.setObjectName("secondaryButton")
        self.send_telegram_btn.setEnabled(False)
        self.send_telegram_btn.clicked.connect(self._send_telegram_message)
        telegram_layout.addWidget(self.send_telegram_btn)

        automatic_note = QLabel(
            "Automatically generate and send an AI Telegram reminder 10 minutes before each pending task. "
            "The background scheduler starts when you sign in to Windows."
        )
        automatic_note.setWordWrap(True)
        automatic_note.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        telegram_layout.addWidget(automatic_note)

        self.automatic_status_label = QLabel("Automatic reminders are disabled.")
        self.automatic_status_label.setWordWrap(True)
        telegram_layout.addWidget(self.automatic_status_label)

        automatic_buttons = QHBoxLayout()
        self.enable_automatic_btn = QPushButton("Enable Automatic Reminders")
        self.enable_automatic_btn.setObjectName("primaryButton")
        self.enable_automatic_btn.clicked.connect(self._enable_automatic_reminders)
        self.disable_automatic_btn = QPushButton("Disable Automatic Reminders")
        self.disable_automatic_btn.setObjectName("dangerButton")
        self.disable_automatic_btn.clicked.connect(self._disable_automatic_reminders)
        automatic_buttons.addWidget(self.enable_automatic_btn)
        automatic_buttons.addWidget(self.disable_automatic_btn)
        telegram_layout.addLayout(automatic_buttons)
        layout.addWidget(telegram_frame)

        # 5. About & Project Info Frame
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
        provider_index = self.ai_provider_combo.findData(
            settings.get("telegram_auto_provider", "groq")
        )
        self.ai_provider_combo.setCurrentIndex(max(provider_index, 0))
        self._update_ai_provider_fields()
        if settings.get("telegram_auto_model"):
            self.ai_model_combo.setCurrentText(settings["telegram_auto_model"])
        if settings.get("telegram_auto_ollama_url"):
            self.ollama_url_input.setText(settings["telegram_auto_ollama_url"])
        is_enabled = settings.get("telegram_auto_enabled") == "1"
        if is_enabled:
            self.automatic_status_label.setText(
                "Automatic reminders are enabled. Credentials are stored in the Windows Credential Manager."
            )
            self.telegram_bot_token_input.setPlaceholderText("Credential saved in Windows Credential Manager")
            self.telegram_chat_id_input.setPlaceholderText("Credential saved in Windows Credential Manager")
            self.groq_api_key_input.setPlaceholderText("Credential saved in Windows Credential Manager")
        self.enable_automatic_btn.setEnabled(not is_enabled)
        self.disable_automatic_btn.setEnabled(is_enabled)

    def _update_ai_provider_fields(self):
        is_groq = self.ai_provider_combo.currentData() == "groq"
        self.groq_api_key_input.setVisible(is_groq)
        self.ai_provider_form.labelForField(self.groq_api_key_input).setVisible(is_groq)
        self.ollama_url_input.setVisible(not is_groq)
        self.ai_provider_form.labelForField(self.ollama_url_input).setVisible(not is_groq)
        suggestions = GROQ_MODEL_SUGGESTIONS if is_groq else OLLAMA_MODEL_SUGGESTIONS
        default_model = DEFAULT_GROQ_MODEL if is_groq else DEFAULT_OLLAMA_MODEL
        self.ai_model_combo.clear()
        self.ai_model_combo.addItems(suggestions)
        self.ai_model_combo.setCurrentText(default_model)

    def _refresh_available_models(self):
        provider = self.ai_provider_combo.currentData()
        api_key = self.groq_api_key_input.text()
        ollama_url = self.ollama_url_input.text()
        self._start_background(
            lambda: list_available_models(provider, api_key, ollama_url),
            self._on_models_loaded,
        )

    def _on_models_loaded(self, models):
        selected_model = self.ai_model_combo.currentText()
        self.ai_model_combo.clear()
        self.ai_model_combo.addItems(models)
        if selected_model and self.ai_model_combo.findText(selected_model) < 0:
            self.ai_model_combo.addItem(selected_model)
        self.ai_model_combo.setCurrentText(selected_model or models[0])

    def _generate_ai_message(self):
        provider = self.ai_provider_combo.currentData()
        api_key = self.groq_api_key_input.text()
        model = self.ai_model_combo.currentText()
        ollama_url = self.ollama_url_input.text()
        target_date = date.today()
        tasks = self.task_service.get_tasks_for_date(target_date)
        self._start_background(
            lambda: generate_study_message(
                provider, api_key, model, ollama_url, target_date, tasks, self.user_name
            ),
            self._on_message_generated,
        )

    def _on_message_generated(self, message):
        self.generated_message_input.setPlainText(message)
        self.send_telegram_btn.setEnabled(True)

    def _send_telegram_message(self):
        bot_token = self.telegram_bot_token_input.text()
        chat_id = self.telegram_chat_id_input.text()
        message = self.generated_message_input.toPlainText()
        self._start_background(
            lambda: send_telegram_message(bot_token, chat_id, message),
            self._on_telegram_sent,
        )

    def _enable_automatic_reminders(self):
        try:
            stored_credentials = get_automation_credentials()
            enable_automatic_reminders(
                self.db,
                self.ai_provider_combo.currentData(),
                self.ai_model_combo.currentText(),
                self.ollama_url_input.text(),
                self.telegram_bot_token_input.text() or stored_credentials["telegram_bot_token"],
                self.telegram_chat_id_input.text() or stored_credentials["telegram_chat_id"],
                self.groq_api_key_input.text() or stored_credentials["groq_api_key"],
            )
        except Exception as exc:
            QMessageBox.critical(self, "Could Not Enable Automatic Reminders", str(exc))
            return

        self.telegram_bot_token_input.clear()
        self.telegram_chat_id_input.clear()
        self.groq_api_key_input.clear()
        self.automatic_status_label.setText(
            "Automatic reminders are enabled. They will run while StudyFlow is closed and start at Windows sign-in."
        )
        self.telegram_bot_token_input.setPlaceholderText("Credential saved in Windows Credential Manager")
        self.telegram_chat_id_input.setPlaceholderText("Credential saved in Windows Credential Manager")
        self.groq_api_key_input.setPlaceholderText("Credential saved in Windows Credential Manager")
        self.enable_automatic_btn.setEnabled(False)
        self.disable_automatic_btn.setEnabled(True)
        QMessageBox.information(
            self,
            "Automatic Reminders Enabled",
            "The background scheduler is running and will start automatically at Windows sign-in.",
        )

    def _disable_automatic_reminders(self):
        try:
            disable_automatic_reminders(self.db)
        except Exception as exc:
            QMessageBox.critical(self, "Could Not Disable Automatic Reminders", str(exc))
            return

        self.automatic_status_label.setText("Automatic reminders are disabled.")
        self.telegram_bot_token_input.setPlaceholderText("Enter Telegram bot token")
        self.telegram_chat_id_input.setPlaceholderText("Enter Telegram chat ID")
        self.groq_api_key_input.setPlaceholderText("Enter Groq API key")
        self.enable_automatic_btn.setEnabled(True)
        self.disable_automatic_btn.setEnabled(False)
        QMessageBox.information(
            self,
            "Automatic Reminders Disabled",
            "The Windows startup task and saved automation credentials have been removed.",
        )

    def _on_telegram_sent(self, _result):
        QMessageBox.information(self, "Message Sent", "The study update was sent to Telegram.")

    def _start_background(self, operation: Callable[[], object], on_success: Callable[[object], None]):
        if self._worker and self._worker.isRunning():
            return
        self.generate_message_btn.setEnabled(False)
        self.send_telegram_btn.setEnabled(False)
        self.refresh_models_btn.setEnabled(False)
        worker = _BackgroundOperation(operation, self)
        worker.succeeded.connect(on_success)
        worker.failed.connect(self._show_operation_error)
        worker.finished.connect(self._operation_finished)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _operation_finished(self):
        self._worker = None
        self.generate_message_btn.setEnabled(True)
        self.send_telegram_btn.setEnabled(bool(self.generated_message_input.toPlainText().strip()))
        self.refresh_models_btn.setEnabled(True)

    def _show_operation_error(self, message):
        QMessageBox.critical(self, "Operation Failed", message)

    def _import_data(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import StudyFlow Data",
            "",
            "StudyFlow exports (*.json *.csv);;JSON files (*.json);;CSV files (*.csv)",
        )
        if not file_path:
            return
        try:
            imported = self.export_service.import_data(file_path)
        except (OSError, ValueError, sqlite3.Error) as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))
            return

        QMessageBox.information(
            self,
            "Import Complete",
            "Data merged successfully:\n"
            f"Categories added: {imported['categories']}\n"
            f"Tasks added: {imported['tasks']}\n"
            f"Completions added: {imported['completions']}",
        )
        self.data_changed.emit()

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
                    self.data_changed.emit()
                else:
                    QMessageBox.critical(self, "Restore Failed", "Failed to restore database from selected file.")

    def _reset_sample_data(self):
        if ask_confirm(self, "Reset Sample Data", "This will reset all tasks and streaks back to the default sample dataset. Proceed?", is_danger=True):
            self.export_service.reset_database()
            QMessageBox.information(self, "Reset Complete", "Sample data re-initialized successfully!")
            self.data_changed.emit()

    def closeEvent(self, event):
        self.wait_for_operation()
        super().closeEvent(event)

    def wait_for_operation(self):
        if self._worker and self._worker.isRunning():
            self._worker.wait()
