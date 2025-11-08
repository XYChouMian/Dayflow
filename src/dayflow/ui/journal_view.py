"""Journal view - daily AI summary and user notes."""

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
    QScrollArea,
    QFrame,
)
from PyQt6.QtCore import Qt

from dayflow.utils.config import Config
from dayflow.ui.widgets.date_navigator import DateNavigator
from dayflow.services.daily_summary_service import DailySummaryService

logger = logging.getLogger(__name__)


class JournalView(QWidget):
    """Daily summary view with AI-generated summary and user notes."""

    def __init__(self, config: Config):
        """
        Initialize journal view.

        Args:
            config: Application configuration
        """
        super().__init__()
        self.config = config
        self.current_date = datetime.now()
        self.summary_service = DailySummaryService()
        self.setup_ui()
        self.load_entry(self.current_date)

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("每日总结")
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

        # AI Summary Section
        summary_header_layout = QHBoxLayout()

        summary_title = QLabel("🤖 AI 生成的总结")
        summary_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        summary_header_layout.addWidget(summary_title)

        summary_header_layout.addStretch()

        # Generate Now button
        self.generate_btn = QPushButton("⚡ 立即总结")
        self.generate_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #9B59B6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8E44AD;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
            }
        """
        )
        self.generate_btn.clicked.connect(self.generate_summary_now)
        summary_header_layout.addWidget(self.generate_btn)

        layout.addLayout(summary_header_layout)

        # AI Summary display (read-only, scrollable, large area)
        summary_scroll = QScrollArea()
        summary_scroll.setWidgetResizable(True)
        summary_scroll.setFrameShape(QFrame.Shape.NoFrame)

        summary_container = QWidget()
        summary_container_layout = QVBoxLayout(summary_container)
        summary_container_layout.setContentsMargins(0, 0, 0, 0)

        self.ai_summary_display = QTextEdit()
        self.ai_summary_display.setReadOnly(True)
        self.ai_summary_display.setPlaceholderText("暂无总结。点击'立即总结'按钮生成今天的AI总结...")
        self.ai_summary_display.setMinimumHeight(300)
        self.ai_summary_display.setStyleSheet(
            """
            QTextEdit {
                border: 2px solid #E8DAEF;
                border-radius: 10px;
                padding: 20px;
                font-size: 14px;
                line-height: 1.8;
                background-color: #F9F3FF;
            }
        """
        )
        summary_container_layout.addWidget(self.ai_summary_display)
        summary_scroll.setWidget(summary_container)

        layout.addWidget(summary_scroll, stretch=3)  # Takes 3/4 of space

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: #BDC3C7;")
        layout.addWidget(separator)

        # User Notes Section
        notes_title = QLabel("📝 我的笔记")
        notes_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(notes_title)

        # User notes editor (smaller area)
        self.user_notes_editor = QTextEdit()
        self.user_notes_editor.setPlaceholderText("在此记录你的想法、感受或补充...")
        self.user_notes_editor.setMaximumHeight(150)
        self.user_notes_editor.setStyleSheet(
            """
            QTextEdit {
                border: 1px solid #BDC3C7;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                line-height: 1.6;
            }
        """
        )
        layout.addWidget(self.user_notes_editor, stretch=1)  # Takes 1/4 of space

        # Save notes button
        save_notes_btn = QPushButton("💾 保存笔记")
        save_notes_btn.setStyleSheet(
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
        save_notes_btn.clicked.connect(self.save_user_notes)
        layout.addWidget(save_notes_btn)

    def load_entry(self, date: datetime) -> None:
        """
        Load summary and notes for date.

        Args:
            date: Date to load
        """
        self.current_date = date
        self.date_label.setText(date.strftime("%Y年%m月%d日 %A"))

        # Load from database via service
        try:
            summary = self.summary_service.get_summary(date)

            if summary:
                # Display AI summary
                if summary.ai_summary:
                    self.ai_summary_display.setPlainText(summary.ai_summary)
                else:
                    self.ai_summary_display.setPlainText("暂无总结。点击'立即总结'按钮生成今天的AI总结...")

                # Display user notes
                if summary.user_notes:
                    self.user_notes_editor.setPlainText(summary.user_notes)
                else:
                    self.user_notes_editor.clear()
            else:
                # No summary exists for this date
                self.ai_summary_display.setPlainText("暂无总结。点击'立即总结'按钮生成今天的AI总结...")
                self.user_notes_editor.clear()

            logger.debug(f"Loaded entry for {date.date()}")

        except Exception as e:
            logger.error(f"Error loading entry: {e}", exc_info=True)
            QMessageBox.warning(
                self, "加载失败", f"无法加载该日期的总结：{str(e)}"
            )

    def generate_summary_now(self) -> None:
        """Manually trigger summary generation for current date."""
        try:
            # Disable button during generation
            self.generate_btn.setEnabled(False)
            self.generate_btn.setText("生成中...")

            # Get current user notes (if any)
            user_notes = self.user_notes_editor.toPlainText().strip()
            user_notes = user_notes if user_notes else None

            # Generate summary
            logger.info(f"Manually generating summary for {self.current_date.date()}")
            summary = self.summary_service.generate_summary(
                date=self.current_date,
                user_notes=user_notes,
                force_regenerate=True  # Force regeneration
            )

            if summary and summary.ai_summary:
                # Display the generated summary
                self.ai_summary_display.setPlainText(summary.ai_summary)
                QMessageBox.information(
                    self, "生成成功", "AI总结已生成！"
                )
                logger.info("Summary generated successfully")
            else:
                QMessageBox.warning(
                    self, "生成失败", "无法生成总结。请检查是否有活动记录，以及AI服务是否可用。"
                )
                logger.warning("Summary generation returned no result")

        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            QMessageBox.critical(
                self, "错误", f"生成总结时出错：{str(e)}"
            )
        finally:
            # Re-enable button
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("⚡ 立即总结")

    def save_user_notes(self) -> None:
        """Save user notes (AI summary is generated separately)."""
        user_notes = self.user_notes_editor.toPlainText().strip()

        if not user_notes:
            QMessageBox.information(
                self, "提示", "笔记为空，无需保存。"
            )
            return

        try:
            # Save user notes via service
            success = self.summary_service.save_user_notes(
                date=self.current_date,
                user_notes=user_notes
            )

            if success:
                QMessageBox.information(
                    self, "已保存", "你的笔记已保存！"
                )
                logger.info(f"Saved user notes for {self.current_date.date()}")
            else:
                QMessageBox.warning(
                    self, "保存失败", "无法保存笔记，请重试。"
                )

        except Exception as e:
            logger.error(f"Error saving user notes: {e}", exc_info=True)
            QMessageBox.critical(
                self, "错误", f"保存笔记失败：{str(e)}"
            )

    def refresh(self) -> None:
        """Refresh the view."""
        self.load_entry(self.current_date)
