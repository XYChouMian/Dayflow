"""Timeline ruler widget - displays vertical time scale."""

import logging
from datetime import datetime, time
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTime
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

logger = logging.getLogger(__name__)


class TimelineRuler(QWidget):
    """
    Vertical timeline ruler showing 24-hour scale.

    Features:
    - Fixed width (80px)
    - Hour markers every hour (00:00 - 23:00)
    - Half-hour markers every 30 minutes
    - Current time indicator
    - Synchronized scrolling with activity cards
    """

    # Height in pixels per hour (this should match the activity layout)
    PIXELS_PER_HOUR = 80

    def __init__(self, parent=None, start_hour=0, end_hour=23):
        """
        Initialize timeline ruler.

        Args:
            parent: Parent widget
            start_hour: Starting hour to display (0-23)
            end_hour: Ending hour to display (0-23)
        """
        super().__init__(parent)
        self.setFixedWidth(80)

        # Time range to display
        self.start_hour = max(0, start_hour)
        self.end_hour = min(23, end_hour)

        # Calculate total height based on time range
        hour_range = self.end_hour - self.start_hour + 1
        total_height = hour_range * self.PIXELS_PER_HOUR
        self.setMinimumHeight(total_height)

        # Current time for indicator line
        self.current_time = datetime.now().time()

    def update_time_range(self, start_hour, end_hour):
        """
        Update the time range to display.

        Args:
            start_hour: Starting hour (0-23)
            end_hour: Ending hour (0-23)
        """
        self.start_hour = max(0, start_hour)
        self.end_hour = min(23, end_hour)

        # Recalculate height
        hour_range = self.end_hour - self.start_hour + 1
        total_height = hour_range * self.PIXELS_PER_HOUR
        self.setMinimumHeight(total_height)

        self.update()

    def paintEvent(self, event):
        """Custom paint event to draw time scale."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#F8F9FA"))

        # Draw hour markers and labels only for the specified range
        for hour in range(self.start_hour, self.end_hour + 1):
            # Calculate Y position relative to start_hour
            relative_hour = hour - self.start_hour
            y_pos = relative_hour * self.PIXELS_PER_HOUR

            # Main hour line
            pen = QPen(QColor("#BDC3C7"), 2)
            painter.setPen(pen)
            painter.drawLine(50, y_pos, 80, y_pos)

            # Hour label
            time_str = f"{hour:02d}:00"
            font = QFont("Microsoft YaHei", 9)
            painter.setFont(font)
            painter.setPen(QColor("#34495E"))
            painter.drawText(5, y_pos - 5, 45, 20, Qt.AlignmentFlag.AlignRight, time_str)

            # Half-hour marker (except for last hour in range)
            if hour < self.end_hour:
                half_hour_y = y_pos + self.PIXELS_PER_HOUR // 2
                pen = QPen(QColor("#E0E0E0"), 1)
                painter.setPen(pen)
                painter.drawLine(60, half_hour_y, 80, half_hour_y)

        # Draw current time indicator
        self._draw_current_time_indicator(painter)

    def _draw_current_time_indicator(self, painter):
        """Draw a line indicating current time if within visible range."""
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute

        # Only draw if current time is within the visible range
        if current_hour < self.start_hour or current_hour > self.end_hour:
            return

        # Calculate Y position relative to start_hour
        relative_hour = current_hour - self.start_hour
        y_pos = relative_hour * self.PIXELS_PER_HOUR + (current_minute / 60) * self.PIXELS_PER_HOUR

        # Draw red indicator line
        pen = QPen(QColor("#E74C3C"), 2)
        painter.setPen(pen)
        painter.drawLine(0, int(y_pos), 80, int(y_pos))

        # Draw current time label
        time_str = f"{current_hour:02d}:{current_minute:02d}"
        font = QFont("Microsoft YaHei", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#E74C3C"))

        # Background for label
        painter.fillRect(2, int(y_pos) - 10, 46, 16, QColor("#FFE8E5"))
        painter.drawText(2, int(y_pos) - 10, 46, 16, Qt.AlignmentFlag.AlignCenter, time_str)

    def update_current_time(self):
        """Update current time and repaint."""
        self.current_time = datetime.now().time()
        self.update()

    def get_y_position_for_time(self, time_obj: time) -> int:
        """
        Calculate Y position for a given time.

        Args:
            time_obj: time object

        Returns:
            Y position in pixels
        """
        hour = time_obj.hour
        minute = time_obj.minute
        return int(hour * self.PIXELS_PER_HOUR + (minute / 60) * self.PIXELS_PER_HOUR)
