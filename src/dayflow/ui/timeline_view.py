"""Timeline view - displays activity cards with video playback."""

import logging
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QDateEdit,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QDate

from dayflow.utils.config import Config
from dayflow.models.database import get_session_direct
from dayflow.models.timeline_activity import TimelineActivity
from dayflow.ui.widgets.activity_card import ActivityCard

logger = logging.getLogger(__name__)


class TimelineView(QWidget):
    """Timeline view showing activities for a selected date."""

    def __init__(self, config: Config):
        """
        Initialize timeline view.

        Args:
            config: Application configuration
        """
        super().__init__()
        self.config = config
        self.current_date = datetime.now().date()
        self.activity_cards = []
        self.setup_ui()
        self.load_activities()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Header with date navigator
        header = self._create_header()
        main_layout.addWidget(header)

        # Main content area: Activity cards scroll area
        self.activities_scroll = QScrollArea()
        self.activities_scroll.setWidgetResizable(True)
        self.activities_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container for activities - using QVBoxLayout with spacers
        self.activities_container = QWidget()
        # Create vertical layout for time-based positioning
        self.activities_layout = QVBoxLayout(self.activities_container)
        self.activities_layout.setContentsMargins(15, 0, 15, 0)  # Left/right margins only
        self.activities_layout.setSpacing(0)  # We'll manually control spacing with spacers

        self.activities_scroll.setWidget(self.activities_container)
        main_layout.addWidget(self.activities_scroll)

    def _create_header(self) -> QWidget:
        """Create header with date navigation."""
        header = QWidget()
        layout = QHBoxLayout(header)

        # Title
        title = QLabel("时间轴")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        layout.addStretch()

        # Date navigation
        self.prev_btn = QPushButton("◀ 前一天")
        self.prev_btn.clicked.connect(self.show_previous_day)
        layout.addWidget(self.prev_btn)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate(self.current_date))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.on_date_changed)
        layout.addWidget(self.date_edit)

        self.next_btn = QPushButton("后一天 ▶")
        self.next_btn.clicked.connect(self.show_next_day)
        layout.addWidget(self.next_btn)

        # Today button
        today_btn = QPushButton("今天")
        today_btn.clicked.connect(self.show_today)
        layout.addWidget(today_btn)

        return header

    def load_activities(self) -> None:
        """Load activities for current date and position them by time."""
        # Clear existing layout items (cards and spacers)
        while self.activities_layout.count():
            item = self.activities_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                del item
        self.activity_cards.clear()

        try:
            # Get activities from database
            session = get_session_direct()
            try:
                start_time = datetime.combine(self.current_date, datetime.min.time())
                end_time = start_time + timedelta(days=1)

                activities = (
                    session.query(TimelineActivity)
                    .filter(
                        TimelineActivity.start_time >= start_time,
                        TimelineActivity.start_time < end_time,
                    )
                    .order_by(TimelineActivity.start_time)
                    .all()
                )

                if not activities:
                    # Show empty state
                    # Add spacer to center the empty message vertically
                    self.activities_layout.addStretch(1)

                    empty_label = QLabel(
                        f"{self.current_date.strftime('%Y年%m月%d日')} 暂无记录的活动"
                    )
                    empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    empty_label.setStyleSheet("color: #7F8C8D; font-size: 16px;")
                    self.activities_layout.addWidget(empty_label)

                    self.activities_layout.addStretch(1)
                    self.activity_cards.append(empty_label)
                else:
                    # Calculate time range from activities
                    min_hour = min(a.start_time.hour for a in activities)
                    max_hour = max(a.end_time.hour for a in activities)

                    # Add buffer before and after (2 hours for better spacing)
                    start_hour = max(0, min_hour - 2)
                    end_hour = min(23, max_hour + 2)

                    # Constants for fixed spacing
                    FIXED_CARD_SPACING = 15  # Fixed spacing between all cards

                    for i, activity in enumerate(activities):
                        # Create card
                        card = ActivityCard(activity, self.config)

                        # Add spacing before card (except first card)
                        if i > 0:
                            self.activities_layout.addSpacing(FIXED_CARD_SPACING)

                        # Add card to layout
                        self.activities_layout.addWidget(card)
                        self.activity_cards.append(card)

                        logger.debug(
                            f"Card {i}: {activity.start_time.strftime('%H:%M')} - "
                            f"Fixed height with {FIXED_CARD_SPACING}px spacing"
                        )

                    # Add stretch at the end to fill remaining space
                    self.activities_layout.addStretch(1)

                logger.info(
                    f"Loaded {len(activities)} activities for {self.current_date}"
                )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error loading activities: {e}", exc_info=True)
            QMessageBox.critical(
                self, "错误", f"加载活动失败: {str(e)}"
            )

    def show_previous_day(self) -> None:
        """Show activities for previous day."""
        self.current_date -= timedelta(days=1)
        self.date_edit.setDate(QDate(self.current_date))
        self.load_activities()

    def show_next_day(self) -> None:
        """Show activities for next day."""
        self.current_date += timedelta(days=1)
        self.date_edit.setDate(QDate(self.current_date))
        self.load_activities()

    def show_today(self) -> None:
        """Show activities for today."""
        self.current_date = datetime.now().date()
        self.date_edit.setDate(QDate(self.current_date))
        self.load_activities()

    def on_date_changed(self, qdate: QDate) -> None:
        """Handle date picker change."""
        self.current_date = qdate.toPyDate()
        self.load_activities()

    def refresh(self) -> None:
        """Refresh the current view."""
        self.load_activities()
