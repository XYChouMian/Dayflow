"""Main application window."""

import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QPushButton,
    QLabel,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from dayflow.utils.config import Config
from dayflow.ui.timeline_view import TimelineView
from dayflow.ui.dashboard_view_new import ModernDashboardView
from dayflow.ui.journal_view import JournalView
from dayflow.ui.settings_view import SettingsView
from dayflow.ui.theme import Theme

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation."""

    def __init__(self, config: Config):
        """
        Initialize main window.

        Args:
            config: Application configuration
        """
        super().__init__()
        self.config = config
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Dayflow - 自动时间轴")
        self.setMinimumSize(1200, 800)

        # Set application stylesheet for modern look
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {Theme.colors.bg_primary};
            }}
            QWidget {{
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }}
        """)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create sidebar
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # Create stacked widget for views
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create views
        self.timeline_view = TimelineView(self.config)
        self.dashboard_view = ModernDashboardView(self.config)
        self.journal_view = JournalView(self.config)
        self.settings_view = SettingsView(self.config)

        # Add views to stack
        self.stacked_widget.addWidget(self.timeline_view)
        self.stacked_widget.addWidget(self.dashboard_view)
        self.stacked_widget.addWidget(self.journal_view)
        self.stacked_widget.addWidget(self.settings_view)

        # Show timeline by default
        self.show_timeline()

        logger.info("Main window initialized")

    def _create_sidebar(self) -> QWidget:
        """Create sidebar navigation."""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(Theme.get_sidebar_style())

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # App title
        title_label = QLabel("Dayflow")
        layout.addWidget(title_label)

        # Navigation buttons
        self.timeline_btn = QPushButton("📅 时间轴")
        self.timeline_btn.setCheckable(True)
        self.timeline_btn.clicked.connect(self.show_timeline)
        layout.addWidget(self.timeline_btn)

        self.dashboard_btn = QPushButton("📊 仪表盘")
        self.dashboard_btn.setCheckable(True)
        self.dashboard_btn.clicked.connect(self.show_dashboard)
        layout.addWidget(self.dashboard_btn)

        self.journal_btn = QPushButton("📝 日志")
        self.journal_btn.setCheckable(True)
        self.journal_btn.clicked.connect(self.show_journal)
        layout.addWidget(self.journal_btn)

        self.settings_btn = QPushButton("⚙️ 设置")
        self.settings_btn.setCheckable(True)
        self.settings_btn.clicked.connect(self.show_settings)
        layout.addWidget(self.settings_btn)

        layout.addStretch()

        return sidebar

    def show_timeline(self) -> None:
        """Show timeline view."""
        self.stacked_widget.setCurrentWidget(self.timeline_view)
        self._update_nav_buttons(self.timeline_btn)
        logger.debug("Switched to timeline view")

    def show_dashboard(self) -> None:
        """Show dashboard view."""
        self.stacked_widget.setCurrentWidget(self.dashboard_view)
        self._update_nav_buttons(self.dashboard_btn)
        logger.debug("Switched to dashboard view")

    def show_journal(self) -> None:
        """Show journal view."""
        self.stacked_widget.setCurrentWidget(self.journal_view)
        self._update_nav_buttons(self.journal_btn)
        logger.debug("Switched to journal view")

    def show_settings(self) -> None:
        """Show settings view."""
        self.stacked_widget.setCurrentWidget(self.settings_view)
        self._update_nav_buttons(self.settings_btn)
        logger.debug("Switched to settings view")

    def _update_nav_buttons(self, active_button: QPushButton) -> None:
        """Update navigation button states."""
        for btn in [
            self.timeline_btn,
            self.dashboard_btn,
            self.journal_btn,
            self.settings_btn,
        ]:
            btn.setChecked(btn == active_button)

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        logger.info("Main window closing")
        event.accept()
