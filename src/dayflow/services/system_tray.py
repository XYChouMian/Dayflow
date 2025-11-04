"""System tray icon and menu."""

import logging
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSignal, QObject

logger = logging.getLogger(__name__)


class SystemTrayIcon(QSystemTrayIcon):
    """System tray icon with context menu."""

    # Signals
    show_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    toggle_recording_requested = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize system tray icon."""
        super().__init__(parent)

        self.is_recording = False
        self.setup_menu()
        self.setup_icon()

        # Connect activated signal
        self.activated.connect(self.on_activated)

        logger.info("System tray icon initialized")

    def setup_icon(self) -> None:
        """Set up tray icon."""
        # For now, use default icon
        # TODO: Add custom icon
        self.setToolTip("Dayflow - 自动时间轴")

    def setup_menu(self) -> None:
        """Set up context menu."""
        menu = QMenu()

        # Show/Hide window
        self.show_action = QAction("显示窗口", self)
        self.show_action.triggered.connect(self.show_window_requested.emit)
        menu.addAction(self.show_action)

        menu.addSeparator()

        # Toggle recording
        self.recording_action = QAction("▶ 开始录制", self)
        self.recording_action.triggered.connect(self._toggle_recording)
        menu.addAction(self.recording_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction("退出 Dayflow", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _toggle_recording(self) -> None:
        """Toggle recording state."""
        self.is_recording = not self.is_recording
        self.update_recording_state(self.is_recording)
        self.toggle_recording_requested.emit()

    def update_recording_state(self, is_recording: bool) -> None:
        """
        Update tray icon and menu to reflect recording state.

        Args:
            is_recording: Whether recording is active
        """
        self.is_recording = is_recording

        if is_recording:
            self.recording_action.setText("⏸ 暂停录制")
            self.setToolTip("Dayflow - 正在录制")
        else:
            self.recording_action.setText("▶ 开始录制")
            self.setToolTip("Dayflow - 已暂停")

    def on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window_requested.emit()

    def show_message(self, title: str, message: str, duration: int = 3000) -> None:
        """
        Show balloon message.

        Args:
            title: Message title
            message: Message text
            duration: Display duration in milliseconds
        """
        self.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            duration,
        )
