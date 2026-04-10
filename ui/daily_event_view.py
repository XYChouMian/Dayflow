"""
Dayflow Windows - 每日事件视图组件
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
import sys

logger = logging.getLogger(__name__)

if sys.platform == 'win32':
    import ctypes

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QSizePolicy, QPushButton, QTextBrowser, QStackedWidget,
    QSplitter, QCalendarWidget, QDialog, QTableView, QToolButton, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QDate
from PySide6.QtGui import QPalette, QColor, QIcon, QFont
from ui.themes import show_information, show_warning, show_critical, show_question

from core.types import ActivityCard
from ui.themes import get_theme_manager, get_theme
from ui.timeline_view import TimelineView
from ui.inspiration_view import InspirationView


if sys.platform == 'win32':
    def _set_dark_title_bar(widget: QWidget, is_dark: bool = True):
        """设置 Windows 原生标题栏颜色为暗色"""
        try:
            hwnd = widget.winId()
            
            # 定义 DWM 窗口属性常量
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            
            if is_dark:
                # 启用沉浸式暗色模式（暗色标题栏）
                use_immersive_dark_mode = 1
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_void_p(int(hwnd)),
                    ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE),
                    ctypes.byref(ctypes.c_int(use_immersive_dark_mode)),
                    ctypes.sizeof(ctypes.c_int)
                )
        except Exception as e:
            logger.debug(f"设置标题栏颜色失败: {e}")


class DailyEventHeader(QWidget):
    """每日事件头部 - 显示日期选择器、导出和统计"""
    
    date_changed = Signal(datetime)
    export_clicked = Signal()
    
    def __init__(self, parent=None, storage=None):
        super().__init__(parent)
        self._current_date = datetime.now()
        self._card_count = 0
        self._total_hours = 0.0
        self.storage = storage
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        
        # 日期导航区域
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(8)
        
        # 上一天按钮
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setObjectName("navArrowButton")
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(self._go_previous_day)
        nav_layout.addWidget(self.prev_btn)
        
        # 日期显示（可点击打开日历）
        self.date_label = QPushButton()
        self.date_label.setFlat(True)
        self.date_label.setCursor(Qt.PointingHandCursor)
        self.date_label.clicked.connect(self._show_calendar)
        nav_layout.addWidget(self.date_label)
        
        # 下一天按钮
        self.next_btn = QPushButton("▶")
        self.next_btn.setObjectName("navArrowButton")
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(self._go_next_day)
        nav_layout.addWidget(self.next_btn)
        
        # 今天按钮
        self.today_btn = QPushButton("今天")
        self.today_btn.setFixedHeight(32)
        self.today_btn.setCursor(Qt.PointingHandCursor)
        self.today_btn.clicked.connect(self._go_today)
        nav_layout.addWidget(self.today_btn)
        
        layout.addLayout(nav_layout)
        layout.addStretch()
        
        # 导出按钮
        self.export_btn = QPushButton("📥 导出")
        self.export_btn.setFixedHeight(32)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_clicked.emit)
        layout.addWidget(self.export_btn)
        
        # 统计信息
        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)
        
        self._update_date_display()
        self._update_stats_display()
    
    def apply_theme(self):
        """应用主题"""
        t = get_theme()
        
        # 导航按钮样式
        # 亮色模式使用更深的颜色以提高对比度
        nav_color = "#1a1a1a" if t.name == "light" else t.text_primary
        nav_btn_style = f"""
            QPushButton#navArrowButton {{
                background-color: {t.bg_tertiary};
                color: {nav_color} !important;
                border: none !important;
                border-radius: 6px !important;
                font-size: 18px !important;
                font-weight: 900 !important;
                padding: 0 !important;
            }}
            QPushButton#navArrowButton:hover {{
                background-color: {t.bg_hover} !important;
                color: {nav_color} !important;
                border: none !important;
            }}
        """
        self.prev_btn.setStyleSheet(nav_btn_style)
        self.next_btn.setStyleSheet(nav_btn_style)
        
        # 日期显示（可点击按钮样式）
        self.date_label.setStyleSheet(f"""
            QPushButton {{
                font-size: 28px;
                font-weight: 700;
                color: {t.text_primary};
                padding: 0 12px;
                background-color: transparent;
                border: none;
            }}
            QPushButton:hover {{
                color: {t.accent};
            }}
        """)
        
        # 今天按钮（强调色）
        self.today_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.accent};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {t.accent_hover};
            }}
        """)
        
        # 导出按钮
        self.export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: none;
                border-radius: 6px;
                font-size: 13px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {t.bg_hover};
            }}
        """)
        
        # 统计信息 - 使用主题文字颜色
        self.stats_label.setStyleSheet(f"""
            font-size: 14px;
            color: {t.text_primary};
            margin-left: 16px;
        """)
    
    def _update_date_display(self):
        """更新日期显示"""
        today = datetime.now().date()
        
        if self._current_date.date() == today:
            date_text = "今天"
        elif self._current_date.date() == today - timedelta(days=1):
            date_text = "昨天"
        elif self._current_date.date() == today + timedelta(days=1):
            date_text = "明天"
        else:
            date_text = self._current_date.strftime("%m月%d日")
        
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[self._current_date.weekday()]
        
        self.date_label.setText(f"{date_text}，{weekday}")
    
    def _update_stats_display(self):
        """更新统计信息显示"""
        if self._card_count > 0:
            self.stats_label.setText(f"{self._card_count} 个活动 · {self._total_hours:.1f} 小时")
        else:
            self.stats_label.setText("暂无记录")
    
    def set_stats(self, card_count: int, total_hours: float):
        """设置统计信息"""
        self._card_count = card_count
        self._total_hours = total_hours
        self._update_stats_display()
    
    def _go_previous_day(self):
        """前一天"""
        self._current_date -= timedelta(days=1)
        self._update_date_display()
        self.date_changed.emit(self._current_date)
    
    def _go_next_day(self):
        """后一天"""
        self._current_date += timedelta(days=1)
        self._update_date_display()
        self.date_changed.emit(self._current_date)
    
    def _go_today(self):
        """跳转到今天"""
        self._current_date = datetime.now()
        self._update_date_display()
        self.date_changed.emit(self._current_date)
    
    def _show_calendar(self):
        """显示日历选择器"""
        dialog = ActivityCalendarDialog(self._current_date, self.storage, self)
        if dialog.exec() == QDialog.Accepted:
            selected_date = dialog.get_selected_date()
            self._current_date = selected_date
            self._update_date_display()
            self.date_changed.emit(selected_date)
    
    def set_date(self, date: datetime):
        """设置日期"""
        self._current_date = date
        self._update_date_display()


class ThemedCalendarWidget(QCalendarWidget):
    """自定义日历控件 - 确保样式正确应用"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def apply_theme(self):
        """应用主题样式"""
        t = get_theme()
        
        # 隐藏左侧的周数（垂直头）
        vertical_header = self.findChild(QTableView).verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)
        
        # 使用样式表设置日历样式
        self.setStyleSheet(f"""
            QTableView {{
                background-color: {t.bg_secondary};
            }}
            QTableView::item {{
                color: {t.text_primary};
                background-color: {t.bg_secondary};
            }}
            QHeaderView::section {{
                background-color: {t.bg_secondary};
                color: {t.text_primary};
                padding: 4px;
                border: none;
                font-weight: bold;
                font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
            }}
            QToolButton {{
                color: {t.text_primary};
                background: transparent;
                border: none;
                font-size: 16px;
            }}
        """)
        
        # 用 Unicode 字符替换箭头图标
        from PySide6.QtWidgets import QToolButton
        from PySide6.QtGui import QIcon
        tool_buttons = self.findChildren(QToolButton)
        for btn in tool_buttons:
            btn.setStyleSheet(f"QToolButton {{ color: {t.text_primary}; background: transparent; border: none; font-size: 16px; }}")
            btn.setIcon(QIcon())
            if "prev" in str(btn.objectName()).lower():
                btn.setText("◀")
            elif "next" in str(btn.objectName()).lower():
                btn.setText("▶")


class ActivityCalendarDialog(QDialog):
    """活动日历对话框"""
    
    def __init__(self, current_date, storage=None, parent=None):
        super().__init__(parent)
        self._current_date = current_date
        self._selected_date = current_date
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("选择日期")
        self.setMinimumSize(400, 350)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 日历
        self.calendar = ThemedCalendarWidget()
        self.calendar.setMinimumHeight(280)
        self.calendar.clicked.connect(self._on_date_selected)
        layout.addWidget(self.calendar)
        
        # 应用主题
        self.apply_theme()
    
    def apply_theme(self):
        """应用主题"""
        t = get_theme()
        
        # 使用 QPalette 设置基础颜色
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(t.bg_primary))
        palette.setColor(QPalette.WindowText, QColor(t.text_primary))
        palette.setColor(QPalette.Base, QColor(t.bg_secondary))
        palette.setColor(QPalette.Button, QColor(t.bg_tertiary))
        palette.setColor(QPalette.ButtonText, QColor(t.text_primary))
        self.setPalette(palette)
        
        # 基础样式
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg_primary};
            }}
        """)
        
        # 应用日历主题
        self.calendar.apply_theme()
        
        # 强制设置 Windows 原生标题栏为暗色
        if sys.platform == 'win32' and t.name == "dark":
            _set_dark_title_bar(self, is_dark=True)
    
    def _on_date_selected(self, date):
        """日期选择事件"""
        self._selected_date = datetime(date.year(), date.month(), date.day())
        self.accept()
    
    def get_selected_date(self):
        """获取选中的日期"""
        return self._selected_date


class DailySummaryView(QWidget):
    """每日总结视图"""
    
    def __init__(self, storage=None, parent=None):
        super().__init__(parent)
        self._cards = []
        self._inspiration_cards = []
        self._date = datetime.now()
        self._is_generating = False
        self._event_summary_generated = False
        self._storage = storage
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
        self._load_summary()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 总结内容显示区域
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(24, 0, 24, 24)
        
        # 每日总结区域
        daily_summary_container = QWidget()
        daily_summary_layout = QVBoxLayout(daily_summary_container)
        daily_summary_layout.setContentsMargins(0, 0, 0, 0)
        daily_summary_layout.setSpacing(10)
        
        # 每日总结内容行
        daily_content_row = QHBoxLayout()
        daily_content_row.setSpacing(10)
        
        # 事件总结
        event_summary_container = QWidget()
        event_summary_layout = QVBoxLayout(event_summary_container)
        event_summary_layout.setContentsMargins(0, 0, 0, 0)
        
        self.event_summary_btn = QPushButton("生成事件总结")
        self.event_summary_btn.setFixedSize(140, 40)
        self.event_summary_btn.setCursor(Qt.PointingHandCursor)
        self.event_summary_btn.clicked.connect(self._on_event_summary)
        event_summary_layout.addWidget(self.event_summary_btn)
        
        self.event_summary_text = QTextBrowser()
        self.event_summary_text.setPlaceholderText("点击\"开始总结\"按钮，系统将为您生成每日活动总结...")
        self.event_summary_text.setMinimumHeight(350)
        event_summary_layout.addWidget(self.event_summary_text)
        
        # 灵感总结
        inspiration_summary_container = QWidget()
        inspiration_summary_layout = QVBoxLayout(inspiration_summary_container)
        inspiration_summary_layout.setContentsMargins(0, 0, 0, 0)
        
        self.inspiration_summary_btn = QPushButton("生成灵感总结")
        self.inspiration_summary_btn.setFixedSize(140, 40)
        self.inspiration_summary_btn.setCursor(Qt.PointingHandCursor)
        self.inspiration_summary_btn.clicked.connect(self._generate_inspiration_summary)
        self.inspiration_summary_btn.setEnabled(True)
        inspiration_summary_layout.addWidget(self.inspiration_summary_btn)
        
        self.inspiration_summary_text = QTextBrowser()
        self.inspiration_summary_text.setPlaceholderText("点击\"开始总结\"按钮，系统将为您生成灵感总结和延伸思考...")
        self.inspiration_summary_text.setMinimumHeight(350)
        inspiration_summary_layout.addWidget(self.inspiration_summary_text)
        
        daily_content_row.addWidget(event_summary_container)
        daily_content_row.addWidget(inspiration_summary_container)
        daily_summary_layout.addLayout(daily_content_row)
        
        content_layout.addWidget(daily_summary_container)
        layout.addLayout(content_layout)
    
    def _on_event_summary(self):
        """生成事件总结"""
        if self._is_generating:
            return
        
        if not self._cards:
            show_warning(self, "提示", "当前日期没有活动记录，无法生成事件总结。")
            return
        
        # 检查是否已有总结内容
        current_summary = self.event_summary_text.toPlainText()
        if current_summary and not current_summary.startswith("生成失败:") and current_summary != "暂无事件总结":
            reply = show_question(
                self,
                "确认生成",
                "当前已有事件总结内容，确定要重新生成吗？"
            )
            if reply != QMessageBox.Yes:
                return
        
        self._is_generating = True
        self.event_summary_btn.setEnabled(False)
        
        from PySide6.QtCore import QThread, Signal
        
        class EventSummaryWorker(QThread):
            finished = Signal(str)
            error = Signal(str)
            
            def __init__(self, cards, date, thinking_mode=None, storage=None):
                super().__init__()
                self.cards = cards
                self.date = date
                self.thinking_mode = thinking_mode
                self.storage = storage
            
            def run(self):
                try:
                    from core.llm_provider import generate_event_summary_sync
                    import config
                    
                    api_base_url = self.storage.get_setting("api_url", config.API_BASE_URL)
                    api_key = self.storage.get_setting("api_key", "")
                    
                    use_glm = self.storage.get_setting("use_glm_model", "false") == "true"
                    if use_glm:
                        summary_model = self.storage.get_setting("daily_summary_model", config.DAILY_SUMMARY_MODEL)
                        event_summary = generate_event_summary_sync(
                            self.cards, 
                            self.date, 
                            thinking_mode=self.thinking_mode,
                            api_base_url=api_base_url,
                            api_key=api_key,
                            model=summary_model
                        )
                    else:
                        summary_model = self.storage.get_setting("custom_summary_model", config.DAILY_SUMMARY_MODEL)
                        event_summary = generate_event_summary_sync(
                            self.cards, 
                            self.date, 
                            api_base_url=api_base_url,
                            api_key=api_key,
                            model=summary_model
                        )
                    self.finished.emit(event_summary)
                except Exception as e:
                    self.error.emit(str(e))
        
        import config
        thinking_mode = config.SUMMARY_THINKING_MODE
        self.worker = EventSummaryWorker(self._cards, self._date, thinking_mode, self._storage)
        self.worker.finished.connect(self._on_event_summary_finished)
        self.worker.error.connect(self._on_summary_error)
        self.worker.start()
    
    def _generate_inspiration_summary(self):
        """生成灵感总结（基于事件总结和灵感卡片）"""
        if self._is_generating:
            return
        
        logger.info(f"准备生成灵感总结，当前日期: {self._date}, 灵感卡片数量: {len(self._inspiration_cards) if self._inspiration_cards else 0}")
        
        if not self._inspiration_cards:
            show_warning(self, "提示", "当前日期没有灵感记录，无法生成灵感总结。")
            return
        
        # 检查是否已生成事件总结
        if not self._event_summary_generated:
            event_summary_content = self.event_summary_text.toPlainText()
            if not event_summary_content or event_summary_content == "暂无事件总结":
                reply = show_question(
                    self,
                    "提示",
                    "当前尚未生成事件总结，生成灵感总结时只会将灵感卡片发送给AI进行分析，缺少当日活动的上下文信息。\n\n建议先生成事件总结以获得更好的分析效果。\n\n是否继续生成灵感总结？"
                )
                if reply != QMessageBox.Yes:
                    return
        
        # 检查是否已有总结内容
        current_summary = self.inspiration_summary_text.toPlainText()
        if current_summary and not current_summary.startswith("生成失败:") and current_summary != "暂无灵感总结":
            reply = show_question(
                self,
                "确认生成",
                "当前已有灵感总结内容，确定要重新生成吗？"
            )
            if reply != QMessageBox.Yes:
                return
        
        self._is_generating = True
        self.inspiration_summary_btn.setEnabled(False)
        
        from PySide6.QtCore import QThread, Signal
        
        class InspirationSummaryWorker(QThread):
            finished = Signal(str)
            error = Signal(str)
            
            def __init__(self, event_summary, inspiration_cards, date, thinking_mode=None, storage=None):
                super().__init__()
                self.event_summary = event_summary
                self.inspiration_cards = inspiration_cards
                self.date = date
                self.thinking_mode = thinking_mode
                self.storage = storage
            
            def run(self):
                try:
                    logger.info(f"开始生成灵感总结，卡片数量: {len(self.inspiration_cards) if self.inspiration_cards else 0}")
                    from core.llm_provider import generate_inspiration_summary_sync
                    import config
                    
                    api_base_url = self.storage.get_setting("api_url", config.API_BASE_URL)
                    api_key = self.storage.get_setting("api_key", "")
                    
                    use_glm = self.storage.get_setting("use_glm_model", "false") == "true"
                    if use_glm:
                        summary_model = self.storage.get_setting("daily_summary_model", config.DAILY_SUMMARY_MODEL)
                        inspiration_summary = generate_inspiration_summary_sync(
                            self.event_summary,
                            self.inspiration_cards, 
                            self.date, 
                            thinking_mode=self.thinking_mode,
                            api_base_url=api_base_url,
                            api_key=api_key,
                            model=summary_model
                        )
                    else:
                        summary_model = self.storage.get_setting("custom_summary_model", config.DAILY_SUMMARY_MODEL)
                        inspiration_summary = generate_inspiration_summary_sync(
                            self.event_summary,
                            self.inspiration_cards, 
                            self.date, 
                            api_base_url=api_base_url,
                            api_key=api_key,
                            model=summary_model
                        )
                    logger.info("灵感总结生成完成")
                    self.finished.emit(inspiration_summary)
                except Exception as e:
                    logger.error(f"灵感总结生成失败: {e}")
                    self.error.emit(str(e))
        
        import config
        thinking_mode = config.SUMMARY_THINKING_MODE
        event_summary = self.event_summary_text.toPlainText() if self._event_summary_generated else ""
        self.worker = InspirationSummaryWorker(event_summary, self._inspiration_cards, self._date, thinking_mode, self._storage)
        self.worker.finished.connect(self._on_inspiration_summary_finished)
        self.worker.error.connect(self._on_summary_error)
        self.worker.start()
    
    def _on_event_summary_finished(self, event_summary: str):
        """事件总结生成完成"""
        self._is_generating = False
        self._event_summary_generated = True
        self.event_summary_btn.setEnabled(True)
        self.inspiration_summary_btn.setEnabled(True)
        
        self.event_summary_text.setMarkdown(event_summary if event_summary else "暂无事件总结")
        
        if self._storage:
            try:
                self._storage.save_daily_summary(self._date, event_summary, None)
                logger.info(f"已保存 {self._date.strftime('%Y-%m-%d')} 的事件总结")
            except Exception as e:
                logger.error(f"保存事件总结失败: {e}")
                show_warning(self, "警告", f"事件总结生成成功，但保存到数据库失败:\n{e}")
        
        show_information(self, "成功", "事件总结生成完成！现在可以生成灵感总结了。")
    
    def _on_inspiration_summary_finished(self, inspiration_summary: str):
        """灵感总结生成完成"""
        self._is_generating = False
        self.inspiration_summary_btn.setEnabled(True)
        
        self.inspiration_summary_text.setMarkdown(inspiration_summary if inspiration_summary else "暂无灵感总结")
        
        if self._storage:
            try:
                event_summary = self.event_summary_text.toPlainText()
                self._storage.save_daily_summary(self._date, event_summary, inspiration_summary)
                logger.info(f"已保存 {self._date.strftime('%Y-%m-%d')} 的灵感总结")
            except Exception as e:
                logger.error(f"保存灵感总结失败: {e}")
                show_warning(self, "警告", f"灵感总结生成成功，但保存到数据库失败:\n{e}")
        
        show_information(self, "成功", "灵感总结生成完成！")
    
    def _on_summary_error(self, error_msg: str):
        """总结生成失败"""
        self._is_generating = False
        self.event_summary_btn.setEnabled(True)
        self.inspiration_summary_btn.setEnabled(True)
        
        self.event_summary_text.setPlainText(f"生成失败: {error_msg}")
        self.inspiration_summary_text.setPlainText(f"生成失败: {error_msg}")
        show_critical(self, "错误", f"总结生成失败:\n{error_msg}")
    
    def set_cards(self, cards: List[ActivityCard]):
        """设置活动卡片"""
        self._cards = cards
    
    def set_date(self, date: datetime):
        """设置日期"""
        self._date = date
        self._load_summary()
    
    def set_storage(self, storage):
        """设置存储管理器"""
        self._storage = storage
        self._load_weekly_summaries_from_database()
        self._load_summary()
    
    def _load_summary(self):
        """加载已保存的每日总结"""
        if not self._storage:
            return
        
        try:
            event_summary, inspiration_summary = self._storage.get_daily_summary(self._date)
            if event_summary:
                self.event_summary_text.setMarkdown(event_summary)
            else:
                self.event_summary_text.clear()
            
            if inspiration_summary:
                self.inspiration_summary_text.setMarkdown(inspiration_summary)
            else:
                self.inspiration_summary_text.clear()
        except Exception as e:
            logger.error(f"加载每日总结失败: {e}")
    
    def set_cards(self, cards: List[ActivityCard]):
        """设置活动卡片"""
        self._cards = cards
    
    def set_inspiration_cards(self, inspiration_cards: List):
        """设置灵感卡片"""
        logger.info(f"设置灵感卡片，日期: {self._date}, 卡片数量: {len(inspiration_cards) if inspiration_cards else 0}")
        self._inspiration_cards = inspiration_cards

    def apply_theme(self):
        """应用主题"""
        t = get_theme()
        
        # 总结按钮样式
        button_style = f"""
            QPushButton {{
                background-color: {t.accent};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {t.accent_hover};
            }}
            QPushButton:pressed {{
                background-color: {t.accent_hover};
            }}
            QPushButton:disabled {{
                background-color: {t.border};
                color: {t.text_muted};
            }}
        """
        self.event_summary_btn.setStyleSheet(button_style)
        self.inspiration_summary_btn.setStyleSheet(button_style)
        
        # 文本浏览器样式（Markdown 渲染）
        summary_style = f"""
            QTextBrowser {{
                background-color: {t.bg_secondary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 12px;
                padding: 24px;
                font-size: 15px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                line-height: 1.8;
            }}
            QTextBrowser h1 {{
                font-size: 24px;
                font-weight: bold;
                margin: 16px 0 8px 0;
                color: {t.text_primary};
            }}
            QTextBrowser h2 {{
                font-size: 20px;
                font-weight: bold;
                margin: 14px 0 6px 0;
                color: {t.text_primary};
            }}
            QTextBrowser h3 {{
                font-size: 18px;
                font-weight: bold;
                margin: 12px 0 6px 0;
                color: {t.text_primary};
            }}
            QTextBrowser ul, QTextBrowser ol {{
                margin: 8px 0 8px 24px;
            }}
            QTextBrowser li {{
                margin: 4px 0;
            }}
            QTextBrowser strong {{
                font-weight: bold;
                color: {t.text_primary};
            }}
            QTextBrowser code {{
                background-color: {t.bg_tertiary};
                color: {t.text_secondary};
                padding: 2px 6px;
                border-radius: 4px;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 14px;
            }}
            QTextBrowser pre {{
                background-color: {t.bg_tertiary};
                padding: 12px;
                border-radius: 8px;
                margin: 8px 0;
            }}
            QTextBrowser pre code {{
                background-color: transparent;
                padding: 0;
            }}
        """
        
        self.event_summary_text.setStyleSheet(summary_style)
        self.inspiration_summary_text.setStyleSheet(summary_style)


class WeeklySummaryView(QWidget):
    """每周总结视图"""
    
    def __init__(self, storage=None, parent=None):
        super().__init__(parent)
        self._cards = []
        self._inspiration_cards = []
        self._date = None
        self._is_generating = False
        self._event_summary_generated = False
        self._storage = storage
        self._workers = {}
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
        self._load_weekly_summaries_from_database()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 总结内容显示区域
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(24, 0, 24, 24)
        
        # 每周总结区域
        weekly_summary_container = QWidget()
        weekly_summary_layout = QVBoxLayout(weekly_summary_container)
        weekly_summary_layout.setContentsMargins(0, 0, 0, 0)
        weekly_summary_layout.setSpacing(10)
        
        # 每周总结内容行
        weekly_content_row = QHBoxLayout()
        weekly_content_row.setSpacing(10)
        
        # 事件总结
        event_summary_container = QWidget()
        event_summary_layout = QVBoxLayout(event_summary_container)
        event_summary_layout.setContentsMargins(0, 0, 0, 0)
        
        self.event_summary_btn = QPushButton("生成本周事件总结")
        self.event_summary_btn.setFixedSize(140, 40)
        self.event_summary_btn.setCursor(Qt.PointingHandCursor)
        self.event_summary_btn.clicked.connect(self._on_event_summary)
        event_summary_layout.addWidget(self.event_summary_btn)
        
        self.event_summary_text = QTextBrowser()
        self.event_summary_text.setPlaceholderText("点击\"生成本周事件总结\"按钮，系统将为您生成每周活动总结...")
        self.event_summary_text.setMinimumHeight(350)
        event_summary_layout.addWidget(self.event_summary_text)
        
        # 灵感总结
        inspiration_summary_container = QWidget()
        inspiration_summary_layout = QVBoxLayout(inspiration_summary_container)
        inspiration_summary_layout.setContentsMargins(0, 0, 0, 0)
        
        self.inspiration_summary_btn = QPushButton("生成本周灵感总结")
        self.inspiration_summary_btn.setFixedSize(140, 40)
        self.inspiration_summary_btn.setCursor(Qt.PointingHandCursor)
        self.inspiration_summary_btn.clicked.connect(self._generate_inspiration_summary)
        self.inspiration_summary_btn.setEnabled(True)
        inspiration_summary_layout.addWidget(self.inspiration_summary_btn)
        
        self.inspiration_summary_text = QTextBrowser()
        self.inspiration_summary_text.setPlaceholderText("点击\"生成本周灵感总结\"按钮，系统将为您生成每周灵感总结和延伸思考...")
        self.inspiration_summary_text.setMinimumHeight(350)
        inspiration_summary_layout.addWidget(self.inspiration_summary_text)
        
        weekly_content_row.addWidget(event_summary_container)
        weekly_content_row.addWidget(inspiration_summary_container)
        weekly_summary_layout.addLayout(weekly_content_row)
        
        content_layout.addWidget(weekly_summary_container)
        layout.addLayout(content_layout)
    
    def _on_event_summary(self):
        """生成本周事件总结"""
        if self._is_generating:
            return
        
        self._is_generating = True
        self.event_summary_btn.setEnabled(False)
        
        if not self._storage:
            self.event_summary_text.setPlainText("错误：未设置存储管理器")
            self._is_generating = False
            self.event_summary_btn.setEnabled(True)
            return
        
        if self._date is None:
            self._date = datetime.now()
        
        try:
            daily_summaries, missing_days = self._get_past_7_days_event_summaries()
            logger.info(f"每周事件总结 - 检测到缺失天数: {len(missing_days)}, 每日总结数量: {len(daily_summaries)}")
            
            if missing_days:
                missing_dates_str = ", ".join([d.strftime('%Y-%m-%d') for d in missing_days])
                logger.info(f"准备弹出确认对话框，缺失日期: {missing_dates_str}")
                reply = show_question(
                    self,
                    "确认生成",
                    f"过去7天中有{len(missing_days)}天的每日事件总结缺失：\n{missing_dates_str}\n\n是否继续生成本周事件总结？"
                )
                logger.info(f"用户回复: {reply}")
                if reply != QMessageBox.Yes:
                    self._is_generating = False
                    self.event_summary_btn.setEnabled(True)
                    logger.info("用户取消生成")
                    return
            
            self._generate_weekly_event_summary(daily_summaries, missing_days)
        except Exception as e:
            logger.error(f"生成本周事件总结失败: {e}")
            self.event_summary_text.setPlainText(f"生成失败: {e}")
            self._is_generating = False
            self.event_summary_btn.setEnabled(True)
    
    def _generate_weekly_event_summary(self, daily_summaries, missing_days):
        """生成每周事件总结"""
        from PySide6.QtCore import QThread, Signal
        
        class WeeklyEventSummaryWorker(QThread):
            finished = Signal(str)
            error = Signal(str)
            
            def __init__(self, daily_summaries, missing_days, end_date, storage=None):
                super().__init__()
                self.daily_summaries = daily_summaries
                self.missing_days = missing_days
                self.end_date = end_date
                self.storage = storage
            
            def run(self):
                try:
                    logger.info(f"开始生成每周事件总结，每日总结数量: {len(self.daily_summaries)}")
                    from core.llm_provider import generate_weekly_event_summary_sync
                    import config
                    
                    api_base_url = self.storage.get_setting("api_url", config.API_BASE_URL)
                    api_key = self.storage.get_setting("api_key", "")
                    
                    use_glm = self.storage.get_setting("use_glm_model", "false") == "true"
                    if use_glm:
                        summary_model = self.storage.get_setting("daily_summary_model", config.DAILY_SUMMARY_MODEL)
                    else:
                        summary_model = self.storage.get_setting("summary_model", config.SUMMARY_MODEL)
                    
                    event_summary = generate_weekly_event_summary_sync(
                        daily_summaries=self.daily_summaries,
                        missing_days=self.missing_days,
                        end_date=self.end_date,
                        model=summary_model,
                        api_base_url=api_base_url,
                        api_key=api_key
                    )
                    
                    self.finished.emit(event_summary)
                except Exception as e:
                    logger.error(f"生成每周事件总结失败: {e}")
                    self.error.emit(str(e))
        
        self.event_summary_text.setPlainText("正在生成每周事件总结，请稍候...")
        
        worker = WeeklyEventSummaryWorker(daily_summaries, missing_days, self._date, self._storage)
        worker_id = f"weekly_event_{datetime.now().timestamp()}"
        self._workers[worker_id] = worker
        
        def cleanup():
            self._workers.pop(worker_id, None)
        
        worker.finished.connect(lambda summary: self._on_weekly_event_summary_finished(summary, cleanup))
        worker.error.connect(lambda error: self._on_weekly_event_summary_error(error, cleanup))
        worker.start()
    
    def _on_weekly_event_summary_finished(self, event_summary, cleanup):
        """每周事件总结生成完成"""
        cleanup()
        self._is_generating = False
        self.event_summary_btn.setEnabled(True)
        
        self.event_summary_text.setMarkdown(event_summary if event_summary else "暂无事件总结")
        
        if self._storage:
            try:
                week_start = self._date - timedelta(days=6)
                week_end = self._date
                inspiration_summary = self.inspiration_summary_text.toPlainText()
                self._storage.save_weekly_summary(week_start, week_end, event_summary, inspiration_summary)
                logger.info(f"已保存本周事件总结 {week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}")
            except Exception as e:
                logger.error(f"保存每周事件总结失败: {e}")
                show_warning(self, "警告", f"事件总结生成成功，但保存到数据库失败:\n{e}")
        
        show_information(self, "成功", "每周事件总结生成完成！")
    
    def _on_weekly_event_summary_error(self, error_msg, cleanup):
        """每周事件总结生成失败"""
        cleanup()
        self._is_generating = False
        self.event_summary_btn.setEnabled(True)
        
        self.event_summary_text.setPlainText(f"生成失败: {error_msg}")
        show_critical(self, "错误", f"每周事件总结生成失败:\n{error_msg}")
    
    def _generate_inspiration_summary(self):
        """生成本周灵感总结"""
        if self._is_generating:
            return
        
        self._is_generating = True
        self.inspiration_summary_btn.setEnabled(False)
        
        if not self._storage:
            self.inspiration_summary_text.setPlainText("错误：未设置存储管理器")
            self._is_generating = False
            self.inspiration_summary_btn.setEnabled(True)
            return
        
        if self._date is None:
            self._date = datetime.now()
        
        try:
            daily_summaries, missing_days = self._get_past_7_days_inspiration_summaries()
            logger.info(f"每周灵感总结 - 检测到缺失天数: {len(missing_days)}, 每日总结数量: {len(daily_summaries)}")
            
            if missing_days:
                missing_dates_str = ", ".join([d.strftime('%Y-%m-%d') for d in missing_days])
                logger.info(f"准备弹出确认对话框，缺失日期: {missing_dates_str}")
                reply = show_question(
                    self,
                    "确认生成",
                    f"过去7天中有{len(missing_days)}天的每日灵感总结缺失：\n{missing_dates_str}\n\n是否继续生成本周灵感总结？"
                )
                logger.info(f"用户回复: {reply}")
                if reply != QMessageBox.Yes:
                    self._is_generating = False
                    self.inspiration_summary_btn.setEnabled(True)
                    logger.info("用户取消生成")
                    return
            
            self._generate_weekly_inspiration_summary(daily_summaries, missing_days)
        except Exception as e:
            logger.error(f"生成本周灵感总结失败: {e}")
            self.inspiration_summary_text.setPlainText(f"生成失败: {e}")
            self._is_generating = False
            self.inspiration_summary_btn.setEnabled(True)
    
    def _generate_weekly_inspiration_summary(self, daily_summaries, missing_days):
        """生成每周灵感总结"""
        from PySide6.QtCore import QThread, Signal
        
        class WeeklyInspirationSummaryWorker(QThread):
            finished = Signal(str)
            error = Signal(str)
            
            def __init__(self, daily_summaries, missing_days, end_date, storage=None):
                super().__init__()
                self.daily_summaries = daily_summaries
                self.missing_days = missing_days
                self.end_date = end_date
                self.storage = storage
            
            def run(self):
                try:
                    logger.info(f"开始生成每周灵感总结，每日总结数量: {len(self.daily_summaries)}")
                    from core.llm_provider import generate_weekly_inspiration_summary_sync
                    import config
                    
                    api_base_url = self.storage.get_setting("api_url", config.API_BASE_URL)
                    api_key = self.storage.get_setting("api_key", "")
                    
                    use_glm = self.storage.get_setting("use_glm_model", "false") == "true"
                    if use_glm:
                        summary_model = self.storage.get_setting("daily_summary_model", config.DAILY_SUMMARY_MODEL)
                    else:
                        summary_model = self.storage.get_setting("summary_model", config.SUMMARY_MODEL)
                    
                    inspiration_summary = generate_weekly_inspiration_summary_sync(
                        daily_summaries=self.daily_summaries,
                        missing_days=self.missing_days,
                        end_date=self.end_date,
                        model=summary_model,
                        api_base_url=api_base_url,
                        api_key=api_key
                    )
                    
                    self.finished.emit(inspiration_summary)
                except Exception as e:
                    logger.error(f"生成每周灵感总结失败: {e}")
                    self.error.emit(str(e))
        
        self.inspiration_summary_text.setPlainText("正在生成每周灵感总结，请稍候...")
        
        worker = WeeklyInspirationSummaryWorker(daily_summaries, missing_days, self._date, self._storage)
        worker_id = f"weekly_inspiration_{datetime.now().timestamp()}"
        self._workers[worker_id] = worker
        
        def cleanup():
            self._workers.pop(worker_id, None)
        
        worker.finished.connect(lambda summary: self._on_weekly_inspiration_summary_finished(summary, cleanup))
        worker.error.connect(lambda error: self._on_weekly_inspiration_summary_error(error, cleanup))
        worker.start()
    
    def _on_weekly_inspiration_summary_finished(self, inspiration_summary, cleanup):
        """每周灵感总结生成完成"""
        cleanup()
        self._is_generating = False
        self.inspiration_summary_btn.setEnabled(True)
        
        self.inspiration_summary_text.setMarkdown(inspiration_summary if inspiration_summary else "暂无灵感总结")
        
        if self._storage:
            try:
                week_start = self._date - timedelta(days=6)
                week_end = self._date
                event_summary = self.event_summary_text.toPlainText()
                self._storage.save_weekly_summary(week_start, week_end, event_summary, inspiration_summary)
                logger.info(f"已保存本周灵感总结 {week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}")
            except Exception as e:
                logger.error(f"保存每周灵感总结失败: {e}")
                show_warning(self, "警告", f"灵感总结生成成功，但保存到数据库失败:\n{e}")
        
        show_information(self, "成功", "每周灵感总结生成完成！")
    
    def _on_weekly_inspiration_summary_error(self, error_msg, cleanup):
        """每周灵感总结生成失败"""
        cleanup()
        self._is_generating = False
        self.inspiration_summary_btn.setEnabled(True)
        
        self.inspiration_summary_text.setPlainText(f"生成失败: {error_msg}")
        show_critical(self, "错误", f"每周灵感总结生成失败:\n{error_msg}")
    
    def _get_past_7_days_event_summaries(self):
        """获取过去7天的每日事件总结"""
        daily_summaries = []
        missing_days = []
        
        for i in range(7):
            date = self._date - timedelta(days=6 - i)
            event_summary, inspiration_summary = self._storage.get_daily_summary(date)
            
            if event_summary is None:
                missing_days.append(date)
            else:
                daily_summaries.append({
                    'date': date,
                    'event_summary': event_summary,
                    'inspiration_summary': inspiration_summary or ""
                })
        
        return daily_summaries, missing_days
    
    def _get_past_7_days_inspiration_summaries(self):
        """获取过去7天的每日灵感总结"""
        daily_summaries = []
        missing_days = []
        
        for i in range(7):
            date = self._date - timedelta(days=6 - i)
            event_summary, inspiration_summary = self._storage.get_daily_summary(date)
            
            if inspiration_summary is None:
                missing_days.append(date)
            else:
                daily_summaries.append({
                    'date': date,
                    'event_summary': event_summary or "",
                    'inspiration_summary': inspiration_summary
                })
        
        return daily_summaries, missing_days
    
    def set_cards(self, cards):
        """设置活动卡片"""
        self._cards = cards
    
    def set_date(self, date):
        """设置日期"""
        self._date = date
        self._load_weekly_summaries_from_database()
    
    def set_storage(self, storage):
        """设置存储管理器"""
        self._storage = storage
        self._load_weekly_summaries_from_database()
    
    def _load_weekly_summaries_from_database(self):
        """从数据库加载每周总结"""
        if not self._storage:
            return
        
        try:
            if self._date is None:
                self._date = datetime.now()
            
            week_start = self._date - timedelta(days=6)
            week_end = self._date
            
            event_summary, inspiration_summary = self._storage.get_weekly_summary(week_start, week_end)
            
            if event_summary:
                self.event_summary_text.setMarkdown(event_summary)
                logger.info(f"已加载本周事件总结 {week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}")
            
            if inspiration_summary:
                self.inspiration_summary_text.setMarkdown(inspiration_summary)
                logger.info(f"已加载本周灵感总结 {week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}")
                
        except Exception as e:
            logger.error(f"加载每周总结失败: {e}")
    
    def set_inspiration_cards(self, inspiration_cards):
        """设置灵感卡片"""
        logger.info(f"设置灵感卡片，卡片数量: {len(inspiration_cards) if inspiration_cards else 0}")
        self._inspiration_cards = inspiration_cards

    def apply_theme(self):
        """应用主题"""
        t = get_theme()
        
        # 总结按钮样式
        button_style = f"""
            QPushButton {{
                background-color: {t.accent};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {t.accent_hover};
            }}
            QPushButton:pressed {{
                background-color: {t.accent_hover};
            }}
            QPushButton:disabled {{
                background-color: {t.border};
                color: {t.text_muted};
            }}
        """
        self.event_summary_btn.setStyleSheet(button_style)
        self.inspiration_summary_btn.setStyleSheet(button_style)
        
        # 文本浏览器样式（Markdown 渲染）
        summary_style = f"""
            QTextBrowser {{
                background-color: {t.bg_secondary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 12px;
                padding: 24px;
                font-size: 15px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                line-height: 1.8;
            }}
            QTextBrowser h1 {{
                font-size: 24px;
                font-weight: bold;
                margin: 16px 0 8px 0;
                color: {t.text_primary};
            }}
            QTextBrowser h2 {{
                font-size: 20px;
                font-weight: bold;
                margin: 14px 0 6px 0;
                color: {t.text_primary};
            }}
            QTextBrowser h3 {{
                font-size: 18px;
                font-weight: bold;
                margin: 12px 0 6px 0;
                color: {t.text_primary};
            }}
            QTextBrowser ul, QTextBrowser ol {{
                margin: 8px 0 8px 24px;
            }}
            QTextBrowser li {{
                margin: 4px 0;
            }}
            QTextBrowser strong {{
                font-weight: bold;
                color: {t.text_primary};
            }}
            QTextBrowser code {{
                background-color: {t.bg_tertiary};
                color: {t.text_secondary};
                padding: 2px 6px;
                border-radius: 4px;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 14px;
            }}
            QTextBrowser pre {{
                background-color: {t.bg_tertiary};
                padding: 12px;
                border-radius: 8px;
                margin: 8px 0;
            }}
            QTextBrowser pre code {{
                background-color: transparent;
                padding: 0;
            }}
        """
        
        self.event_summary_text.setStyleSheet(summary_style)
        self.inspiration_summary_text.setStyleSheet(summary_style)


class SubTabButton(QPushButton):
    """子选项卡按钮"""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
    
    def apply_theme(self, checked: bool = False):
        """应用主题"""
        t = get_theme()
        
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.accent};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 600;
                    padding: 0 20px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {t.text_secondary};
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    padding: 0 20px;
                }}
                QPushButton:hover {{
                    background-color: {t.bg_tertiary};
                    color: {t.text_primary};
                }}
            """)


class DailyEventView(QWidget):
    """每日事件主视图"""
    
    card_selected = Signal(ActivityCard)
    date_changed = Signal(datetime)
    export_requested = Signal(datetime, list)
    card_updated = Signal(ActivityCard)
    card_deleted = Signal(int)
    
    def __init__(self, storage=None, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._current_date = datetime.now()
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
        
        # 初始化时将灵感卡片传递给总结视图
        self._on_inspiration_updated()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 头部 - 日期选择器、导出和统计
        self.header = DailyEventHeader(storage=self._storage)
        self.header.date_changed.connect(self._on_date_changed)
        self.header.export_clicked.connect(self._on_export_clicked)
        main_layout.addWidget(self.header)
        
        # 子选项卡区域
        tabs_layout = QHBoxLayout()
        tabs_layout.setContentsMargins(24, 8, 24, 8)
        
        self.timeline_tab = SubTabButton("时间轴")
        self.timeline_tab.setChecked(True)
        self.timeline_tab.clicked.connect(lambda: self._switch_tab(0))
        tabs_layout.addWidget(self.timeline_tab)
        
        self.inspiration_tab = SubTabButton("快速记录")
        self.inspiration_tab.clicked.connect(lambda: self._switch_tab(1))
        tabs_layout.addWidget(self.inspiration_tab)
        
        self.summary_tab = SubTabButton("每日总结")
        self.summary_tab.clicked.connect(lambda: self._switch_tab(2))
        tabs_layout.addWidget(self.summary_tab)
        
        self.weekly_summary_tab = SubTabButton("近7日总结")
        self.weekly_summary_tab.clicked.connect(lambda: self._switch_tab(3))
        tabs_layout.addWidget(self.weekly_summary_tab)
        
        tabs_layout.addStretch()
        main_layout.addLayout(tabs_layout)
        
        # 内容堆栈
        self.stack = QStackedWidget()
        
        # 时间轴页面
        self.timeline_view = TimelineView()
        self.timeline_view.card_selected.connect(self.card_selected)
        self.timeline_view.export_requested.connect(self.export_requested)
        self.timeline_view.card_updated.connect(self.card_updated)
        self.timeline_view.card_deleted.connect(self.card_deleted)
        self.stack.addWidget(self.timeline_view)
        
        # 灵感页面
        self.inspiration_view = InspirationView(storage=self._storage)
        self.inspiration_view.inspiration_updated.connect(self._on_inspiration_updated)
        self.stack.addWidget(self.inspiration_view)
        
        # 每日总结页面
        self.summary_view = DailySummaryView(storage=self._storage)
        self.stack.addWidget(self.summary_view)
        
        # 每周总结页面
        self.weekly_summary_view = WeeklySummaryView(storage=self._storage)
        self.stack.addWidget(self.weekly_summary_view)
        
        main_layout.addWidget(self.stack)
    
    def apply_theme(self):
        """应用主题"""
        self.timeline_tab.apply_theme(True)
        self.inspiration_tab.apply_theme(False)
        self.summary_tab.apply_theme(False)
        self.weekly_summary_tab.apply_theme(False)
    
    def _switch_tab(self, index: int):
        """切换子选项卡"""
        self.stack.setCurrentIndex(index)
        
        if index == 0:
            self.timeline_tab.setChecked(True)
            self.timeline_tab.apply_theme(True)
            self.inspiration_tab.setChecked(False)
            self.inspiration_tab.apply_theme(False)
            self.summary_tab.setChecked(False)
            self.summary_tab.apply_theme(False)
            self.weekly_summary_tab.setChecked(False)
            self.weekly_summary_tab.apply_theme(False)
        elif index == 1:
            self.timeline_tab.setChecked(False)
            self.timeline_tab.apply_theme(False)
            self.inspiration_tab.setChecked(True)
            self.inspiration_tab.apply_theme(True)
            self.summary_tab.setChecked(False)
            self.summary_tab.apply_theme(False)
            self.weekly_summary_tab.setChecked(False)
            self.weekly_summary_tab.apply_theme(False)
        elif index == 2:
            self.timeline_tab.setChecked(False)
            self.timeline_tab.apply_theme(False)
            self.inspiration_tab.setChecked(False)
            self.inspiration_tab.apply_theme(False)
            self.summary_tab.setChecked(True)
            self.summary_tab.apply_theme(True)
            self.weekly_summary_tab.setChecked(False)
            self.weekly_summary_tab.apply_theme(False)
            self.summary_view._load_summary()
        else:
            self.timeline_tab.setChecked(False)
            self.timeline_tab.apply_theme(False)
            self.inspiration_tab.setChecked(False)
            self.inspiration_tab.apply_theme(False)
            self.summary_tab.setChecked(False)
            self.summary_tab.apply_theme(False)
            self.weekly_summary_tab.setChecked(True)
            self.weekly_summary_tab.apply_theme(True)
    
    def _on_date_changed(self, date: datetime):
        """日期改变"""
        self._current_date = date
        self.timeline_view.set_date(date)
        self.inspiration_view.set_date(date)
        self.summary_view.set_date(date)
        self.weekly_summary_view.set_date(date)
        self.date_changed.emit(date)
    
    def _on_inspiration_updated(self):
        """灵感更新"""
        self.summary_view.set_inspiration_cards(self.inspiration_view.get_cards())
    
    def _on_export_clicked(self):
        """导出按钮点击"""
        cards = self.timeline_view._cards
        self.export_requested.emit(self._current_date, cards)
    
    def set_cards(self, cards: List[ActivityCard]):
        """设置卡片"""
        self.timeline_view.set_cards(cards)
        self.summary_view.set_cards(cards)
        # 更新统计信息
        total_hours = sum(card.duration_minutes / 60 for card in cards)
        self.header.set_stats(len(cards), total_hours)
    
    def set_date(self, date: datetime):
        """设置日期"""
        self._current_date = date
        self.header.set_date(date)
        self.timeline_view.set_date(date)
        self.inspiration_view.set_date(date)
        self.summary_view.set_date(date)
        self.summary_view.set_inspiration_cards(self.inspiration_view.get_cards())
        self.weekly_summary_view.set_date(date)
    
    def get_current_date(self) -> datetime:
        """获取当前查看的日期"""
        return self._current_date
