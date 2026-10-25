"""
StudyFlow Vector Chart Widgets
High-DPI antialiased charts drawn with QPainter:
- CompletionTrendChart (Bar chart of daily task completions)
- CategoryDonutChart (Donut chart of category distribution)
- DayOfWeekHeatmap (Day-by-day productivity breakdown)
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QLinearGradient, QPainterPath
)


def _is_dark_theme(widget: QWidget) -> bool:
    """Helper to detect whether the widget is rendered in dark mode."""
    bg_col = widget.palette().window().color()
    # If lightness is below 128, it's dark theme
    return bg_col.lightness() < 128


class CompletionTrendChart(QWidget):
    """Modern Bar Chart displaying daily task completion trend."""

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.data: List[Dict[str, Any]] = data or []
        self.setMinimumHeight(220)

    def set_data(self, data: List[Dict[str, Any]]):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        is_dark = _is_dark_theme(self)
        text_color = QColor("#F8FAFC" if is_dark else "#0F172A")
        muted_color = QColor("#94A3B8" if is_dark else "#64748B")
        grid_color = QColor("#334155" if is_dark else "#E2E8F0")
        total_bar_color = QColor("#334155" if is_dark else "#E2E8F0")

        w = self.width()
        h = self.height()

        padding_left = 35
        padding_right = 20
        padding_top = 30
        padding_bottom = 35

        chart_w = w - padding_left - padding_right
        chart_h = h - padding_top - padding_bottom

        if not self.data:
            painter.setPen(muted_color)
            painter.drawText(self.rect(), Qt.AlignCenter, "No completion data available yet")
            return

        # Find max value for Y axis scaling
        max_val = max([d.get("total", 0) for d in self.data] + [5])
        max_val = max(max_val, 4)

        # Draw Grid Lines
        grid_pen = QPen(grid_color, 1, Qt.DashLine)
        painter.setPen(grid_pen)
        painter.setFont(QFont("Segoe UI", 9))

        steps = 4
        for i in range(steps + 1):
            y_val = int(max_val * i / steps)
            y_pos = padding_top + chart_h - (chart_h * (i / steps))
            painter.drawLine(int(padding_left), int(y_pos), int(w - padding_right), int(y_pos))

            # Y-axis Label
            painter.setPen(muted_color)
            painter.drawText(0, int(y_pos - 8), int(padding_left - 8), 16, Qt.AlignRight | Qt.AlignVCenter, str(y_val))
            painter.setPen(grid_pen)

        # Draw Bars
        n = len(self.data)
        slot_w = chart_w / n
        bar_w = min(max(slot_w * 0.55, 8.0), 28.0)

        for i, item in enumerate(self.data):
            total = item.get("total", 0)
            completed = item.get("completed", 0)

            x_center = padding_left + (i + 0.5) * slot_w
            x_left = x_center - bar_w / 2

            # Background bar (Total)
            if total > 0:
                total_bar_h = (total / max_val) * chart_h
                total_y = padding_top + chart_h - total_bar_h

                bg_path = QPainterPath()
                bg_path.addRoundedRect(QRectF(x_left, total_y, bar_w, total_bar_h), 5, 5)
                painter.fillPath(bg_path, QBrush(total_bar_color))

            # Foreground bar (Completed)
            if completed > 0:
                comp_bar_h = (completed / max_val) * chart_h
                comp_y = padding_top + chart_h - comp_bar_h

                grad = QLinearGradient(x_left, comp_y, x_left, padding_top + chart_h)
                grad.setColorAt(0, QColor("#6366F1"))
                grad.setColorAt(1, QColor("#4F46E5"))

                comp_path = QPainterPath()
                comp_path.addRoundedRect(QRectF(x_left, comp_y, bar_w, comp_bar_h), 5, 5)
                painter.fillPath(comp_path, QBrush(grad))

                # Value text on top
                painter.setPen(text_color)
                painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
                painter.drawText(
                    QRectF(x_left - 10, comp_y - 16, bar_w + 20, 14),
                    Qt.AlignCenter,
                    str(completed)
                )

            # X-axis label (Day / Date)
            painter.setPen(muted_color)
            painter.setFont(QFont("Segoe UI", 9))
            lbl = item.get("day_name", "") or item.get("short_date", "")
            painter.drawText(
                QRectF(x_center - slot_w / 2, padding_top + chart_h + 8, slot_w, 20),
                Qt.AlignCenter,
                lbl
            )


class CategoryDonutChart(QWidget):
    """Crisp Donut Chart displaying distribution of tasks by category."""

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.data: List[Dict[str, Any]] = data or []
        self.setMinimumHeight(220)

    def set_data(self, data: List[Dict[str, Any]]):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        is_dark = _is_dark_theme(self)
        card_bg = QColor("#1E293B" if is_dark else "#FFFFFF")
        text_color = QColor("#F8FAFC" if is_dark else "#0F172A")
        muted_color = QColor("#94A3B8" if is_dark else "#64748B")

        w = self.width()
        h = self.height()

        if not self.data:
            painter.setPen(muted_color)
            painter.drawText(self.rect(), Qt.AlignCenter, "No category data available")
            return

        total_completions = sum(item.get("count", 0) for item in self.data)
        if total_completions == 0:
            painter.setPen(muted_color)
            painter.drawText(self.rect(), Qt.AlignCenter, "No completions recorded yet")
            return

        # Layout: Donut on Left, Legend on Right
        donut_size = min(w * 0.45, h * 0.85, 180.0)
        center_x = donut_size / 2 + 20
        center_y = h / 2

        rect = QRectF(center_x - donut_size / 2, center_y - donut_size / 2, donut_size, donut_size)

        # Draw slices
        start_angle = 90.0 * 16
        hole_ratio = 0.62

        for item in self.data:
            count = item.get("count", 0)
            if count <= 0:
                continue

            span_angle = -(count / total_completions) * 360.0 * 16
            color = QColor(item.get("color", "#6366F1"))

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawPie(rect, int(start_angle), int(span_angle))

            start_angle += span_angle

        # Draw Center Hole for Donut effect (matching card background color!)
        hole_size = donut_size * hole_ratio
        hole_rect = QRectF(center_x - hole_size / 2, center_y - hole_size / 2, hole_size, hole_size)

        painter.setBrush(QBrush(card_bg))
        painter.drawEllipse(hole_rect)

        # Center Text (Total count)
        painter.setPen(text_color)
        painter.setFont(QFont("Segoe UI", 13, QFont.Bold))
        painter.drawText(hole_rect, Qt.AlignCenter, f"{total_completions}\nDone")

        # Draw Legend on Right
        legend_x = center_x + donut_size / 2 + 30
        legend_y = max(15, int((h - len(self.data[:6]) * 26) / 2))

        painter.setFont(QFont("Segoe UI", 9))
        for item in self.data[:6]:
            color = QColor(item.get("color", "#6366F1"))
            name = item.get("name", "Other")
            pct = item.get("percentage", 0)

            # Color rounded pill
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRectF(legend_x, legend_y + 4, 10, 10), 3, 3)

            # Text
            painter.setPen(text_color)
            text = f"{name}: {pct}% ({item.get('count', 0)})"
            painter.drawText(QRectF(legend_x + 18, legend_y, w - legend_x - 25, 20), Qt.AlignLeft | Qt.AlignVCenter, text)

            legend_y += 26


class DayOfWeekHeatmap(QWidget):
    """Displays 7-day productivity comparison with highlight on most productive day."""

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.data: List[Dict[str, Any]] = data or []
        self.setMinimumHeight(140)

    def set_data(self, data: List[Dict[str, Any]]):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        is_dark = _is_dark_theme(self)
        card_bg = QColor("#1E293B" if is_dark else "#FFFFFF")
        card_border = QColor("#334155" if is_dark else "#CBD5E1")
        text_color = QColor("#F8FAFC" if is_dark else "#0F172A")
        muted_color = QColor("#94A3B8" if is_dark else "#64748B")

        w = self.width()
        h = self.height()

        if not self.data:
            painter.setPen(muted_color)
            painter.drawText(self.rect(), Qt.AlignCenter, "No weekly activity data")
            return

        max_count = max([d.get("count", 0) for d in self.data] + [1])
        n = len(self.data)
        margin = 12
        card_w = (w - (n + 1) * margin) / n
        card_h = h - 30

        for i, item in enumerate(self.data):
            x = margin + i * (card_w + margin)
            y = 10
            count = item.get("count", 0)
            is_top = (count == max_count and count > 0)

            # Background Box with smooth curves
            card_rect = QRectF(x, y, card_w, card_h)
            path = QPainterPath()
            path.addRoundedRect(card_rect, 10, 10)

            if is_top:
                painter.fillPath(path, QBrush(QColor("rgba(99, 102, 241, 0.18)")))
                painter.setPen(QPen(QColor("#6366F1"), 1.5))
                painter.drawPath(path)
            else:
                painter.fillPath(path, QBrush(card_bg))
                painter.setPen(QPen(card_border, 1))
                painter.drawPath(path)

            # Day Name
            painter.setPen(muted_color)
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            painter.drawText(QRectF(x, y + 10, card_w, 18), Qt.AlignCenter, item.get("short_name", ""))

            # Count
            painter.setPen(QColor("#6366F1" if is_top else text_color))
            painter.setFont(QFont("Segoe UI", 14, QFont.Bold))
            painter.drawText(QRectF(x, y + 34, card_w, 24), Qt.AlignCenter, str(count))

            # Subtitle or Trophy
            painter.setFont(QFont("Segoe UI", 8))
            if is_top:
                painter.setPen(QColor("#F59E0B"))
                painter.drawText(QRectF(x, y + card_h - 22, card_w, 16), Qt.AlignCenter, "★ Best")
            else:
                painter.setPen(muted_color)
                painter.drawText(QRectF(x, y + card_h - 22, card_w, 16), Qt.AlignCenter, "tasks")
