"""Category badge widget - displays category with color and icon."""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

from dayflow.models.category import TimelineCategory


class CategoryBadge(QLabel):
    """Badge widget displaying category with color-coded background."""

    def __init__(self, category: TimelineCategory):
        """
        Initialize category badge.

        Args:
            category: TimelineCategory model instance
        """
        super().__init__()
        self.category = category
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        # Text: icon + name
        text = f"{self.category.icon} {self.category.name}" if self.category.icon else self.category.name
        self.setText(text)

        # Style with category color
        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {self.category.color};
                color: white;
                border-radius: 12px;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 12px;
            }}
        """
        )

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
