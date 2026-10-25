"""
StudyFlow Productivity Analytics View (FR-10)
Comprehensive visual metrics dashboard featuring:
- Overall productivity score banner
- Key metric cards (Current Streak, Best Streak, Most Productive Day, Top Subject)
- 14-day completion trend bar chart
- Category distribution donut chart
- Day-of-week activity breakdown
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from services.stats_service import StatsService
from ui.components.stat_card import StatCard
from ui.components.chart_widgets import (
    CompletionTrendChart, CategoryDonutChart, DayOfWeekHeatmap
)


class AnalyticsView(QWidget):
    """Analytics & Productivity Statistics View."""

    def __init__(self, stats_service: StatsService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.stats_service = stats_service

        self._init_ui()
        self.refresh_analytics()

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(28, 24, 28, 24)
        self.main_layout.setSpacing(20)

        # 1. Header
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        page_title = QLabel("Productivity & Analytics")
        page_title.setObjectName("pageTitle")
        subtitle = QLabel("Track your long-term consistency, habit streaks, and subject completion trends")
        subtitle.setObjectName("pageSubtitle")
        title_box.addWidget(page_title)
        title_box.addWidget(subtitle)
        self.main_layout.addLayout(title_box)

        # 2. Overall Productivity Banner
        self.banner_frame = QFrame()
        self.banner_frame.setObjectName("cardFrame")
        b_layout = QHBoxLayout(self.banner_frame)
        b_layout.setContentsMargins(24, 20, 24, 20)

        score_box = QVBoxLayout()
        score_box.setSpacing(4)
        score_lbl = QLabel("Overall Consistency Score")
        score_lbl.setStyleSheet("color: #64748B; font-size: 13px; font-weight: 600; background: transparent;")
        self.score_val = QLabel("0%")
        self.score_val.setStyleSheet("font-size: 36px; font-weight: 800; color: #10B981; background: transparent;")
        score_desc = QLabel("Based on 14-day completion history and active habit streaks")
        score_desc.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")

        score_box.addWidget(score_lbl)
        score_box.addWidget(self.score_val)
        score_box.addWidget(score_desc)
        b_layout.addLayout(score_box)

        b_layout.addStretch()
        self.main_layout.addWidget(self.banner_frame)

        # 3. Quick Metric Cards Row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        self.card_streak = StatCard("Current Streak", "0 Days", "Consecutive active days", "🔥", "#F59E0B")
        self.card_best = StatCard("Best Streak", "0 Days", "All-time personal record", "⭐", "#EC4899")
        self.card_day = StatCard("Most Productive", "N/A", "Peak completion day", "🏆", "#6366F1")
        self.card_subj = StatCard("Top Subject", "N/A", "Most completed tasks", "📚", "#14B8A6")

        cards_row.addWidget(self.card_streak)
        cards_row.addWidget(self.card_best)
        cards_row.addWidget(self.card_day)
        cards_row.addWidget(self.card_subj)
        self.main_layout.addLayout(cards_row)

        # 4. Charts Grid (Trend Bar Chart & Category Donut Chart)
        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        # Trend Chart Card
        trend_frame = QFrame()
        trend_frame.setObjectName("cardFrame")
        tf_layout = QVBoxLayout(trend_frame)
        tf_layout.setContentsMargins(18, 16, 18, 16)
        tf_layout.setSpacing(10)
        tf_title = QLabel("14-Day Completion Trend")
        tf_title.setObjectName("sectionTitle")
        self.trend_chart = CompletionTrendChart()
        tf_layout.addWidget(tf_title)
        tf_layout.addWidget(self.trend_chart)
        charts_row.addWidget(trend_frame, stretch=3)

        # Donut Chart Card
        donut_frame = QFrame()
        donut_frame.setObjectName("cardFrame")
        df_layout = QVBoxLayout(donut_frame)
        df_layout.setContentsMargins(18, 16, 18, 16)
        df_layout.setSpacing(10)
        df_title = QLabel("Category Distribution")
        df_title.setObjectName("sectionTitle")
        self.donut_chart = CategoryDonutChart()
        df_layout.addWidget(df_title)
        df_layout.addWidget(self.donut_chart)
        charts_row.addWidget(donut_frame, stretch=2)

        self.main_layout.addLayout(charts_row)

        # 5. Day-of-the-Week Activity Heatmap
        week_frame = QFrame()
        week_frame.setObjectName("cardFrame")
        wf_layout = QVBoxLayout(week_frame)
        wf_layout.setContentsMargins(18, 16, 18, 16)
        wf_layout.setSpacing(10)
        wf_title = QLabel("Day of Week Productivity Breakdown")
        wf_title.setObjectName("sectionTitle")
        self.week_heatmap = DayOfWeekHeatmap()
        wf_layout.addWidget(wf_title)
        wf_layout.addWidget(self.week_heatmap)
        self.main_layout.addWidget(week_frame)

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

    def refresh_analytics(self):
        """Updates all statistics, scores, and charts."""
        productivity = self.stats_service.get_overall_productivity()

        # Update Score Banner
        pct = productivity["overall_percentage"]
        self.score_val.setText(f"{pct}%")
        if pct >= 80:
            self.score_val.setStyleSheet("font-size: 36px; font-weight: 800; color: #10B981; background: transparent;")
        elif pct >= 50:
            self.score_val.setStyleSheet("font-size: 36px; font-weight: 800; color: #F59E0B; background: transparent;")
        else:
            self.score_val.setStyleSheet("font-size: 36px; font-weight: 800; color: #EF4444; background: transparent;")

        # Update Cards
        self.card_streak.set_value(f"{productivity['current_streak']} Days")
        self.card_best.set_value(f"{productivity['best_streak']} Days")
        self.card_day.set_value(productivity["most_productive_day"])
        self.card_subj.set_value(productivity["top_subject"][:16] if len(productivity["top_subject"]) > 16 else productivity["top_subject"])

        # Update Charts
        trend = self.stats_service.get_completion_trend(14)
        self.trend_chart.set_data(trend)

        cat_dist = self.stats_service.get_category_distribution()
        self.donut_chart.set_data(cat_dist)

        day_analysis = self.stats_service.get_day_of_week_analysis()
        self.week_heatmap.set_data(day_analysis)
