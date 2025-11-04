"""Modern dashboard view with rich visualizations."""

import logging
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QFrame,
    QScrollArea,
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib as mpl

from dayflow.utils.config import Config
from dayflow.models.database import get_session_direct
from dayflow.models.timeline_activity import TimelineActivity
from dayflow.ui.theme import Theme
from dayflow.ui.widgets.stat_card import StatCard

logger = logging.getLogger(__name__)

# Configure matplotlib to use Chinese fonts
try:
    # Try to use Microsoft YaHei first (Windows)
    mpl.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    mpl.rcParams['axes.unicode_minus'] = False  # Fix minus sign display
except Exception as e:
    logger.warning(f"Failed to set Chinese font for matplotlib: {e}")


class ModernDashboardView(QWidget):
    """Modern dashboard with comprehensive statistics and trends."""

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.setup_ui()
        self.load_stats()

    def setup_ui(self):
        """Set up the user interface."""
        # Main layout with padding
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(Theme.spacing_xl, Theme.spacing_xl,
                                      Theme.spacing_xl, Theme.spacing_xl)
        main_layout.setSpacing(Theme.spacing_lg)

        # Header
        header = self._create_header()
        main_layout.addWidget(header)

        # Stats cards row - 3 cards in a row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(Theme.spacing_md)

        self.total_time_card = StatCard(
            "今日总时长",
            "0小时",
            Theme.colors.gradient_orange_start,
            Theme.colors.gradient_orange_end
        )
        stats_layout.addWidget(self.total_time_card)

        self.productive_time_card = StatCard(
            "工作时长",
            "0小时",
            Theme.colors.gradient_blue_start,
            Theme.colors.gradient_blue_end
        )
        stats_layout.addWidget(self.productive_time_card)

        self.focus_score_card = StatCard(
            "专注度",
            "0%",
            Theme.colors.gradient_purple_start,
            Theme.colors.gradient_purple_end
        )
        stats_layout.addWidget(self.focus_score_card)

        main_layout.addLayout(stats_layout)

        # Charts row - 2 charts side by side
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(Theme.spacing_md)

        # Weekly trend (line chart)
        trend_widget = self._create_chart_card("每周活动趋势", 350)
        self.trend_canvas = FigureCanvasQTAgg(Figure(figsize=(6, 4), facecolor='none'))
        trend_layout = trend_widget.layout()
        trend_layout.addWidget(self.trend_canvas)
        charts_layout.addWidget(trend_widget, stretch=1)

        # Category breakdown (horizontal bar chart)
        category_widget = self._create_chart_card("活动分类统计", 350)
        self.category_canvas = FigureCanvasQTAgg(Figure(figsize=(6, 4), facecolor='none'))
        category_layout = category_widget.layout()
        category_layout.addWidget(self.category_canvas)
        charts_layout.addWidget(category_widget, stretch=1)

        main_layout.addLayout(charts_layout)

        main_layout.addStretch()

    def _create_header(self) -> QWidget:
        """Create dashboard header."""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("仪表盘")
        title.setStyleSheet(f"""
            font-size: {Theme.font_size_h1}px;
            font-weight: 700;
            color: {Theme.colors.text_primary};
        """)
        layout.addWidget(title)

        layout.addStretch()

        # Date label
        date_label = QLabel(datetime.now().strftime("%Y年%m月%d日"))
        date_label.setStyleSheet(f"""
            font-size: {Theme.font_size_body}px;
            color: {Theme.colors.text_secondary};
        """)
        layout.addWidget(date_label)

        return header

    def _create_chart_card(self, title: str, min_height: int = 200) -> QFrame:
        """Create a card container for charts."""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.NoFrame)
        card.setMinimumHeight(min_height)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.colors.bg_card};
                border-radius: {Theme.radius_lg}px;
                border: 1px solid rgba(0, 0, 0, 0.06);
                padding: {Theme.spacing_lg}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(Theme.spacing_md)

        # Chart title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: {Theme.font_size_h3}px;
            font-weight: 600;
            color: {Theme.colors.text_primary};
        """)
        layout.addWidget(title_label)

        return card

    def load_stats(self):
        """Load and display statistics."""
        try:
            session = get_session_direct()
            try:
                # Get today's activities
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)

                activities = (
                    session.query(TimelineActivity)
                    .filter(
                        TimelineActivity.start_time >= today_start,
                        TimelineActivity.start_time < today_end,
                    )
                    .all()
                )

                # Update stat cards
                self._update_stat_cards(activities)

                # Update charts
                self._update_trend_chart(session)
                self._update_category_chart(activities)

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error loading stats: {e}", exc_info=True)

    def _update_stat_cards(self, activities):
        """Update statistic cards with robust error handling."""
        # Total time
        total_minutes = sum(a.duration_minutes for a in activities) if activities else 0
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)

        if hours > 0:
            self.total_time_card.update_value(f"{hours}小时")
        else:
            self.total_time_card.update_value(f"{minutes}分钟" if minutes > 0 else "0小时")

        # Productive time (supports both Chinese and English category names)
        productive = [
            a for a in activities
            if a.category and Theme.is_productive_category(a.category.name)
        ] if activities else []

        prod_minutes = sum(a.duration_minutes for a in productive) if productive else 0
        prod_hours = int(prod_minutes // 60)
        prod_mins = int(prod_minutes % 60)

        if prod_hours > 0:
            self.productive_time_card.update_value(f"{prod_hours}小时")
        else:
            self.productive_time_card.update_value(f"{prod_mins}分钟" if prod_mins > 0 else "0小时")

        # Focus score (simple calculation: productive time / total time)
        focus = int((prod_minutes / total_minutes * 100) if total_minutes > 0 else 0)
        self.focus_score_card.update_value(f"{focus}%")


    def _update_trend_chart(self, session):
        """Update weekly trend line chart."""
        # Get last 7 days data
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=6)

        daily_data = []
        dates = []

        for i in range(7):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)

            activities = (
                session.query(TimelineActivity)
                .filter(
                    TimelineActivity.start_time >= day_start,
                    TimelineActivity.start_time < day_end,
                )
                .all()
            )

            total_minutes = sum(a.duration_minutes for a in activities)
            daily_data.append(total_minutes / 60)  # Convert to hours
            dates.append(day_start.strftime("%m/%d"))

        # Create line chart with modern style
        fig = self.trend_canvas.figure
        fig.clear()
        fig.patch.set_alpha(0)  # Transparent background
        ax = fig.add_subplot(111)
        ax.patch.set_alpha(0)  # Transparent axes background

        if daily_data and any(d > 0 for d in daily_data):
            ax.plot(dates, daily_data, color=Theme.colors.gradient_blue_end,
                    linewidth=3, marker='o', markersize=8,
                    markerfacecolor='white', markeredgewidth=2,
                    markeredgecolor=Theme.colors.gradient_blue_end)
            ax.fill_between(range(len(dates)), daily_data, alpha=0.2,
                             color=Theme.colors.gradient_blue_start)
            ax.set_ylabel('小时', fontsize=11)
            ax.grid(True, alpha=0.15, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#E0E0E0')
            ax.spines['bottom'].set_color('#E0E0E0')
        else:
            # Show empty state
            ax.text(0.5, 0.5, '暂无数据',
                   ha='center', va='center', fontsize=14,
                   color=Theme.colors.text_secondary,
                   transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)

        fig.tight_layout(pad=1.5)
        self.trend_canvas.draw()


    def _update_category_chart(self, activities):
        """Update category breakdown bar chart."""
        # Group by category (translate to Chinese for display)
        category_time = {}
        for activity in activities:
            cat_name = activity.category.name if activity.category else "其他"
            # Translate to Chinese for consistent display
            cat_display = Theme.translate_category_to_chinese(cat_name)
            category_time[cat_display] = category_time.get(cat_display, 0) + activity.duration_minutes

        # Create bar chart with modern style
        fig = self.category_canvas.figure
        fig.clear()
        fig.patch.set_alpha(0)  # Transparent background
        ax = fig.add_subplot(111)
        ax.patch.set_alpha(0)  # Transparent axes background

        if category_time:
            categories = list(category_time.keys())
            values = [v / 60 for v in category_time.values()]  # Convert to hours
            colors = [Theme.get_category_color(cat) for cat in categories]

            bars = ax.barh(categories, values, color=colors, alpha=0.85, height=0.6)
            ax.set_xlabel('小时', fontsize=11)
            ax.grid(True, axis='x', alpha=0.15, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#E0E0E0')
            ax.spines['bottom'].set_color('#E0E0E0')

            # Add value labels on bars
            for i, (bar, value) in enumerate(zip(bars, values)):
                if value > 0:
                    ax.text(value, i, f' {value:.1f}h',
                           va='center', fontsize=9,
                           color=Theme.colors.text_secondary)
        else:
            # Show empty state
            ax.text(0.5, 0.5, '暂无数据',
                   ha='center', va='center', fontsize=14,
                   color=Theme.colors.text_secondary,
                   transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)

        fig.tight_layout(pad=1.5)
        self.category_canvas.draw()
