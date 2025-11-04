"""Heatmap widget for productivity visualization."""

import logging
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from dayflow.ui.theme import Theme

logger = logging.getLogger(__name__)


class HeatmapWidget(QWidget):
    """Heatmap showing productivity over time blocks."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(Theme.spacing_sm)

        # Title
        title = QLabel("生产力时间块")
        title.setStyleSheet(f"""
            font-size: {Theme.font_size_h3}px;
            font-weight: 600;
            color: {Theme.colors.text_primary};
            margin-bottom: {Theme.spacing_sm}px;
        """)
        layout.addWidget(title)

        # Grid for heatmap
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(4)
        layout.addLayout(self.grid_layout)

        # Add stretch
        layout.addStretch()

    def update_data(self, productivity_data: dict):
        """
        Update heatmap with productivity data.

        Args:
            productivity_data: Dict mapping (day, hour) to productivity score (0-100)
        """
        # Clear existing widgets
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create heatmap blocks (7 days x 24 hours)
        for day in range(7):
            for hour in range(24):
                score = productivity_data.get((day, hour), 0)
                block = self._create_block(score)
                self.grid_layout.addWidget(block, day, hour)

    def _create_block(self, score: int) -> QWidget:
        """Create a single heatmap block."""
        block = QWidget()
        block.setFixedSize(12, 12)

        # Color intensity based on score
        if score == 0:
            color = "#F5F5F5"
        elif score < 25:
            color = "#FFE5CC"
        elif score < 50:
            color = "#FFCF9F"
        elif score < 75:
            color = "#FFB84D"
        else:
            color = "#FF8A4D"

        block.setStyleSheet(f"""
            background-color: {color};
            border-radius: 2px;
        """)
        block.setToolTip(f"生产力: {score}%")

        return block
