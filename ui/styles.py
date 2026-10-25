"""
StudyFlow UI Theme & Styling Engine
Provides modern Dark and Light stylesheets (QSS), consistent color palettes,
typography, card styling, and component themes.
"""

from typing import Dict, Any

# Color Palettes
DARK_PALETTE = {
    "bg_main": "#0F172A",          # Slate 900
    "bg_card": "#1E293B",          # Slate 800
    "bg_sidebar": "#090D16",       # Slate 950
    "bg_elevated": "#334155",      # Slate 700
    "bg_input": "#1E293B",
    "border": "#334155",
    "border_light": "#475569",
    "text_main": "#F8FAFC",        # Slate 50
    "text_muted": "#94A3B8",       # Slate 400
    "text_subtle": "#64748B",      # Slate 500
    "primary": "#6366F1",          # Indigo 500
    "primary_hover": "#4F46E5",    # Indigo 600
    "primary_light": "rgba(99, 102, 241, 0.15)",
    "success": "#10B981",          # Emerald 500
    "success_light": "rgba(16, 185, 129, 0.15)",
    "warning": "#F59E0B",          # Amber 500
    "warning_light": "rgba(245, 158, 11, 0.15)",
    "danger": "#EF4444",           # Rose 500
    "danger_light": "rgba(239, 68, 68, 0.15)",
    "info": "#06B6D4",             # Cyan 500
    "info_light": "rgba(6, 182, 212, 0.15)",
}

LIGHT_PALETTE = {
    "bg_main": "#F1F5F9",          # Slate 100
    "bg_card": "#FFFFFF",          # Pure White
    "bg_sidebar": "#0F172A",       # Dark Slate sidebar for crisp contrast
    "bg_elevated": "#E2E8F0",      # Slate 200
    "bg_input": "#FFFFFF",
    "border": "#CBD5E1",           # Slate 300
    "border_light": "#E2E8F0",     # Slate 200
    "text_main": "#0F172A",        # Slate 900 (Dark text for light mode)
    "text_muted": "#475569",       # Slate 600
    "text_subtle": "#64748B",      # Slate 500
    "primary": "#4F46E5",          # Indigo 600
    "primary_hover": "#4338CA",    # Indigo 700
    "primary_light": "rgba(79, 70, 229, 0.12)",
    "success": "#059669",          # Emerald 600
    "success_light": "rgba(5, 150, 105, 0.12)",
    "warning": "#D97706",          # Amber 600
    "warning_light": "rgba(217, 119, 6, 0.12)",
    "danger": "#DC2626",           # Red 600
    "danger_light": "rgba(220, 38, 38, 0.12)",
    "info": "#0891B2",             # Cyan 600
    "info_light": "rgba(8, 145, 178, 0.12)",
}

# Priority Color Mapping
PRIORITY_COLORS = {
    "Low": {"color": "#10B981", "bg": "rgba(16, 185, 129, 0.15)", "text": "#10B981"},
    "Medium": {"color": "#3B82F6", "bg": "rgba(59, 130, 246, 0.15)", "text": "#3B82F6"},
    "High": {"color": "#F59E0B", "bg": "rgba(245, 158, 11, 0.15)", "text": "#F59E0B"},
    "Critical": {"color": "#EF4444", "bg": "rgba(239, 68, 11, 0.15)", "text": "#EF4444"},
}


def get_palette(theme: str = "dark") -> Dict[str, str]:
    """Returns the color dictionary for the given theme."""
    return DARK_PALETTE if theme == "dark" else LIGHT_PALETTE


def get_stylesheet(theme: str = "dark") -> str:
    """Generates the master Qt StyleSheet (QSS) for the application."""
    p = get_palette(theme)

    return f"""
    /* Master Background & Typography */
    QMainWindow, QDialog, QStackedWidget {{
        background-color: {p["bg_main"]};
    }}

    QWidget {{
        color: {p["text_main"]};
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
        font-size: 13px;
    }}

    /* Transparent Labels to eliminate sharp background rectangles behind text */
    QLabel {{
        background-color: transparent;
        color: {p["text_main"]};
    }}

    /* Card Panels & Containers with Smooth Curves */
    QFrame#cardFrame, QWidget#cardWidget {{
        background-color: {p["bg_card"]};
        border: 1px solid {p["border"]};
        border-radius: 12px;
    }}

    QFrame#elevatedCard {{
        background-color: {p["bg_elevated"]};
        border: 1px solid {p["border_light"]};
        border-radius: 10px;
    }}

    /* Sidebar Navigation */
    QWidget#sidebarWidget {{
        background-color: {p["bg_sidebar"]};
        border-right: 1px solid {p["border"]};
    }}

    QPushButton#navButton {{
        background-color: transparent;
        color: #94A3B8;
        border: none;
        border-radius: 8px;
        text-align: left;
        padding: 10px 14px;
        font-size: 13px;
        font-weight: 500;
    }}

    QPushButton#navButton:hover {{
        background-color: rgba(255, 255, 255, 0.08);
        color: #F8FAFC;
    }}

    QPushButton#navButton[active="true"] {{
        background-color: {p["primary"]};
        color: #FFFFFF;
        font-weight: 600;
    }}

    /* Header Bar */
    QWidget#headerBar {{
        background-color: {p["bg_card"]};
        border-bottom: 1px solid {p["border"]};
    }}

    /* Primary & Action Buttons */
    QPushButton#primaryButton {{
        background-color: {p["primary"]};
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton#primaryButton:hover {{
        background-color: {p["primary_hover"]};
    }}
    QPushButton#primaryButton:pressed {{
        background-color: {p["primary"]};
    }}

    QPushButton#secondaryButton {{
        background-color: {p["bg_card"]};
        color: {p["text_main"]};
        border: 1px solid {p["border"]};
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
        font-size: 13px;
    }}
    QPushButton#secondaryButton:hover {{
        background-color: {p["bg_elevated"]};
        border-color: {p["border_light"]};
    }}

    QPushButton#dangerButton {{
        background-color: {p["danger"]};
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
    }}
    QPushButton#dangerButton:hover {{
        background-color: #B91C1C;
    }}

    QPushButton#successButton {{
        background-color: {p["success"]};
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
    }}

    QPushButton#iconButton {{
        background-color: transparent;
        color: {p["text_muted"]};
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 6px;
    }}
    QPushButton#iconButton:hover {{
        background-color: {p["bg_elevated"]};
        color: {p["text_main"]};
        border-color: {p["border"]};
    }}

    /* Form Controls & Inputs */
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit, QTimeEdit {{
        background-color: {p["bg_input"]};
        color: {p["text_main"]};
        border: 1px solid {p["border"]};
        border-radius: 8px;
        padding: 8px 12px;
        selection-background-color: {p["primary"]};
    }}

    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus {{
        border: 1px solid {p["primary"]};
    }}

    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left-width: 0px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {p["bg_card"]};
        color: {p["text_main"]};
        border: 1px solid {p["border"]};
        border-radius: 8px;
        selection-background-color: {p["primary"]};
        selection-color: #FFFFFF;
        padding: 4px;
    }}

    /* List Widgets & Dialog Lists */
    QListWidget {{
        background-color: {p["bg_input"]};
        color: {p["text_main"]};
        border: 1px solid {p["border"]};
        border-radius: 8px;
        padding: 6px;
    }}
    QListWidget::item {{
        padding: 8px 10px;
        border-radius: 6px;
        margin-bottom: 2px;
        color: {p["text_main"]};
    }}
    QListWidget::item:selected {{
        background-color: {p["primary_light"]};
        color: {p["primary"]};
        font-weight: 600;
    }}

    /* Progress Bar */
    QProgressBar {{
        background-color: {p["bg_elevated"]};
        border: none;
        border-radius: 6px;
        height: 10px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {p["primary"]};
        border-radius: 6px;
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {p["border"]};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p["text_subtle"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {p["border"]};
        border-radius: 4px;
        min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {p["text_subtle"]};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* Scroll Area */
    QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
        background-color: transparent;
        background: transparent;
        border: none;
    }}

    /* Tooltips */
    QToolTip {{
        background-color: #0F172A;
        color: #F8FAFC;
        border: 1px solid #475569;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    /* Dialog styling */
    QDialog {{
        background-color: {p["bg_main"]};
    }}

    /* Custom Labels */
    QLabel#pageTitle {{
        font-size: 22px;
        font-weight: 700;
        color: {p["text_main"]};
        background: transparent;
    }}
    QLabel#pageSubtitle {{
        font-size: 13px;
        color: {p["text_muted"]};
        background: transparent;
    }}
    QLabel#sectionTitle {{
        font-size: 16px;
        font-weight: 600;
        color: {p["text_main"]};
        background: transparent;
    }}
    QLabel#statValue {{
        font-size: 26px;
        font-weight: 700;
        color: {p["text_main"]};
        background: transparent;
    }}
    QLabel#statLabel {{
        font-size: 12px;
        font-weight: 500;
        color: {p["text_muted"]};
        background: transparent;
    }}
    """
