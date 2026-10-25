"""Views package for StudyFlow."""
from ui.views.dashboard_view import DashboardView
from ui.views.calendar_view import CalendarView
from ui.views.timetable_view import TimetableView
from ui.views.task_list_view import TaskListView
from ui.views.analytics_view import AnalyticsView
from ui.views.settings_view import SettingsView

__all__ = [
    "DashboardView",
    "CalendarView",
    "TimetableView",
    "TaskListView",
    "AnalyticsView",
    "SettingsView",
]
