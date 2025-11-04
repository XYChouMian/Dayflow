"""Date navigator widget for timeline navigation."""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QDateEdit, QLabel
from PyQt6.QtCore import Qt, QDate, pyqtSignal


class DateNavigator(QWidget):
    """Widget for navigating through dates."""

    date_changed = pyqtSignal(datetime)  # Emitted when date changes

    def __init__(self, initial_date: datetime = None):
        """
        Initialize date navigator.

        Args:
            initial_date: Initial date to show (defaults to today)
        """
        super().__init__()
        self.current_date = initial_date or datetime.now()
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Previous day button
        self.prev_btn = QPushButton("◀")
        self.prev_btn.clicked.connect(self.previous_day)
        layout.addWidget(self.prev_btn)

        # Date picker
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate(self.current_date.date()))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self._on_date_edit_changed)
        layout.addWidget(self.date_edit)

        # Next day button
        self.next_btn = QPushButton("▶")
        self.next_btn.clicked.connect(self.next_day)
        layout.addWidget(self.next_btn)

        # Today button
        self.today_btn = QPushButton("今天")
        self.today_btn.clicked.connect(self.go_to_today)
        layout.addWidget(self.today_btn)

    def previous_day(self) -> None:
        """Go to previous day."""
        self.current_date -= timedelta(days=1)
        self.date_edit.setDate(QDate(self.current_date.date()))
        self.date_changed.emit(self.current_date)

    def next_day(self) -> None:
        """Go to next day."""
        self.current_date += timedelta(days=1)
        self.date_edit.setDate(QDate(self.current_date.date()))
        self.date_changed.emit(self.current_date)

    def go_to_today(self) -> None:
        """Go to today."""
        self.current_date = datetime.now()
        self.date_edit.setDate(QDate(self.current_date.date()))
        self.date_changed.emit(self.current_date)

    def _on_date_edit_changed(self, qdate: QDate) -> None:
        """Handle date edit change."""
        self.current_date = datetime.combine(qdate.toPyDate(), datetime.min.time())
        self.date_changed.emit(self.current_date)

    def get_current_date(self) -> datetime:
        """Get currently selected date."""
        return self.current_date
