"""
StudyFlow — Smart Calendar & Timetable Task Management Application
Entry Point Application Launcher
"""

import sys
import os

# Ensure the application root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.main_window import MainWindow


def main():
    """Main application execution routine."""
    # Configure high-DPI display attributes
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("StudyFlow")
    app.setOrganizationName("StudyFlow")
    app.setApplicationVersion("1.0")

    # Set default modern clean font
    app_font = QFont("Segoe UI", 10)
    app_font.setStyleHint(QFont.SansSerif)
    app.setFont(app_font)

    # Instantiate and display master window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
