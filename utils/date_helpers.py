"""
StudyFlow Date and Time Helper Utilities
Provides functions for date formatting, week/month range calculations,
relative time helpers, and calendar grid builders.
"""

from datetime import datetime, date, timedelta
import calendar
from typing import List, Tuple, Optional


def today_date() -> date:
    """Returns today's date object."""
    return date.today()


def today_str() -> str:
    """Returns today's date as ISO string (YYYY-MM-DD)."""
    return date.today().isoformat()


def current_time_str() -> str:
    """Returns current time as HH:MM (24-hour)."""
    return datetime.now().strftime("%H:%M")


def parse_date(d: str | date | datetime) -> date:
    """Converts a string (YYYY-MM-DD) or datetime to a date object."""
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        # Support YYYY-MM-DD and common formats
        try:
            return datetime.strptime(d[:10], "%Y-%m-%d").date()
        except ValueError:
            return datetime.fromisoformat(d).date()
    raise ValueError(f"Cannot parse date: {d}")


def format_date_display(d: str | date, style: str = "full") -> str:
    """
    Formats a date for display.
    - 'full': 'Monday, 31 August 2026'
    - 'medium': '31 Aug 2026'
    - 'short': '31/08/2026'
    - 'day_month': 'Mon, 31 Aug'
    - 'day_name': 'Monday'
    - 'month_year': 'August 2026'
    """
    dt = parse_date(d)
    if style == "full":
        return dt.strftime("%A, %d %B %Y")
    elif style == "medium":
        return dt.strftime("%d %b %Y")
    elif style == "short":
        return dt.strftime("%d/%m/%Y")
    elif style == "day_month":
        return dt.strftime("%a, %d %b")
    elif style == "day_name":
        return dt.strftime("%A")
    elif style == "month_year":
        return dt.strftime("%B %Y")
    return dt.isoformat()


def format_time_12h(time_str: str) -> str:
    """Converts '14:30' -> '02:30 PM' or '2:30 PM'."""
    if not time_str:
        return ""
    try:
        parts = time_str.split(":")
        h, m = int(parts[0]), int(parts[1])
        t = datetime.strptime(f"{h:02d}:{m:02d}", "%H:%M")
        return t.strftime("%I:%M %p").lstrip("0")
    except Exception:
        return time_str


def get_greeting() -> str:
    """Returns a time-appropriate greeting: Good Morning, Afternoon, or Evening."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 17:
        return "Good Afternoon"
    elif 17 <= hour < 22:
        return "Good Evening"
    else:
        return "Good Night"


def get_week_dates(pivot: Optional[date | str] = None) -> List[date]:
    """
    Returns the list of 7 dates (Monday through Sunday) for the week containing pivot.
    """
    if pivot is None:
        pivot_date = date.today()
    else:
        pivot_date = parse_date(pivot)

    # Monday is 0, Sunday is 6
    start_of_week = pivot_date - timedelta(days=pivot_date.weekday())
    return [start_of_week + timedelta(days=i) for i in range(7)]


def get_month_grid(year: int, month: int) -> List[List[Optional[date]]]:
    """
    Generates a 6-week x 7-day grid of dates for the monthly calendar view.
    Weeks start on Monday.
    """
    cal = calendar.Calendar(firstweekday=0)  # Monday start
    month_days = cal.monthdatescalendar(year, month)
    return month_days


def get_past_n_days(n: int, end_date: Optional[date | str] = None) -> List[date]:
    """Returns a list of n dates ending on end_date (inclusive), in chronological order."""
    if end_date is None:
        end = date.today()
    else:
        end = parse_date(end_date)
    return [end - timedelta(days=i) for i in reversed(range(n))]


def time_to_minutes(time_str: str) -> int:
    """Converts 'HH:MM' string into minutes since midnight."""
    if not time_str:
        return 0
    try:
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0


def minutes_to_time(minutes: int) -> str:
    """Converts minutes since midnight to 'HH:MM' string."""
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"
