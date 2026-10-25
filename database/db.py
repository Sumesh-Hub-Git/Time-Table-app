"""
StudyFlow SQLite Database Manager
Handles connection lifecycle, table migrations, schema creation,
and sample seed data initialization.
"""

import sqlite3
import os
import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

# Default database location in the application root directory
DEFAULT_DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studyflow.db")


class DatabaseManager:
    """Manages SQLite database connections and table schemas."""

    def __init__(self, db_path: str = DEFAULT_DB_FILE):
        self.db_path = db_path
        self._ensure_db_dir()
        self.init_db()

    def _ensure_db_dir(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with foreign keys enabled and Row factory."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def transaction(self):
        """Context manager for atomic database transactions."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        """Creates tables and indexes if they do not exist, and migrates missing columns."""
        with self.transaction() as conn:
            cursor = conn.cursor()

            # Categories Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL DEFAULT '#6366F1',
                icon TEXT NOT NULL DEFAULT 'bookmark'
            );
            """)

            # Tasks Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                category_id INTEGER,
                priority TEXT NOT NULL DEFAULT 'Medium',
                scheduled_date TEXT NOT NULL,
                end_date TEXT DEFAULT '',
                custom_dates TEXT DEFAULT '',
                start_time TEXT NOT NULL DEFAULT '09:00',
                end_time TEXT NOT NULL DEFAULT '10:00',
                repeat_type TEXT NOT NULL DEFAULT 'None',
                reminder_minutes INTEGER NOT NULL DEFAULT 15,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE SET NULL
            );
            """)

            # Auto-migration for existing databases
            cursor.execute("PRAGMA table_info(tasks);")
            existing_cols = [col["name"] for col in cursor.fetchall()]
            if "end_date" not in existing_cols:
                cursor.execute("ALTER TABLE tasks ADD COLUMN end_date TEXT DEFAULT '';")
            if "custom_dates" not in existing_cols:
                cursor.execute("ALTER TABLE tasks ADD COLUMN custom_dates TEXT DEFAULT '';")

            # Task Completions Table (Unique per task per completion date)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_completions (
                completion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                completion_date TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                notes TEXT DEFAULT '',
                FOREIGN KEY (task_id) REFERENCES tasks (task_id) ON DELETE CASCADE,
                UNIQUE (task_id, completion_date)
            );
            """)

            # Settings Key-Value Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS telegram_reminder_attempts (
                task_id INTEGER NOT NULL,
                reminder_date TEXT NOT NULL,
                status TEXT NOT NULL,
                last_attempt_at TEXT NOT NULL,
                sent_at TEXT,
                PRIMARY KEY (task_id, reminder_date),
                FOREIGN KEY (task_id) REFERENCES tasks (task_id) ON DELETE CASCADE
            );
            """)

            # Indexes for high performance queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_date ON tasks(scheduled_date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_active ON tasks(is_active);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_completions_task_date ON task_completions(task_id, completion_date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_completions_date ON task_completions(completion_date);")

            # Seed default categories if empty
            cursor.execute("SELECT COUNT(*) as count FROM categories;")
            if cursor.fetchone()["count"] == 0:
                self._seed_default_categories(cursor)

            # Seed sample tasks if database is brand new
            cursor.execute("SELECT COUNT(*) as count FROM tasks;")
            if cursor.fetchone()["count"] == 0:
                self._seed_sample_tasks(cursor)

    def _seed_default_categories(self, cursor: sqlite3.Cursor):
        default_categories = [
            ("Study", "#6366F1", "book-open"),         # Indigo
            ("Assignment", "#EC4899", "file-text"),     # Pink
            ("Exam", "#EF4444", "alert-circle"),       # Red
            ("Project", "#8B5CF6", "folder"),          # Purple
            ("Personal", "#10B981", "user"),           # Emerald
            ("Exercise", "#F59E0B", "activity"),       # Amber
            ("Revision", "#3B82F6", "refresh-cw"),      # Blue
            ("Practice", "#14B8A6", "target"),         # Teal
            ("Other", "#64748B", "tag")                # Slate
        ]
        cursor.executemany(
            "INSERT INTO categories (name, color, icon) VALUES (?, ?, ?);",
            default_categories
        )

    def _seed_sample_tasks(self, cursor: sqlite3.Cursor):
        """Populates realistic initial sample tasks and historical completions."""
        today = date.today()
        today_iso = today.isoformat()
        now_iso = datetime.now().isoformat()

        cursor.execute("SELECT category_id, name FROM categories;")
        cat_map = {row["name"]: row["category_id"] for row in cursor.fetchall()}

        # Sample tasks including date range and specific custom dates
        exam_dates = json.dumps([
            (today + timedelta(days=2)).isoformat(),
            (today + timedelta(days=5)).isoformat(),
            (today + timedelta(days=9)).isoformat()
        ])

        sample_tasks = [
            (
                "Discrete Mathematics & Structures (DMS)",
                "Chapter 3: Graph Theory and Relations revision",
                cat_map.get("Study", 1),
                "High",
                (today - timedelta(days=14)).isoformat(),
                "",
                "",
                "08:00",
                "10:00",
                "Daily",
                15,
                now_iso,
                1
            ),
            (
                "Digital Logic & Microprocessors",
                "K-maps minimization and multiplexer design exercises",
                cat_map.get("Study", 1),
                "High",
                (today - timedelta(days=12)).isoformat(),
                "",
                "",
                "10:30",
                "12:00",
                "Daily",
                15,
                now_iso,
                1
            ),
            (
                "Data Structures Lab Assignment",
                "Implement AVL Tree rotations and Red-Black Tree properties",
                cat_map.get("Assignment", 2),
                "Critical",
                today_iso,
                (today + timedelta(days=10)).isoformat(),
                "",
                "13:00",
                "15:00",
                "Date Range",
                30,
                now_iso,
                1
            ),
            (
                "Semester Mid-Term Exams Schedule",
                "Scheduled exam sessions across specific testing days",
                cat_map.get("Exam", 3),
                "Critical",
                today_iso,
                "",
                exam_dates,
                "09:30",
                "12:30",
                "Custom Dates",
                60,
                now_iso,
                1
            ),
            (
                "Computer Networks (CN)",
                "OSI Model, TCP/IP vs UDP protocols deep dive",
                cat_map.get("Study", 1),
                "Medium",
                (today - timedelta(days=10)).isoformat(),
                "",
                "",
                "15:30",
                "17:00",
                "Daily",
                15,
                now_iso,
                1
            ),
            (
                "Aptitude & Coding Practice",
                "Solve 2 LeetCode Medium questions & Quantitative questions",
                cat_map.get("Practice", 8),
                "Medium",
                (today - timedelta(days=20)).isoformat(),
                "",
                "",
                "18:00",
                "19:30",
                "Daily",
                10,
                now_iso,
                1
            ),
            (
                "Evening Fitness / Jogging",
                "30 mins cardio and stretching",
                cat_map.get("Exercise", 6),
                "Low",
                (today - timedelta(days=30)).isoformat(),
                "",
                "",
                "20:00",
                "20:45",
                "Daily",
                15,
                now_iso,
                1
            ),
        ]

        cursor.executemany("""
            INSERT INTO tasks (
                title, description, category_id, priority, scheduled_date,
                end_date, custom_dates, start_time, end_time, repeat_type,
                reminder_minutes, created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, sample_tasks)

        # Fetch actual task IDs for foreign key safety
        cursor.execute("SELECT task_id FROM tasks ORDER BY task_id ASC;")
        task_id_list = [r["task_id"] for r in cursor.fetchall()]
        if not task_id_list:
            return

        t1 = task_id_list[0]
        t2 = task_id_list[1] if len(task_id_list) > 1 else t1
        t_apt = task_id_list[5] if len(task_id_list) > 5 else task_id_list[-1]

        # Seed completion history
        task_completions = []
        for i in range(1, 15):
            d = today - timedelta(days=i)
            d_str = d.isoformat()
            completed_time = f"{d_str}T10:15:00"

            if i not in [4, 9]:
                task_completions.append((t1, d_str, completed_time, "Completed on time"))

            if i <= 7 or i in [10, 11]:
                task_completions.append((t2, d_str, completed_time, "Good revision session"))

            if i != 5:
                task_completions.append((t_apt, d_str, completed_time, "Solved all target problems"))

        task_completions.append((t1, today_iso, f"{today_iso}T09:45:00", "Morning session done"))
        task_completions.append((t2, today_iso, f"{today_iso}T11:50:00", "Notes completed"))

        cursor.executemany("""
            INSERT OR IGNORE INTO task_completions (task_id, completion_date, completed_at, notes)
            VALUES (?, ?, ?, ?);
        """, task_completions)

        # Default settings
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('user_name', 'Student');")
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('theme', 'dark');")
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sound_enabled', '1');")
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('default_reminder_min', '15');")


# Global database manager instance
_db_instance: Optional[DatabaseManager] = None


def get_db(db_path: Optional[str] = None) -> DatabaseManager:
    """Returns the singleton DatabaseManager instance or a custom instance for the provided path."""
    global _db_instance
    if db_path is not None:
        return DatabaseManager(db_path)
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
