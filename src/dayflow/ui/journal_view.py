"""Journal view - daily reflection and notes."""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from dayflow.utils.config import Config
from dayflow.ui.widgets.date_navigator import DateNavigator

logger = logging.getLogger(__name__)


class JournalView(QWidget):
    """Journal view for daily reflections and notes."""

    def __init__(self, config: Config):
        """
        Initialize journal view.

        Args:
            config: Application configuration
        """
        super().__init__()
        self.config = config
        self.current_date = datetime.now()
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("日志")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Date navigator
        self.date_nav = DateNavigator(self.current_date)
        self.date_nav.date_changed.connect(self.load_entry)
        header_layout.addWidget(self.date_nav)

        layout.addLayout(header_layout)

        # Date label
        self.date_label = QLabel(self.current_date.strftime("%Y年%m月%d日 %A"))
        self.date_label.setStyleSheet("font-size: 16px; color: #7F8C8D;")
        layout.addWidget(self.date_label)

        # Reflection prompts
        prompts_label = QLabel("💭 反思提示：")
        prompts_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(prompts_label)

        self.prompts_text = QLabel(
            "• 今天完成了什么？\n"
            "• 遇到了什么挑战？\n"
            "• 有什么值得感恩的事情？"
        )
        self.prompts_text.setStyleSheet("color: #95A5A6; margin-left: 10px;")
        layout.addWidget(self.prompts_text)

        # Text editor
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("记录今天的想法...")
        self.editor.setStyleSheet(
            """
            QTextEdit {
                border: 1px solid #BDC3C7;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.6;
            }
        """
        )
        layout.addWidget(self.editor)

        # Save button
        save_btn = QPushButton("💾 保存条目")
        save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """
        )
        save_btn.clicked.connect(self.save_entry)
        layout.addWidget(save_btn)

    def load_entry(self, date: datetime) -> None:
        """
        Load journal entry for date.

        Args:
            date: Date to load
        """
        self.current_date = date
        self.date_label.setText(date.strftime("%Y年%m月%d日 %A"))

        # TODO: Load from database
        # For now, just clear the editor
        self.editor.clear()

    def save_entry(self) -> None:
        """Save current journal entry."""
        content = self.editor.toPlainText()

        if not content.strip():
            QMessageBox.warning(
                self, "空白条目", "请在保存前写入一些内容。"
            )
            return

        try:
            # TODO: Save to database
            logger.info(f"Saved journal entry for {self.current_date.date()}")

            QMessageBox.information(
                self, "已保存", "日记条目保存成功！"
            )

        except Exception as e:
            logger.error(f"Error saving journal: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"保存条目失败：{str(e)}")

    def refresh(self) -> None:
        """Refresh the view."""
        self.load_entry(self.current_date)
