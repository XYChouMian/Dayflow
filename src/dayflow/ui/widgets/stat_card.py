"""Modern statistics card widget."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt

from dayflow.ui.theme import Theme


class StatCard(QFrame):
    """Modern card displaying a single statistic."""

    def __init__(
        self,
        title: str,
        value: str,
        gradient_start: str = None,
        gradient_end: str = None,
        parent=None
    ):
        super().__init__(parent)
        self.title_text = title
        self.value_text = value
        self.gradient_start = gradient_start or Theme.colors.gradient_orange_start
        self.gradient_end = gradient_end or Theme.colors.gradient_orange_end
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface."""
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setFixedHeight(140)

        # Modern card with gradient background
        self.setStyleSheet(f"""
            StatCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.gradient_start}, stop:1 {self.gradient_end});
                border-radius: {Theme.radius_lg}px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Theme.spacing_lg, Theme.spacing_lg,
                                  Theme.spacing_lg, Theme.spacing_lg)
        layout.setSpacing(Theme.spacing_sm)

        # Title
        title = QLabel(self.title_text)
        title.setStyleSheet(f"""
            font-size: {Theme.font_size_small}px;
            color: rgba(255, 255, 255, 0.9);
            font-weight: 500;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        """)
        layout.addWidget(title)

        # Value
        value = QLabel(self.value_text)
        value.setStyleSheet(f"""
            font-size: {Theme.font_size_h1}px;
            color: white;
            font-weight: 700;
            line-height: 1.2;
        """)
        layout.addWidget(value)

        layout.addStretch()

    def update_value(self, new_value: str):
        """Update the displayed value."""
        self.value_text = new_value
        # Find and update the value label
        layout = self.layout()
        if layout.count() >= 2:
            value_label = layout.itemAt(1).widget()
            if isinstance(value_label, QLabel):
                value_label.setText(new_value)
