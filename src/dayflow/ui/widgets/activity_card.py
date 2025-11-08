"""Activity card widget - displays individual activity with video."""

import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from dayflow.utils.config import Config
from dayflow.models.timeline_activity import TimelineActivity
from dayflow.ui.widgets.video_player import VideoPlayer
from dayflow.ui.theme import Theme

logger = logging.getLogger(__name__)


class ActivityCard(QFrame):
    """
    Card widget displaying a single timeline activity.
    Includes title, time, summary, category, and video player.
    """

    deleted = pyqtSignal()  # Emitted when card is deleted

    def __init__(self, activity: TimelineActivity, config: Config):
        """
        Initialize activity card.

        Args:
            activity: TimelineActivity model instance
            config: Application configuration
        """
        super().__init__()
        self.activity = activity
        self.config = config
        self.is_expanded = False

        # Calculate dynamic height based on duration
        self.card_height = self._calculate_card_height()
        self.display_mode = self._determine_display_mode()

        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        self.setFrameStyle(QFrame.Shape.NoFrame)

        # Set dynamic height
        self.setMinimumHeight(self.card_height)
        if not self.is_expanded:
            self.setMaximumHeight(self.card_height)

        # Modern card style with shadow and gradient accent
        category_color = Theme.get_category_color(
            self.activity.category.name if self.activity.category else "其他"
        )

        self.setStyleSheet(f"""
            ActivityCard {{
                background-color: {Theme.colors.bg_card};
                border-radius: {Theme.radius_lg}px;
                border: 1px solid rgba(0, 0, 0, 0.06);
                border-left: 8px solid {category_color};
            }}
            ActivityCard:hover {{
                border: 1px solid {category_color};
                border-left: 8px solid {category_color};
                background-color: #FAFBFC;
            }}
        """
        )

        layout = QVBoxLayout(self)
        # Adjust margins for compact mode
        margin = 8 if self.display_mode == "compact" else 15
        spacing = 5 if self.display_mode == "compact" else 10
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(spacing)

        # Header row
        header_layout = QHBoxLayout()

        # Time range
        time_label = QLabel(self._format_time_range())
        font_size = "10px" if self.display_mode == "compact" else "12px"
        time_label.setStyleSheet(f"color: #7F8C8D; font-weight: bold; font-size: {font_size};")
        header_layout.addWidget(time_label)

        # Duration (only in standard mode)
        if self.display_mode == "standard":
            duration_label = QLabel(f"{self.activity.duration_minutes:.0f} 分钟")
            duration_label.setStyleSheet("color: #95A5A6;")
            header_layout.addWidget(duration_label)

        header_layout.addStretch()

        # Expand/collapse button (always shown for click-to-expand)
        self.expand_btn = QPushButton("▼" if self.display_mode == "standard" else "...")
        self.expand_btn.setFlat(True)
        self.expand_btn.setStyleSheet(f"font-size: {'10px' if self.display_mode == 'compact' else '12px'};")
        self.expand_btn.clicked.connect(self.toggle_expand)
        header_layout.addWidget(self.expand_btn)

        layout.addLayout(header_layout)

        # Title
        title_label = QLabel(self.activity.title)
        title_font = QFont()
        if self.display_mode == "compact":
            title_font.setPointSize(11)
            title_font.setBold(True)
            # Truncate title in compact mode
            if len(self.activity.title) > 40:
                title_label.setText(self.activity.title[:37] + "...")
        else:
            title_font.setPointSize(14)
            title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Summary preview (only in standard mode)
        if self.display_mode == "standard":
            summary_preview = self.activity.summary[:150]
            if len(self.activity.summary) > 150:
                summary_preview += "..."

            self.summary_label = QLabel(summary_preview)
            self.summary_label.setWordWrap(True)
            self.summary_label.setStyleSheet("color: #34495E;")
            layout.addWidget(self.summary_label)
        else:
            # In compact mode, summary_label is None
            self.summary_label = None

        # Expandable content (initially hidden)
        self.expanded_content = QWidget()
        self.expanded_content.hide()
        expanded_layout = QVBoxLayout(self.expanded_content)
        expanded_layout.setContentsMargins(0, 10, 0, 0)

        # Full summary (when expanded)
        if len(self.activity.summary) > 150:
            self.full_summary = QTextEdit()
            self.full_summary.setPlainText(self.activity.summary)
            self.full_summary.setReadOnly(True)
            self.full_summary.setMaximumHeight(100)
            self.full_summary.setStyleSheet("border: none; background: transparent;")
            expanded_layout.addWidget(self.full_summary)

        # Video player (when expanded)
        if self.activity.timelapse_path and Path(self.activity.timelapse_path).exists():
            self.video_player = VideoPlayer(Path(self.activity.timelapse_path))
            expanded_layout.addWidget(self.video_player)
        else:
            no_video_label = QLabel("暂无延时视频")
            no_video_label.setStyleSheet("color: #95A5A6; font-style: italic;")
            no_video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            expanded_layout.addWidget(no_video_label)

        layout.addWidget(self.expanded_content)

    def _format_time_range(self) -> str:
        """Format activity time range."""
        start = self.activity.start_time.strftime("%H:%M")
        end = self.activity.end_time.strftime("%H:%M")
        return f"{start} - {end}"

    def toggle_expand(self) -> None:
        """Toggle expanded/collapsed state."""
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.expanded_content.show()
            # Remove height restriction when expanded
            self.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
            self.expand_btn.setText("▲")
            # Hide summary preview if it exists (standard mode only)
            if self.summary_label:
                self.summary_label.hide()
        else:
            self.expanded_content.hide()
            # Restore original height when collapsed
            self.setMaximumHeight(self.card_height)
            self.expand_btn.setText("▼" if self.display_mode == "standard" else "...")
            # Show summary preview if it exists (standard mode only)
            if self.summary_label:
                self.summary_label.show()

    def get_activity_id(self) -> int:
        """Get the activity database ID."""
        return self.activity.id

    def _calculate_card_height(self) -> int:
        """
        Calculate card height - fixed size for all activities.

        Returns:
            Card height in pixels (fixed at 150px)
        """
        # Fixed height for all activity cards to ensure content is always visible
        FIXED_HEIGHT = 150
        return FIXED_HEIGHT

    def _determine_display_mode(self) -> str:
        """
        Determine display mode - always use standard mode for full content display.

        Returns:
            Display mode string (always "standard")
        """
        # Always use standard mode to show full content (time, title, and summary)
        return "standard"
