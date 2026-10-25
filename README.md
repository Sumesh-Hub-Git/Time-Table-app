# StudyFlow

StudyFlow is a desktop timetable and task planner for students. Create one-time or recurring schedule entries, mark work complete, and review your progress in a calendar and analytics dashboard. The application is built with Python, PySide6, and a local SQLite database.

## Features

- **Dashboard:** Review today's schedule, completion progress, and productivity summaries.
- **Calendar:** Browse a monthly calendar with daily task and completion indicators.
- **Timetable:** View scheduled tasks in daily time blocks or a weekly timetable.
- **Task management:** Create, edit, delete, search, and filter tasks by category, priority, and completion status.
- **Flexible scheduling:** Set a single date, date range, selected custom dates, daily, weekday, or weekly recurrence.
- **Categories and priorities:** Organize tasks with custom categories and color coding; assign Low, Medium, High, or Critical priority.
- **Completion tracking:** Mark tasks complete, keep completion history, and track current and best streaks.
- **Reminders:** Receive in-app reminders before upcoming tasks.
- **Analytics:** See completion trends, category breakdowns, weekday activity, and streak metrics.
- **Settings and data portability:** Choose a dark or light theme, set a display name, export tasks to CSV or all app data to JSON, and back up or restore the database.

## Requirements

- Python 3.10 or later
- pip

The GUI dependency is PySide6; see [`requirements.txt`](requirements.txt) for the version constraint.

## Installation and launch

From the project directory, create and activate a virtual environment, then install the dependencies and start the app:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

macOS or Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On first launch, StudyFlow creates its SQLite database (`studyflow.db`) in the project directory and initializes default categories and sample schedule data. The database stores tasks, categories, completions, and settings locally; no cloud account is required.

## Running tests

Run the automated unit and UI tests from the project directory:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

The UI test module configures Qt's offscreen platform so the suite can run without opening application windows.

## Project structure

```text
.
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── database/
│   ├── db.py                # SQLite setup, migrations, and seed data
│   └── models.py            # Task, category, completion, and streak models
├── services/
│   ├── task_service.py      # Task CRUD, recurrence, and search
│   ├── streak_service.py   # Completion history and streak calculations
│   ├── stats_service.py    # Productivity metrics and analytics
│   ├── reminder_service.py # In-app task reminders
│   └── export_service.py   # CSV/JSON exports and database backup/restore
├── ui/
│   ├── main_window.py      # Main window and navigation
│   ├── views/              # Dashboard, calendar, timetable, tasks, analytics, settings
│   ├── dialogs/            # Task, category, and confirmation dialogs
│   └── components/         # Reusable cards, charts, and toast notifications
├── utils/                  # Date helpers
└── tests/                  # Unit and UI tests
```

## Data and backups

StudyFlow's data is stored in `studyflow.db` in the project directory. Use **Settings → Data Backup & Export** to export task schedules, export all data, create a database backup, or restore from one. Restoring replaces the current database. **Reset Sample Data** also replaces the current task and category data, so create a backup first if you need to keep it.
