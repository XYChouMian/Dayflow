"""Dashboard view - statistics and productivity metrics."""

import logging
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QFrame,
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from dayflow.utils.config import Config
from dayflow.models.database import get_session_direct
from dayflow.models.timeline_activity import TimelineActivity
from sqlalchemy import func

logger = logging.getLogger(__name__)


class DashboardView(QWidget):
    """Dashboard showing productivity statistics and trends."""

    def __init__(self, config: Config):
        """
        Initialize dashboard view.

        Args:
            config: Application configuration
        """
        super().__init__()
        self.config = config
        self.setup_ui()
        self.load_stats()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title = QLabel("仪表盘")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # Stats cards
        stats_layout = QGridLayout()
        stats_layout.setSpacing(15)

        self.total_time_card = self._create_stat_card("今日总时长", "0小时 0分钟")
        stats_layout.addWidget(self.total_time_card, 0, 0)

        self.activities_card = self._create_stat_card("今日活动数", "0")
        stats_layout.addWidget(self.activities_card, 0, 1)

        self.productive_time_card = self._create_stat_card("工作时长", "0小时 0分钟")
        stats_layout.addWidget(self.productive_time_card, 0, 2)

        layout.addLayout(stats_layout)

        # Chart area
        chart_label = QLabel("每周活动统计")
        chart_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(chart_label)

        self.chart = TimeChart()
        layout.addWidget(self.chart)

        layout.addStretch()

    def _create_stat_card(self, title: str, value: str) -> QFrame:
        """Create a statistics card."""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        card.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border: 1px solid #BDC3C7;
                border-radius: 8px;
                padding: 20px;
            }
        """
        )

        layout = QVBoxLayout(card)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; color: #7F8C8D;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #2C3E50;")
        layout.addWidget(value_label)

        return card

    def load_stats(self) -> None:
        """Load and display statistics."""
        try:
            session = get_session_direct()
            try:
                # Today's stats
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)

                activities_today = (
                    session.query(TimelineActivity)
                    .filter(
                        TimelineActivity.start_time >= today_start,
                        TimelineActivity.start_time < today_end,
                    )
                    .all()
                )

                # Calculate total time
                total_minutes = sum(a.duration_minutes for a in activities_today)
                hours = int(total_minutes // 60)
                minutes = int(total_minutes % 60)

                # Update cards
                self._update_card_value(self.total_time_card, f"{hours}小时 {minutes}分钟")
                self._update_card_value(self.activities_card, str(len(activities_today)))

                # Calculate productive time (supports both Chinese and English)
                from dayflow.ui.theme import Theme
                productive = [
                    a for a in activities_today
                    if a.category and Theme.is_productive_category(a.category.name)
                ]
                prod_minutes = sum(a.duration_minutes for a in productive)
                prod_hours = int(prod_minutes // 60)
                prod_mins = int(prod_minutes % 60)
                self._update_card_value(self.productive_time_card, f"{prod_hours}小时 {prod_mins}分钟")

                # Load chart data
                self.chart.update_data(self._get_weekly_data(session))

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error loading stats: {e}", exc_info=True)

    def _update_card_value(self, card: QFrame, value: str) -> None:
        """Update stat card value."""
        value_label = card.findChild(QLabel, "value")
        if value_label:
            value_label.setText(value)

    def _get_weekly_data(self, session) -> dict:
        """Get activity data for the past week."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        activities = (
            session.query(TimelineActivity)
            .filter(TimelineActivity.start_time >= start_date)
            .all()
        )

        # Group by category
        category_times = {}
        for activity in activities:
            if activity.category:
                cat_name = activity.category.name
                if cat_name not in category_times:
                    category_times[cat_name] = 0
                category_times[cat_name] += activity.duration_minutes

        return category_times


class TimeChart(FigureCanvasQTAgg):
    """Matplotlib chart widget for time visualization."""

    def __init__(self):
        self.figure = Figure(figsize=(8, 4))
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot(111)

    def update_data(self, data: dict) -> None:
        """
        Update chart with new data.

        Args:
            data: Dictionary of category -> minutes
        """
        self.axes.clear()

        if not data:
            self.axes.text(
                0.5, 0.5, "暂无数据",
                horizontalalignment='center',
                verticalalignment='center'
            )
        else:
            categories = list(data.keys())
            hours = [data[cat] / 60 for cat in categories]

            self.axes.barh(categories, hours, color='#3498DB')
            self.axes.set_xlabel("小时")
            self.axes.set_title("每周活动分布")
            self.axes.grid(axis='x', alpha=0.3)

        self.figure.tight_layout()
        self.draw()

    def refresh(self) -> None:
        """Refresh the view."""
        self.load_stats()
