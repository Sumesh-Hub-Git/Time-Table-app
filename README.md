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
- **AI study updates:** Generate a daily schedule and progress message with Groq or a local Ollama model, review or edit it, then send it to Telegram using your bot token and chat ID. Optional Windows background automation sends task reminders 10 minutes before start.
- **Settings and data portability:** Choose a dark or light theme, set a display name, import CSV or JSON data, export tasks to CSV or all app data to JSON, and back up or restore the database.

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

### Standalone Windows executable

`dist\StudyFlow.exe` is a self-contained, single-file Windows build. It bundles Python and the app's Python dependencies, so people running it do not need to install Python or pip. To build it from source on Windows, install the build dependencies and run the PowerShell script:

```powershell
python -m pip install -r requirements-build.txt
.\build_exe.ps1
```

The executable stores its database and logs in `%LOCALAPPDATA%\StudyFlow`; it does not need write access to the folder containing the executable. Automatic Telegram reminders continue to use Windows Task Scheduler. Groq, Telegram, and Ollama features still require their respective network services or local Ollama installation.

## AI-generated Telegram updates

Open **Settings → AI Study Update → Telegram**:

1. Select **Groq (Cloud)** or **Ollama (Local)**, then choose a model from the dropdown. Model choices can be refreshed from Groq using your API key or from the models installed on your Ollama server. The dropdown also accepts a custom model ID. The generated update addresses you by the display name saved in app settings. Defaults are `llama-3.3-70b-versatile` for Groq and `llama3.2` for Ollama at `http://localhost:11434`.
2. For Groq, enter a Groq API key. For Ollama, make sure the Ollama server is running and the selected model is available locally.
3. Enter your Telegram bot token and chat ID, then choose **Generate Today's Study Update**.
4. Review or edit the generated message before choosing **Send Message to Telegram**.

The bot token and Groq API key are masked in the interface and are never saved in the app database. Manual sending uses credentials entered in the current session. Enabling automatic reminders stores credentials in the Windows Credential Manager so the background scheduler can use them while the app is closed. Groq receives task details sent for message generation; Ollama sends them to your configured server. Keep your bot token and API key private.

### Automatic reminders (Windows)

In **Settings → AI Study Update → Telegram**, enter your Telegram bot token and chat ID, choose Groq or Ollama and a model, then select **Enable Automatic Reminders**. StudyFlow stores credentials in the Windows Credential Manager, registers a hidden Windows Task Scheduler task for user sign-in, and starts a background scheduler. It checks pending scheduled tasks every 15 seconds and generates and sends one AI message per task during the 10-minute period before its start time. Successful deliveries are recorded to prevent duplicates; failed sends are logged and retried while the task is still upcoming.

Automatic reminders continue if you close the StudyFlow window, but Windows must remain signed in and awake for timely delivery. After signing in, the scheduler starts automatically. Groq requires network access; Ollama reminders require the configured Ollama server to be running. Choose **Disable Automatic Reminders** to remove the startup task and saved credentials. Background scheduler errors are written to `%LOCALAPPDATA%\StudyFlow\telegram_automation.log`.

Closed-app automation currently supports Windows only. Regular in-app reminders continue to work as before.

If Groq returns **HTTP 403, Cloudflare error 1010**, the request is being blocked by a network or provider access policy; changing the model or API key usually will not resolve that specific error. Use **Ollama (Local)** as an alternative, or contact the provider's support. StudyFlow identifies its requests with a `StudyFlow/1.0` user agent and displays this error with next steps.

## Importing data

Use **Settings → Data Backup & Export → Import Data (CSV / JSON)** to select:

- A StudyFlow JSON export created with **Export All Data (JSON)**. Categories, tasks, and completion history are imported; display preferences and other settings are not.
- A task CSV export created with **Export Tasks (CSV)**. Task schedules are imported; CSV files do not include completion history.

Import merges data into the current database without deleting existing records. Matching categories are reused, and already-present tasks and task completions are skipped to prevent duplicate imports. Create a database backup before importing important data.

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
├── telegram_scheduler.py   # Windows logon entry point for background reminders
├── requirements.txt         # Python dependencies
├── database/
│   ├── db.py                # SQLite setup, migrations, and seed data
│   └── models.py            # Task, category, completion, and streak models
├── services/
│   ├── task_service.py      # Task CRUD, recurrence, and search
│   ├── streak_service.py   # Completion history and streak calculations
│   ├── stats_service.py    # Productivity metrics and analytics
│   ├── reminder_service.py # In-app task reminders
│   ├── telegram_automation.py # Credential Manager and Windows startup task
│   ├── telegram_scheduler.py # Background task reminder polling
│   ├── ai_telegram_service.py # Groq/Ollama generation and Telegram delivery
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
