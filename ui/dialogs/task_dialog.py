"""
StudyFlow Task Dialog
Comprehensive modal for creating and editing tasks with date range (start to end date),
multiple custom specific dates, repeat rules, categories, priority, and reminders.
"""

from typing import Optional, List, Set
from datetime import date, datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QComboBox, QDateEdit,
    QTimeEdit, QPushButton, QWidget, QFrame,
    QMessageBox, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, QDate, QTime
from database.models import Task
from services.task_service import TaskService
from ui.dialogs.category_dialog import CategoryDialog
from utils.date_helpers import parse_date, today_date, today_str, format_date_display


class TaskDialog(QDialog):
    """Dialog for creating and editing scheduled tasks."""

    def __init__(
        self,
        task_service: TaskService,
        task: Optional[Task] = None,
        default_date: Optional[str | date] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.task_service = task_service
        self.task = task
        self.default_date = parse_date(default_date) if default_date else today_date()
        self.custom_dates_set: Set[str] = set()

        self.setWindowTitle("Edit Task" if task else "Create New Task")
        self.setFixedSize(540, 680)
        self.setModal(True)

        self._init_ui()
        self._populate_categories()
        if self.task:
            self._populate_task_data()
        else:
            self._set_defaults()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header Title
        title_lbl = QLabel("Edit Task" if self.task else "Schedule New Task")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        main_layout.addWidget(title_lbl)

        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(4, 4, 4, 4)
        form_layout.setSpacing(14)

        # Form Container Frame
        form_frame = QFrame()
        form_frame.setObjectName("cardFrame")
        frame_layout = QVBoxLayout(form_frame)
        frame_layout.setContentsMargins(16, 16, 16, 16)
        frame_layout.setSpacing(12)

        # 1. Task Title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        lbl1 = QLabel("Task / Subject Name *")
        lbl1.setStyleSheet("font-weight: 600; font-size: 12px; color: #64748B; background: transparent;")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Discrete Mathematics (DMS)")
        title_box.addWidget(lbl1)
        title_box.addWidget(self.title_input)
        frame_layout.addLayout(title_box)

        # 2. Description
        desc_box = QVBoxLayout()
        desc_box.setSpacing(4)
        lbl2 = QLabel("Description / Notes")
        lbl2.setStyleSheet("font-weight: 600; font-size: 12px; color: #64748B; background: transparent;")
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("e.g. Chapter 3: Graph Theory and Relations")
        self.desc_input.setFixedHeight(58)
        desc_box.addWidget(lbl2)
        desc_box.addWidget(self.desc_input)
        frame_layout.addLayout(desc_box)

        # 3. Category + Priority Row
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        # Category
        cat_box = QVBoxLayout()
        cat_box.setSpacing(4)
        cat_header = QHBoxLayout()
        lbl3 = QLabel("Category")
        lbl3.setStyleSheet("font-weight: 600; font-size: 12px; color: #64748B; background: transparent;")
        cat_header.addWidget(lbl3)
        cat_header.addStretch()

        manage_cat_btn = QPushButton("+ Manage")
        manage_cat_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6366F1;
                border: none;
                font-size: 11px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        manage_cat_btn.clicked.connect(self._open_category_manager)
        cat_header.addWidget(manage_cat_btn)
        cat_box.addLayout(cat_header)

        self.cat_combo = QComboBox()
        cat_box.addWidget(self.cat_combo)
        row1.addLayout(cat_box, stretch=1)

        # Priority
        pri_box = QVBoxLayout()
        pri_box.setSpacing(4)
        lbl4 = QLabel("Priority")
        lbl4.setStyleSheet("font-weight: 600; font-size: 12px; color: #64748B; background: transparent;")
        self.pri_combo = QComboBox()
        self.pri_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.pri_combo.setCurrentText("Medium")
        pri_box.addWidget(lbl4)
        pri_box.addWidget(self.pri_combo)
        row1.addLayout(pri_box, stretch=1)

        frame_layout.addLayout(row1)

        # 4. Schedule Type / Repeat Option Selector
        rep_box = QVBoxLayout()
        rep_box.setSpacing(4)
        lbl8 = QLabel("Scheduling & Recurrence Mode")
        lbl8.setStyleSheet("font-weight: 600; font-size: 12px; color: #64748B; background: transparent;")
        self.rep_combo = QComboBox()
        self.rep_combo.addItem("Single Date (One-time)", "None")
        self.rep_combo.addItem("Date Range (Start Date to End Date)", "Date Range")
        self.rep_combo.addItem("Multiple Specific Dates (Pick Custom Days)", "Custom Dates")
        self.rep_combo.addItem("Daily (Every Day)", "Daily")
        self.rep_combo.addItem("Weekdays (Mon – Fri)", "Weekdays")
        self.rep_combo.addItem("Weekly (Same Day Every Week)", "Weekly")
        self.rep_combo.currentIndexChanged.connect(self._on_repeat_mode_changed)

        rep_box.addWidget(lbl8)
        rep_box.addWidget(self.rep_combo)
        frame_layout.addLayout(rep_box)

        # 5. Date Selection Controls
        # Container for Start / End Date pickers
        self.dates_frame = QFrame()
        dates_frame_layout = QVBoxLayout(self.dates_frame)
        dates_frame_layout.setContentsMargins(0, 0, 0, 0)
        dates_frame_layout.setSpacing(8)

        self.dates_row = QHBoxLayout()
        self.dates_row.setSpacing(12)

        # Start Date
        self.start_date_box = QVBoxLayout()
        self.start_date_box.setSpacing(4)
        self.start_date_lbl = QLabel("Date")
        self.start_date_lbl.setStyleSheet("font-weight: 600; font-size: 12px; color: #64748B; background: transparent;")
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDisplayFormat("yyyy-MM-dd")
        self.date_picker.setDate(QDate(self.default_date.year, self.default_date.month, self.default_date.day))
        self.start_date_box.addWidget(self.start_date_lbl)
        self.start_date_box.addWidget(self.date_picker)
        self.dates_row.addLayout(self.start_date_box, stretch=1)

        # End Date
        self.end_date_box = QVBoxLayout()
        self.end_date_box.setSpacing(4)
        self.end_date_lbl = QLabel("End Date")
        self.end_date_lbl.setStyleSheet("font-weight: 600; font-size: 12px; color: #64748B; background: transparent;")
        self.end_date_picker = QDateEdit()
        self.end_date_picker.setCalendarPopup(True)
        self.end_date_picker.setDisplayFormat("yyyy-MM-dd")
        self.end_date_picker.setDate(QDate(self.default_date.year, self.default_date.month, self.default_date.day))
        self.end_date_box.addWidget(self.end_date_lbl)
        self.end_date_box.addWidget(self.end_date_picker)
        self.dates_row.addLayout(self.end_date_box, stretch=1)

        dates_frame_layout.addLayout(self.dates_row)

        # Optional End Date Checkbox (for Daily/Weekdays/Weekly)
        self.has_end_date_cb = QCheckBox("Set an End Date / Deadline for recurrence")
        self.has_end_date_cb.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        self.has_end_date_cb.toggled.connect(self._on_end_date_checkbox_toggled)
        dates_frame_layout.addWidget(self.has_end_date_cb)

        frame_layout.addWidget(self.dates_frame)

        # 6. Multiple Specific / Custom Dates Picker Container
        self.custom_dates_frame = QFrame()
        self.custom_dates_frame.setObjectName("elevatedCard")
        custom_layout = QVBoxLayout(self.custom_dates_frame)
        custom_layout.setContentsMargins(12, 12, 12, 12)
        custom_layout.setSpacing(10)

        c_title = QLabel("Select Specific Dates for this Task:")
        c_title.setStyleSheet("font-weight: 600; font-size: 12px; color: #64748B; background: transparent;")
        custom_layout.addWidget(c_title)

        add_date_row = QHBoxLayout()
        add_date_row.setSpacing(8)

        self.custom_date_add_picker = QDateEdit()
        self.custom_date_add_picker.setCalendarPopup(True)
        self.custom_date_add_picker.setDisplayFormat("yyyy-MM-dd")
        self.custom_date_add_picker.setDate(QDate.currentDate())
        add_date_row.addWidget(self.custom_date_add_picker, stretch=1)

        add_date_btn = QPushButton("+ Add Date")
        add_date_btn.setObjectName("secondaryButton")
        add_date_btn.clicked.connect(self._add_custom_date_from_picker)
        add_date_row.addWidget(add_date_btn)
        custom_layout.addLayout(add_date_row)

        # Scrollable chips container for chosen dates
        self.chips_container = QWidget()
        self.chips_layout = QVBoxLayout(self.chips_container)
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_layout.setSpacing(4)
        custom_layout.addWidget(self.chips_container)

        frame_layout.addWidget(self.custom_dates_frame)

        # 7. Start & End Time Row
        row_time = QHBoxLayout()
        row_time.setSpacing(12)

        start_box = QVBoxLayout()
        start_box.setSpacing(4)
        lbl6 = QLabel("Start Time")
        lbl6.setStyleSheet("font-weight: 600; font-size: 12px; color: #64748B; background: transparent;")
        self.start_picker = QTimeEdit()
        self.start_picker.setDisplayFormat("HH:mm")
        self.start_picker.setTime(QTime(9, 0))
        start_box.addWidget(lbl6)
        start_box.addWidget(self.start_picker)
        row_time.addLayout(start_box, stretch=1)

        end_box = QVBoxLayout()
        end_box.setSpacing(4)
        lbl7 = QLabel("End Time")
        lbl7.setStyleSheet("font-weight: 600; font-size: 12px; color: #64748B; background: transparent;")
        self.end_picker = QTimeEdit()
        self.end_picker.setDisplayFormat("HH:mm")
        self.end_picker.setTime(QTime(10, 0))
        end_box.addWidget(lbl7)
        end_box.addWidget(self.end_picker)
        row_time.addLayout(end_box, stretch=1)

        # Reminder
        rem_box = QVBoxLayout()
        rem_box.setSpacing(4)
        lbl9 = QLabel("Reminder")
        lbl9.setStyleSheet("font-weight: 600; font-size: 12px; color: #64748B; background: transparent;")
        self.rem_combo = QComboBox()
        self.rem_combo.addItem("Disabled", 0)
        self.rem_combo.addItem("5 mins before", 5)
        self.rem_combo.addItem("10 mins before", 10)
        self.rem_combo.addItem("15 mins before", 15)
        self.rem_combo.addItem("30 mins before", 30)
        self.rem_combo.addItem("1 hour before", 60)
        self.rem_combo.setCurrentIndex(3)
        rem_box.addWidget(lbl9)
        rem_box.addWidget(self.rem_combo)
        row_time.addLayout(rem_box, stretch=1)

        frame_layout.addLayout(row_time)

        form_layout.addWidget(form_frame)
        scroll.setWidget(form_container)
        main_layout.addWidget(scroll, stretch=1)

        # Bottom Buttons (Cancel & Save)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Task" if self.task else "Create Task")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(save_btn)

        main_layout.addLayout(btn_layout)

        # Initialize view state
        self._on_repeat_mode_changed()

    def _on_repeat_mode_changed(self):
        mode = self.rep_combo.currentData()

        if mode == "Custom Dates":
            self.dates_frame.hide()
            self.custom_dates_frame.show()
        elif mode == "Date Range":
            self.custom_dates_frame.hide()
            self.dates_frame.show()
            self.start_date_lbl.setText("Start Date")
            self.end_date_lbl.show()
            self.end_date_picker.show()
            self.has_end_date_cb.hide()
        elif mode in ["Daily", "Weekdays", "Weekly"]:
            self.custom_dates_frame.hide()
            self.dates_frame.show()
            self.start_date_lbl.setText("Start Date")
            self.has_end_date_cb.show()
            self._on_end_date_checkbox_toggled(self.has_end_date_cb.isChecked())
        else:  # "None" / Single Date
            self.custom_dates_frame.hide()
            self.dates_frame.show()
            self.start_date_lbl.setText("Date")
            self.end_date_lbl.hide()
            self.end_date_picker.hide()
            self.has_end_date_cb.hide()

    def _on_end_date_checkbox_toggled(self, checked: bool):
        mode = self.rep_combo.currentData()
        if mode in ["Daily", "Weekdays", "Weekly"]:
            if checked:
                self.end_date_lbl.show()
                self.end_date_picker.show()
            else:
                self.end_date_lbl.hide()
                self.end_date_picker.hide()

    def _add_custom_date_from_picker(self):
        q_d = self.custom_date_add_picker.date()
        d_str = f"{q_d.year():04d}-{q_d.month():02d}-{q_d.day():02d}"
        self.custom_dates_set.add(d_str)
        self._render_custom_date_chips()

    def _remove_custom_date(self, d_str: str):
        self.custom_dates_set.discard(d_str)
        self._render_custom_date_chips()

    def _render_custom_date_chips(self):
        while self.chips_layout.count() > 0:
            item = self.chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.custom_dates_set:
            empty_lbl = QLabel("No dates added yet. Select a date above and click '+ Add Date'.")
            empty_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-style: italic; background: transparent;")
            self.chips_layout.addWidget(empty_lbl)
            return

        for d_str in sorted(list(self.custom_dates_set)):
            chip = QFrame()
            chip.setStyleSheet("""
                QFrame {
                    background-color: rgba(99, 102, 241, 0.15);
                    border: 1px solid rgba(99, 102, 241, 0.3);
                    border-radius: 6px;
                    padding: 2px;
                }
            """)
            c_layout = QHBoxLayout(chip)
            c_layout.setContentsMargins(8, 4, 8, 4)
            c_layout.setSpacing(6)

            lbl = QLabel(f"📅 {format_date_display(d_str, 'full')}")
            lbl.setStyleSheet("color: #6366F1; font-weight: 600; font-size: 11px; background: transparent;")
            c_layout.addWidget(lbl)
            c_layout.addStretch()

            del_btn = QPushButton("✕")
            del_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #EF4444;
                    font-size: 11px;
                    font-weight: bold;
                    border: none;
                    padding: 0px 4px;
                }
                QPushButton:hover {
                    color: #DC2626;
                }
            """)
            d_val = d_str
            del_btn.clicked.connect(lambda _, d_target=d_val: self._remove_custom_date(d_target))
            c_layout.addWidget(del_btn)

            self.chips_layout.addWidget(chip)

    def _populate_categories(self):
        current_id = self.cat_combo.currentData()
        self.cat_combo.clear()
        categories = self.task_service.get_all_categories()
        for cat in categories:
            self.cat_combo.addItem(f"● {cat.name}", cat.category_id)

        if current_id is not None:
            idx = self.cat_combo.findData(current_id)
            if idx >= 0:
                self.cat_combo.setCurrentIndex(idx)

    def _open_category_manager(self):
        dlg = CategoryDialog(self.task_service, self)
        dlg.exec()
        self._populate_categories()

    def _set_defaults(self):
        now = datetime.now()
        next_hour = (now.hour + 1) % 24
        self.start_picker.setTime(QTime(next_hour, 0))
        self.end_picker.setTime(QTime((next_hour + 1) % 24, 0))
        self._render_custom_date_chips()

    def _populate_task_data(self):
        if not self.task:
            return
        self.title_input.setText(self.task.title)
        self.desc_input.setText(self.task.description)

        # Category
        if self.task.category_id:
            idx = self.cat_combo.findData(self.task.category_id)
            if idx >= 0:
                self.cat_combo.setCurrentIndex(idx)

        # Priority
        p_idx = self.pri_combo.findText(self.task.priority)
        if p_idx >= 0:
            self.pri_combo.setCurrentIndex(p_idx)

        # Repeat Type
        r_type = self.task.repeat_type or "None"
        r_idx = self.rep_combo.findData(r_type)
        if r_idx >= 0:
            self.rep_combo.setCurrentIndex(r_idx)
        else:
            self.rep_combo.setCurrentIndex(0)

        # Dates
        try:
            d = parse_date(self.task.scheduled_date)
            self.date_picker.setDate(QDate(d.year, d.month, d.day))
        except Exception:
            pass

        if self.task.end_date:
            try:
                ed = parse_date(self.task.end_date)
                self.end_date_picker.setDate(QDate(ed.year, ed.month, ed.day))
                self.has_end_date_cb.setChecked(True)
            except Exception:
                pass

        # Custom Dates
        self.custom_dates_set = set(self.task.get_custom_dates_list())
        self._render_custom_date_chips()

        # Times
        try:
            sh, sm = map(int, self.task.start_time.split(":"))
            self.start_picker.setTime(QTime(sh, sm))
        except Exception:
            pass

        try:
            eh, em = map(int, self.task.end_time.split(":"))
            self.end_picker.setTime(QTime(eh, em))
        except Exception:
            pass

        # Reminder
        rem_idx = self.rem_combo.findData(self.task.reminder_minutes)
        if rem_idx >= 0:
            self.rem_combo.setCurrentIndex(rem_idx)

        self._on_repeat_mode_changed()

    def _on_save_clicked(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing Title", "Please enter a task or subject title.")
            self.title_input.setFocus()
            return

        repeat = self.rep_combo.currentData()

        # Scheduled Date and End Date resolution
        q_start = self.date_picker.date()
        start_date_str = f"{q_start.year():04d}-{q_start.month():02d}-{q_start.day():02d}"
        end_date_str = ""

        if repeat == "Date Range":
            q_end = self.end_date_picker.date()
            end_date_str = f"{q_end.year():04d}-{q_end.month():02d}-{q_end.day():02d}"
            if q_end < q_start:
                QMessageBox.warning(self, "Invalid Date Range", "The End Date cannot be earlier than the Start Date.")
                return
        elif repeat in ["Daily", "Weekdays", "Weekly"]:
            if self.has_end_date_cb.isChecked():
                q_end = self.end_date_picker.date()
                end_date_str = f"{q_end.year():04d}-{q_end.month():02d}-{q_end.day():02d}"
                if q_end < q_start:
                    QMessageBox.warning(self, "Invalid Date Range", "The Recurrence End Date cannot be earlier than the Start Date.")
                    return
        elif repeat == "Custom Dates":
            if not self.custom_dates_set:
                QMessageBox.warning(self, "No Dates Selected", "Please select and add at least one date for this task.")
                return
            # Set base scheduled date to first custom date
            start_date_str = sorted(list(self.custom_dates_set))[0]

        q_t_start = self.start_picker.time()
        start_str = f"{q_t_start.hour():02d}:{q_t_start.minute():02d}"

        q_t_end = self.end_picker.time()
        end_str = f"{q_t_end.hour():02d}:{q_t_end.minute():02d}"

        cat_id = self.cat_combo.currentData()
        priority = self.pri_combo.currentText()
        reminder_min = self.rem_combo.currentData() or 0
        desc = self.desc_input.toPlainText().strip()

        if self.task:
            self.task.title = title
            self.task.description = desc
            self.task.category_id = cat_id
            self.task.priority = priority
            self.task.scheduled_date = start_date_str
            self.task.end_date = end_date_str
            if repeat == "Custom Dates":
                self.task.set_custom_dates_list(list(self.custom_dates_set))
            else:
                self.task.custom_dates = ""
            self.task.start_time = start_str
            self.task.end_time = end_str
            self.task.repeat_type = repeat
            self.task.reminder_minutes = reminder_min
            self.task_service.update_task(self.task)
        else:
            new_task = Task(
                title=title,
                description=desc,
                category_id=cat_id,
                priority=priority,
                scheduled_date=start_date_str,
                end_date=end_date_str,
                start_time=start_str,
                end_time=end_str,
                repeat_type=repeat,
                reminder_minutes=reminder_min
            )
            if repeat == "Custom Dates":
                new_task.set_custom_dates_list(list(self.custom_dates_set))
            self.task_service.create_task(new_task)

        self.accept()
