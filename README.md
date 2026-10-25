# StudyFlow — Smart Calendar & Timetable Task Management Application

> **A modern, academic desktop productivity system built with Python 3, PySide6 (Qt6), and SQLite.**  
> Designed for college students and professionals to schedule tasks, manage daily/weekly timetables, maintain habit streaks, and analyze long-term productivity trends.

---

## Table of Contents
- [1. Overview & Objectives](#1-overview--objectives)
- [2. System Architecture](#2-system-architecture)
- [3. Key Features & SRS Mapping](#3-key-features--srs-mapping)
- [4. Streak Calculation Algorithm](#4-streak-calculation-algorithm)
- [5. Project Directory Structure](#5-project-directory-structure)
- [6. Database Schema](#6-database-schema)
- [7. Installation & Setup Guide](#7-installation--setup-guide)
- [8. Running Automated Tests](#8-running-automated-tests)
- [9. College Project Report Summary](#9-college-project-report-summary)

---

## 1. Overview & Objectives

**StudyFlow** combines a **Calendar**, **Timetable**, **Task Manager**, and **Task Completion/Streak Tracker** into a unified modern desktop application.

### Key Objectives:
1. **Organized Digital Timetable**: Easily manage class schedules, study blocks, lab assignments, and revision sessions.
2. **Habit Streak & Completion Engine**: Automatically track how many days tasks have been completed, calculate consecutive streaks, and record all-time personal best streaks.
3. **Interactive Monthly Calendar**: Visually inspect days with complete (🟢), partial (🟡), or pending (🔵) tasks.
4. **Productivity Analytics**: View real-time charts (14-day completion trends, category donut distributions, day-of-week productivity heatmaps).
5. **Modern Native UI/UX**: Dark and Light theme engine with smooth styling, responsive sidebars, card layouts, and floating reminder toasts.
6. **Data Reliability & Portability**: Local SQLite database with zero cloud dependencies, CSV/JSON data export, and database backup/restore.

---

## 2. System Architecture

StudyFlow implements a clean layered MVC/Service Architecture:

```text
┌────────────────────────────────────────────────────────┐
│                   Presentation Layer                   │
│                                                        │
│  [Dashboard]   [Calendar]   [Timetable]   [Task List]  │
│         [Analytics]   [Settings]   [Dialogs & Toast]   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                     Service Layer                      │
│                                                        │
│  TaskService  │  StreakService  │  StatsService        │
│  ReminderService  │  ExportService                     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                   Data Storage Layer                   │
│                                                        │
│  SQLite3 (WAL Mode)  │  Schema & Migrations            │
│  Tasks  │  Completions  │  Categories  │  Settings     │
└────────────────────────────────────────────────────────┘
```

---

## 3. Key Features & SRS Mapping

| SRS Requirement | Feature | Implementation Details |
| :--- | :--- | :--- |
| **FR-01: User Dashboard** | Daily Progress & Overview | Real-time progress bar (%), greeting header, 4 metric stat cards, today's schedule with checkboxes, 14-day trend mini-chart. |
| **FR-02: Monthly Calendar** | Calendar Grid & Day Detail | Interactive 6-week grid, status badges (🟢 All Done, 🟡 Partial, 🔵 Scheduled), day-selection side panel, "+ Add for this date". |
| **FR-03: Timetable** | Daily & Weekly Schedules | Hourly time-blocked Daily view (07:00–22:00) and 7-Column Weekly Matrix view with category color coding. |
| **FR-04..06: Task CRUD** | Creation, Editing, Deletion | Modal dialog for title, description, category, priority, date, start/end time, repeat rules (Daily/Weekly/Weekdays), reminder window. |
| **FR-07: Completion System** | One-Click Checkboxes | Clickable circular checkboxes on cards immediately update database and trigger streak calculations. |
| **FR-08: Streak Engine** | Day Counter & Streaks | Calculates **Total Completed Days**, **Current Consecutive Streak**, and **Best Streak**. |
| **FR-09: Task History** | Completion Modal | Detailed history dialog displaying all historical completion timestamps and streak records for any task. |
| **FR-10: Analytics** | Visual Charts & Metrics | Overall productivity score, 14-Day Completion Bar Chart, Category Donut Chart, Day-of-the-Week Heatmap. |
| **FR-11: Categories** | Category Management | Custom categories with hex color picker, icons, and filter tags. |
| **FR-12: Priority System** | Visual Priority Badges | Low (Emerald), Medium (Blue), High (Amber), Critical (Red). |
| **FR-13: Reminders** | Floating In-App Toasts | Background `QTimer` triggers non-blocking toast popups with "Mark Done" and "Dismiss" buttons before tasks start. |
| **FR-14: Search & Filters** | Real-Time Search Toolbar | Search by keywords, filter by Category, Priority, and Completion status. |
| **FR-15: Modern UI/UX** | Dark / Light Theme Engine | High-DPI QSS stylesheets, custom vector `QPainter` charts, cards, hover effects. |
| **Section 26: Backup/Export**| CSV, JSON & SQLite Backups | One-click export to CSV/JSON, full SQLite database snapshot backup and restore. |

---

## 4. Streak Calculation Algorithm

The application calculates three distinct metrics for recurring tasks and global habits:

1. **Total Completed Days**:
   $$\text{Total Days} = |\text{Unique Dates with Recorded Completion}|$$
2. **Current Streak**:
   $$\text{Streak} = \text{Count of consecutive days ending on today (or yesterday)}$$
3. **Best Streak**:
   $$\text{Best Streak} = \max(\text{Length of all historical consecutive completion sequences})$$

---

## 5. Project Directory Structure

```text
Time Table app/
│
├── main.py                     # Application bootstrap and GUI entry point
├── requirements.txt            # Python dependencies (PySide6)
├── README.md                   # Full documentation & project guide
├── studyflow.db                # SQLite database (auto-generated)
│
├── database/
│   ├── __init__.py
│   ├── db.py                   # SQLite connection manager, migrations, seed data
│   └── models.py               # Data models: Task, TaskCompletion, Category, StreakInfo
│
├── services/
│   ├── __init__.py
│   ├── task_service.py         # Task CRUD, recurring resolution, date search
│   ├── streak_service.py       # Streak & habit calculation engine
│   ├── stats_service.py        # Aggregate metrics, completion rates & trends
│   ├── reminder_service.py     # Background QTimer for approaching task alerts
│   └── export_service.py       # CSV/JSON export and SQLite backup/restore
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # Master window with sidebar, header & stacked views
│   ├── styles.py               # Modern Dark & Light QSS theme stylesheets
│   │
│   ├── components/             # Reusable GUI widgets
│   │   ├── __init__.py
│   │   ├── stat_card.py        # Metric card with icons and values
│   │   ├── task_card.py        # Interactive task card with completion toggle
│   │   ├── chart_widgets.py    # Custom antialiased QPainter bar & donut charts
│   │   └── toast.py            # Floating notification toast overlay
│   │
│   ├── dialogs/                # Modals
│   │   ├── __init__.py
│   │   ├── task_dialog.py      # Task creator & editor modal
│   │   ├── category_dialog.py  # Category manager with color picker
│   │   └── confirm_dialog.py   # Confirmation prompt for deletions
│   │
│   └── views/                  # Primary Page Views
│       ├── __init__.py
│       ├── dashboard_view.py   # FR-01: Today's progress, stats, schedule preview
│       ├── calendar_view.py    # FR-02: Monthly calendar grid & day detail panel
│       ├── timetable_view.py   # FR-03: Daily time-blocks & Weekly matrix
│       ├── task_list_view.py   # FR-04..07: Search, multi-filtering & history
│       ├── analytics_view.py   # FR-10: Productivity charts & heatmaps
│       └── settings_view.py    # FR-15/26: Profile, themes, export & backup
│
├── utils/
│   ├── __init__.py
│   └── date_helpers.py         # Date arithmetic, week/month generators, formatters
│
└── tests/                      # Automated Unit & UI Test Suite
    ├── __init__.py
    ├── test_database.py        # Schema and initialization tests
    ├── test_streaks.py         # Streak algorithm unit tests
    ├── test_task_service.py    # Task recurring logic and CRUD tests
    ├── test_stats.py           # Analytics aggregation and export tests
    └── test_ui.py              # Headless UI integration tests
```

---

## 6. Database Schema

### `tasks` Table
| Column | Type | Description |
| :--- | :--- | :--- |
| `task_id` | `INTEGER PRIMARY KEY` | Auto-increment unique task identifier |
| `title` | `TEXT NOT NULL` | Name / subject of the task |
| `description` | `TEXT` | Detailed notes or chapter information |
| `category_id` | `INTEGER` | Foreign key referencing `categories(category_id)` |
| `priority` | `TEXT NOT NULL` | `Low`, `Medium`, `High`, or `Critical` |
| `scheduled_date` | `TEXT NOT NULL` | Base date in ISO format (`YYYY-MM-DD`) |
| `start_time` | `TEXT NOT NULL` | Start time (`HH:MM` 24h) |
| `end_time` | `TEXT NOT NULL` | End time (`HH:MM` 24h) |
| `repeat_type` | `TEXT NOT NULL` | `None`, `Daily`, `Weekly`, `Weekdays` |
| `reminder_minutes` | `INTEGER NOT NULL` | Alert lead time in minutes (e.g. 15) |
| `created_at` | `TEXT NOT NULL` | ISO creation timestamp |
| `is_active` | `INTEGER NOT NULL` | Active status flag (1 or 0) |

### `task_completions` Table
| Column | Type | Description |
| :--- | :--- | :--- |
| `completion_id` | `INTEGER PRIMARY KEY` | Auto-increment completion record ID |
| `task_id` | `INTEGER NOT NULL` | Foreign key referencing `tasks(task_id)` |
| `completion_date` | `TEXT NOT NULL` | Date of completion (`YYYY-MM-DD`) |
| `completed_at` | `TEXT NOT NULL` | ISO completion timestamp |
| `notes` | `TEXT` | Optional notes on completion |

*Unique constraint on `(task_id, completion_date)` ensures accurate daily streak calculations.*

---

## 7. Installation & Setup Guide

### Prerequisites
- **Python 3.10+** (Tested and compatible with Python 3.10, 3.11, 3.12, 3.13, 3.14)
- **pip** package installer

### Setup Steps
1. Open a terminal / command prompt in the project root:
   ```bash
   cd "c:\Users\ASUS\Documents\Time Table app"
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

---

## 8. Running Automated Tests

Run the full automated test suite containing 16 unit and UI integration tests:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

All tests execute in under 3 seconds using the headless `offscreen` Qt platform.

---

## 9. College Project Report Summary

- **Project Title**: StudyFlow — Smart Calendar & Timetable Task Management Application
- **Project Type**: Desktop Productivity Software (Mini / Major College Project)
- **Primary Programming Language**: Python 3
- **GUI Framework**: PySide6 (Qt for Python)
- **Database Engine**: SQLite 3 with WAL Mode
- **Key Algorithms**: Consecutive Daily Habit Streak Engine, Dynamic Recurring Schedule Resolver, Multi-Criteria Task Filter Engine.
