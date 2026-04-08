"""
Dayflow Windows - 主窗口
现代化 Windows 11 风格界面
"""
import logging
from datetime import datetime
from typing import Optional
import sys
import time

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame,
    QLineEdit, QMessageBox, QSystemTrayIcon, QMenu,
    QApplication, QSizePolicy, QSpacerItem, QFileDialog,
    QScrollArea, QProgressBar, QComboBox, QDialog,
    QRadioButton
)
from PySide6.QtCore import QEvent
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QSize, QPoint
from PySide6.QtGui import QIcon, QAction, QFont, QColor, QPalette

# Windows API 用于无边框窗口调整大小
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

import config
from ui.timeline_view import TimelineView
from ui.daily_event_view import DailyEventView
from ui.stats_view import StatsPanel
from ui.themes import (
    get_theme_manager, get_theme, 
    show_information, show_warning, show_critical, show_question,
    create_themed_message_box
)
from core.types import ActivityCard
from core.health_reminder import HealthReminder
from database.storage import StorageManager

logger = logging.getLogger(__name__)


class NoScrollComboBox(QComboBox):
    """禁用鼠标滚轮的ComboBox"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def wheelEvent(self, event):
        """禁用鼠标滚轮事件"""
        event.ignore()


class TitleBarButton(QPushButton):
    """标题栏按钮"""
    
    def __init__(self, text: str, hover_color: str = None, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(46, 32)
        self.setCursor(Qt.PointingHandCursor)
        self._hover_color = hover_color or "#3d3d3d"
        self._is_close = False
        self.apply_theme()
    
    def set_close_button(self, is_close: bool):
        """设置为关闭按钮样式"""
        self._is_close = is_close
        self._hover_color = "#e81123" if is_close else "#3d3d3d"
        self.apply_theme()
    
    def apply_theme(self):
        t = get_theme()
        hover_bg = self._hover_color
        hover_text = "white" if self._is_close else t.text_primary
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {t.text_secondary};
                font-size: 12px;
                font-family: "Segoe MDL2 Assets", "Segoe UI Symbol", sans-serif;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: {hover_text};
            }}
        """)


class CustomTitleBar(QWidget):
    """自定义标题栏 - VS Code 风格"""
    
    minimize_to_tray = Signal()
    minimize_window = Signal()
    maximize_window = Signal()
    close_window = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self._dragging = False
        self._drag_pos = None
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(0)
        
        # 左侧：图标和标题
        self.icon_label = QLabel("⏱️")
        self.icon_label.setFixedWidth(24)
        layout.addWidget(self.icon_label)
        
        self.title_label = QLabel("Dayflow")
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # 右侧：窗口控制按钮
        # 最小化到托盘
        self.tray_btn = TitleBarButton("↓")
        self.tray_btn.setToolTip("最小化到托盘")
        self.tray_btn.clicked.connect(self.minimize_to_tray.emit)
        layout.addWidget(self.tray_btn)
        
        # 最小化
        self.min_btn = TitleBarButton("─")
        self.min_btn.setToolTip("最小化")
        self.min_btn.clicked.connect(self.minimize_window.emit)
        layout.addWidget(self.min_btn)
        
        # 最大化/还原
        self.max_btn = TitleBarButton("□")
        self.max_btn.setToolTip("最大化")
        self.max_btn.clicked.connect(self.maximize_window.emit)
        layout.addWidget(self.max_btn)
        
        # 关闭
        self.close_btn = TitleBarButton("×")
        self.close_btn.set_close_button(True)
        self.close_btn.setToolTip("关闭")
        self.close_btn.clicked.connect(self.close_window.emit)
        layout.addWidget(self.close_btn)
    
    def update_maximize_button(self, is_maximized: bool):
        """更新最大化按钮图标"""
        if is_maximized:
            self.max_btn.setText("❐")
            self.max_btn.setToolTip("还原")
        else:
            self.max_btn.setText("□")
            self.max_btn.setToolTip("最大化")
    
    def apply_theme(self):
        t = get_theme()
        self.setStyleSheet(f"background-color: {t.bg_secondary};")
        self.icon_label.setStyleSheet(f"font-size: 14px;")
        self.title_label.setStyleSheet(f"""
            color: {t.text_secondary};
            font-size: 12px;
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            padding-left: 4px;
        """)
        # 更新按钮主题
        self.tray_btn.apply_theme()
        self.min_btn.apply_theme()
        self.max_btn.apply_theme()
        self.close_btn.apply_theme()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_pos:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._drag_pos = None
    
    def mouseDoubleClickEvent(self, event):
        """双击最大化/还原"""
        if event.button() == Qt.LeftButton:
            self.maximize_window.emit()


class SidebarButton(QPushButton):
    """侧边栏按钮"""
    
    def __init__(self, text: str, icon_text: str = "", parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_text}  {text}" if icon_text else f"  {text}")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self.apply_theme()
        
        # 监听主题变化
        get_theme_manager().theme_changed.connect(self.apply_theme)
    
    def apply_theme(self):
        t = get_theme()
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t.text_muted};
                border: none;
                border-radius: 0px 10px 10px 0px;
                text-align: left;
                padding-left: 14px;
                font-size: 14px;
                font-weight: 500;
                margin: 2px 8px 2px 0px;
            }}
            QPushButton:hover {{
                background-color: {t.bg_hover};
                color: {t.text_primary};
            }}
            QPushButton:checked {{
                background-color: {t.accent_light};
                color: {t.accent};
                border-left: 3px solid {t.accent};
                padding-left: 11px;
                font-weight: 600;
            }}
        """)


class RecordingIndicator(QWidget):
    """录制状态指示器 - 带实时时长显示"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._recording = False
        self._paused = False
        self._start_time = None
        self._elapsed_seconds = 0
        self._setup_ui()
        get_theme_manager().theme_changed.connect(self._apply_idle_theme)
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # 指示点
        self.dot = QLabel("●")
        layout.addWidget(self.dot)
        
        # 状态文字
        self.status_label = QLabel("未录制")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # 闪烁动画（脉冲效果）
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_state = True
        
        # 时长更新定时器
        self._duration_timer = QTimer(self)
        self._duration_timer.timeout.connect(self._update_duration)
        
        self._apply_idle_theme()
    
    def _format_duration(self, seconds: int) -> str:
        """格式化时长为 HH:MM:SS"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _update_duration(self):
        """更新录制时长显示"""
        if self._recording and not self._paused and self._start_time:
            from datetime import datetime
            elapsed = (datetime.now() - self._start_time).total_seconds()
            self._elapsed_seconds = int(elapsed)
            duration_str = self._format_duration(self._elapsed_seconds)
            self.status_label.setText(f"录制中 {duration_str}")
    
    def _apply_idle_theme(self):
        if not self._recording:
            t = get_theme()
            self.dot.setStyleSheet(f"color: {t.text_muted}; font-size: 10px;")
            self.status_label.setStyleSheet(f"color: {t.text_muted}; font-size: 12px;")
    
    def set_recording(self, recording: bool, paused: bool = False):
        from datetime import datetime
        
        self._recording = recording
        self._paused = paused
        t = get_theme()
        
        if recording and not paused:
            # 开始录制
            if self._start_time is None:
                self._start_time = datetime.now()
                self._elapsed_seconds = 0
            
            self.dot.setStyleSheet(f"color: {t.error}; font-size: 10px;")
            self.status_label.setText("录制中 00:00:00")
            self.status_label.setStyleSheet(f"color: {t.error}; font-size: 12px; font-weight: 600;")
            self._blink_timer.start(800)
            self._duration_timer.start(1000)
            
        elif recording and paused:
            # 暂停
            duration_str = self._format_duration(self._elapsed_seconds)
            self.dot.setStyleSheet(f"color: {t.warning}; font-size: 10px;")
            self.status_label.setText(f"已暂停 {duration_str}")
            self.status_label.setStyleSheet(f"color: {t.warning}; font-size: 12px;")
            self._blink_timer.stop()
            self._duration_timer.stop()
            
        else:
            # 停止
            self._start_time = None
            self._elapsed_seconds = 0
            self.dot.setStyleSheet(f"color: {t.text_muted}; font-size: 10px;")
            self.status_label.setText("未录制")
            self.status_label.setStyleSheet(f"color: {t.text_muted}; font-size: 12px;")
            self._blink_timer.stop()
            self._duration_timer.stop()
    
    def _blink(self):
        """脉冲动画"""
        t = get_theme()
        self._blink_state = not self._blink_state
        if self._blink_state:
            self.dot.setStyleSheet(f"color: {t.error}; font-size: 10px;")
        else:
            self.dot.setStyleSheet(f"color: {t.error}; font-size: 10px; opacity: 0.3;")
    
    def get_elapsed_time(self) -> str:
        """获取当前录制时长字符串"""
        return self._format_duration(self._elapsed_seconds)


class CollapsibleSection(QWidget):
    """可折叠区域组件"""
    
    def __init__(self, title: str, summary: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self._summary = summary
        self._collapsed = True  # 默认折叠
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
    
    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 标题栏（可点击）
        self.header = QFrame()
        self.header.setCursor(Qt.PointingHandCursor)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(20, 14, 20, 14)
        
        # 折叠图标
        self.toggle_icon = QLabel("▶")
        header_layout.addWidget(self.toggle_icon)
        
        # 标题
        self.title_label = QLabel(self._title)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # 摘要（折叠时显示）
        self.summary_label = QLabel(self._summary)
        header_layout.addWidget(self.summary_label)
        
        self.main_layout.addWidget(self.header)
        
        # 内容区域
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 0, 20, 16)
        self.content_layout.setSpacing(12)
        self.content.setVisible(False)  # 默认隐藏
        
        self.main_layout.addWidget(self.content)
        
        # 点击事件
        self.header.mousePressEvent = self._on_header_click
    
    def _on_header_click(self, event):
        self.toggle()
    
    def toggle(self):
        """切换折叠状态"""
        self._collapsed = not self._collapsed
        self.content.setVisible(not self._collapsed)
        self.toggle_icon.setText("▼" if not self._collapsed else "▶")
        self.summary_label.setVisible(self._collapsed)
    
    def set_summary(self, summary: str):
        """更新摘要"""
        self._summary = summary
        self.summary_label.setText(summary)
    
    def add_widget(self, widget: QWidget):
        """添加内容组件"""
        self.content_layout.addWidget(widget)
    
    def add_layout(self, layout):
        """添加布局"""
        self.content_layout.addLayout(layout)
    
    def apply_theme(self):
        t = get_theme()
        self.header.setStyleSheet(f"""
            QFrame {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 12px;
            }}
            QFrame:hover {{
                background-color: {t.bg_hover};
            }}
        """)
        self.toggle_icon.setStyleSheet(f"""
            font-size: 12px;
            color: {t.text_muted};
            padding-right: 8px;
        """)
        self.title_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 600;
            color: {t.text_primary};
        """)
        self.summary_label.setStyleSheet(f"""
            font-size: 12px;
            color: {t.text_muted};
        """)
        self.content.setStyleSheet(f"""
            background-color: {t.bg_secondary};
            border: 1px solid {t.border};
            border-top: none;
            border-radius: 0 0 12px 12px;
            margin-top: -12px;
        """)


class SettingsPanel(QWidget):
    """设置面板"""
    
    api_key_saved = Signal(str)
    
    def __init__(self, storage: StorageManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._frames = []  # 存储需要主题化的 frame
        self._titles = []  # 存储标题
        self._descs = []   # 存储描述文字
        self._setup_ui()
        self._load_settings()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
        
        # 保存对 MainWindow 的引用
        self.main_window = parent
    
    def _create_card(self, layout) -> QFrame:
        """创建设置卡片"""
        frame = QFrame()
        frame.setObjectName("settingsCard")
        self._frames.append(frame)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(20, 16, 20, 16)
        frame_layout.setSpacing(10)
        layout.addWidget(frame)
        return frame, frame_layout
    
    def _create_title(self, text: str, layout) -> QLabel:
        """创建卡片标题"""
        label = QLabel(text)
        label.setObjectName("cardTitle")
        label.setMinimumHeight(24)
        self._titles.append(label)
        layout.addWidget(label)
        return label
    
    def _create_desc(self, text: str, layout) -> QLabel:
        """创建描述文字"""
        label = QLabel(text)
        label.setObjectName("cardDesc")
        label.setWordWrap(True)
        label.setMinimumHeight(20)
        self._descs.append(label)
        layout.addWidget(label)
        return label
    
    def _setup_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.NoFrame)
        
        # 滚动区域内容
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)  # 增加卡片间距
        
        # 页面标题
        self.page_title = QLabel("⚙️ 设置")
        self.page_title.setMinimumHeight(40)
        layout.addWidget(self.page_title)
        
        # === API 设置 ===
        api_frame, api_layout = self._create_card(layout)
        self._create_title("🔑 API 设置", api_layout)
        
        api_desc = QLabel("支持 OpenAI 兼容接口（心流API、OpenAI、DeepSeek、本地模型等）")
        api_desc.setObjectName("cardDesc")
        api_desc.setWordWrap(True)
        self._descs.append(api_desc)
        api_layout.addWidget(api_desc)
        
        # GLM 模型选择
        glm_label = QLabel("GLM 模型（当前测试完善的模型）")
        glm_label.setObjectName("cardDesc")
        self._descs.append(glm_label)
        api_layout.addWidget(glm_label)
        
        glm_row = QHBoxLayout()
        self.use_glm_radio = QRadioButton("使用 GLM 模型")
        self.use_glm_radio.setChecked(True)
        self.use_glm_radio.toggled.connect(self._on_glm_mode_changed)
        glm_row.addWidget(self.use_glm_radio)
        
        self.use_custom_radio = QRadioButton("使用其他模型")
        self.use_custom_radio.setChecked(False)
        self.use_custom_radio.toggled.connect(self._on_glm_mode_changed)
        glm_row.addWidget(self.use_custom_radio)
        glm_row.addStretch()
        api_layout.addLayout(glm_row)
        
        # API URL 输入框
        api_url_row = QHBoxLayout()
        api_url_label = QLabel("API 地址")
        api_url_label.setObjectName("cardDesc")
        self._descs.append(api_url_label)
        api_url_row.addWidget(api_url_label)
        api_url_row.addStretch()
        
        self.reset_api_url_btn = QPushButton("恢复默认 URL")
        self.reset_api_url_btn.setCursor(Qt.PointingHandCursor)
        self.reset_api_url_btn.clicked.connect(self._reset_api_url)
        api_url_row.addWidget(self.reset_api_url_btn)
        api_layout.addLayout(api_url_row)
        
        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText("https://api.openai.com/v1")
        self.api_url_input.setMinimumHeight(40)
        api_layout.addWidget(self.api_url_input)
        
        # API Key 输入框
        api_key_label = QLabel("API Key")
        api_key_label.setObjectName("cardDesc")
        self._descs.append(api_key_label)
        api_layout.addWidget(api_key_label)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setMinimumHeight(40)
        api_layout.addWidget(self.api_key_input)
        
        # 模型选择下拉框（GLM模型时显示）
        model_label = QLabel("视觉模型")
        model_label.setObjectName("cardDesc")
        self._descs.append(model_label)
        api_layout.addWidget(model_label)
        
        self.api_model_combo = NoScrollComboBox()
        self.api_model_combo.setMinimumHeight(40)
        self.glm_models = [
            ("glm-4.6v", "GLM-4.6V (推荐)", True),
            ("glm-4.6v-flash", "GLM-4.6V-Flash (快速)", True),
            ("glm-4.6v-flashx", "GLM-4.6V-FlashX (极速)", True),
            ("glm-4v-flash", "GLM-4V-Flash (免费)", False),
            ("glm-4.1v-thinking-flashx", "GLM-4.1V-Thinking-FlashX (推理)", False),
            ("glm-4.1v-thinking-flash", "GLM-4.1V-Thinking-Flash (免费)", False),
        ]
        for model_id, model_name, _ in self.glm_models:
            self.api_model_combo.addItem(model_name, model_id)
        self.api_model_combo.currentIndexChanged.connect(self._on_model_changed)
        api_layout.addWidget(self.api_model_combo)
        
        self.api_model_input = QLineEdit()
        self.api_model_input.setPlaceholderText("请输入视觉模型名称，如: gpt-4o")
        self.api_model_input.setMinimumHeight(40)
        self.api_model_input.hide()
        api_layout.addWidget(self.api_model_input)
        
        # 视觉模型思考模式开关
        self.visual_thinking_label = QLabel("视觉模型思考模式")
        self.visual_thinking_label.setObjectName("cardDesc")
        self._descs.append(self.visual_thinking_label)
        api_layout.addWidget(self.visual_thinking_label)
        
        self.visual_thinking_combo = NoScrollComboBox()
        self.visual_thinking_combo.setMinimumHeight(40)
        self.visual_thinking_combo.addItem("关闭 (推荐)", "disabled")
        self.visual_thinking_combo.addItem("开启", "enabled")
        api_layout.addWidget(self.visual_thinking_combo)
        
        # 每日总结模型选择下拉框
        self.summary_model_label = QLabel("每日总结模型")
        self.summary_model_label.setObjectName("cardDesc")
        self._descs.append(self.summary_model_label)
        api_layout.addWidget(self.summary_model_label)
        
        self.summary_model_combo = NoScrollComboBox()
        self.summary_model_combo.setMinimumHeight(40)
        self.summary_models = [
            ("glm-4-flash-250414", "GLM-4-Flash (免费，推荐)"),
            ("glm-4-flashx-250414", "GLM-4-FlashX (极速免费)"),
            ("glm-4.5-flash", "GLM-4.5-Flash (快速)"),
            ("glm-4.5-air", "GLM-4.5-Air (轻量)"),
            ("glm-4.5-airx", "GLM-4.5-AirX (极速)"),
            ("glm-4.6", "GLM-4.6 (标准)"),
            ("glm-4.7", "GLM-4.7 (高级)"),
            ("glm-4.7-flash", "GLM-4.7-Flash (快速高级)"),
            ("glm-4.7-flashx", "GLM-4.7-FlashX (极速高级)"),
            ("glm-5", "GLM-5 (旗舰)"),
            ("glm-5-turbo", "GLM-5-Turbo (旗舰快速)"),
        ]
        for model_id, model_name in self.summary_models:
            self.summary_model_combo.addItem(model_name, model_id)
        api_layout.addWidget(self.summary_model_combo)
        
        self.summary_model_input = QLineEdit()
        self.summary_model_input.setPlaceholderText("请输入每日总结模型名称，如: gpt-4")
        self.summary_model_input.setMinimumHeight(40)
        self.summary_model_input.hide()
        api_layout.addWidget(self.summary_model_input)
        
        # 每日总结模型思考模式开关（GLM模型时显示）
        self.summary_thinking_label = QLabel("每日总结思考模式")
        self.summary_thinking_label.setObjectName("cardDesc")
        self._descs.append(self.summary_thinking_label)
        api_layout.addWidget(self.summary_thinking_label)
        
        self.summary_thinking_combo = NoScrollComboBox()
        self.summary_thinking_combo.setMinimumHeight(40)
        self.summary_thinking_combo.addItem("关闭", "disabled")
        self.summary_thinking_combo.addItem("开启 (推荐)", "enabled")
        api_layout.addWidget(self.summary_thinking_combo)
        
        # 按钮行
        key_row = QHBoxLayout()
        key_row.setSpacing(10)
        
        self.save_btn = QPushButton("保存配置")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setFixedSize(100, 40)
        self.save_btn.clicked.connect(self._save_api_config)
        key_row.addWidget(self.save_btn)
        
        self.test_btn = QPushButton("测试连接")
        self.test_btn.setCursor(Qt.PointingHandCursor)
        self.test_btn.setFixedSize(100, 40)
        self.test_btn.clicked.connect(self._test_connection)
        key_row.addWidget(self.test_btn)
        
        key_row.addStretch()
        api_layout.addLayout(key_row)
        
        # 测试结果
        self.test_result_label = QLabel("")
        self.test_result_label.setWordWrap(True)
        self.test_result_label.setMinimumHeight(24)
        self.test_result_label.hide()
        api_layout.addWidget(self.test_result_label)
        
        # === 外观 + 录制设置（合并为一行两列）===
        settings_row = QHBoxLayout()
        settings_row.setSpacing(16)
        
        # 外观设置
        theme_frame = QFrame()
        theme_frame.setObjectName("settingsCard")
        self._frames.append(theme_frame)
        theme_layout = QVBoxLayout(theme_frame)
        theme_layout.setContentsMargins(20, 16, 20, 16)
        theme_layout.setSpacing(10)
        
        self._create_title("🎨 外观：点击切换明暗主题", theme_layout)
        
        theme_content = QHBoxLayout()
        self.theme_label = QLabel("主题模式")
        self.theme_label.setObjectName("cardDesc")
        self._descs.append(self.theme_label)
        theme_content.addWidget(self.theme_label)
        theme_content.addStretch()
        
        self.theme_toggle = QPushButton("🌙 暗色")
        self.theme_toggle.setCursor(Qt.PointingHandCursor)
        self.theme_toggle.setFixedSize(90, 34)
        self.theme_toggle.clicked.connect(self._toggle_theme)
        theme_content.addWidget(self.theme_toggle)
        theme_layout.addLayout(theme_content)
        
        settings_row.addWidget(theme_frame)
        
        # 录制设置
        record_frame = QFrame()
        record_frame.setObjectName("settingsCard")
        self._frames.append(record_frame)
        record_layout = QVBoxLayout(record_frame)
        record_layout.setContentsMargins(20, 16, 20, 16)
        record_layout.setSpacing(10)
        
        self._create_title("🎬 录制", record_layout)
        fps = 1.0 / config.RECORD_FRAME_INTERVAL
        record_desc = QLabel(f"帧间隔: {config.RECORD_FRAME_INTERVAL}秒/帧 (FPS: {fps:.2f}) | 切片: {config.CHUNK_DURATION_SECONDS}秒")
        record_desc.setObjectName("cardDesc")
        self._descs.append(record_desc)
        record_layout.addWidget(record_desc)

        monitor_row = QHBoxLayout()
        monitor_label = QLabel("录制显示器")
        monitor_label.setObjectName("cardDesc")
        self._descs.append(monitor_label)
        monitor_row.addWidget(monitor_label)
        monitor_row.addStretch()

        self.monitor_combo = NoScrollComboBox()
        self.monitor_combo.setMinimumHeight(34)
        self.monitor_combo.setMinimumWidth(150)
        self._populate_monitor_options()
        monitor_row.addWidget(self.monitor_combo)
        record_layout.addLayout(monitor_row)

        self.monitor_save_btn = QPushButton("保存录制设置")
        self.monitor_save_btn.setCursor(Qt.PointingHandCursor)
        self.monitor_save_btn.setFixedHeight(36)
        self.monitor_save_btn.clicked.connect(self._save_recording_settings)
        record_layout.addWidget(self.monitor_save_btn)
        
        settings_row.addWidget(record_frame)
        layout.addLayout(settings_row)
        
        # === 数据管理 ===
        data_frame, data_layout = self._create_card(layout)
        self._create_title("💾 数据管理", data_layout)
        self._create_desc("导出或导入您的所有活动数据", data_layout)
        
        data_row = QHBoxLayout()
        data_row.setSpacing(10)
        
        self.export_btn = QPushButton("📤 导出数据")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setFixedHeight(38)
        self.export_btn.clicked.connect(self._export_data)
        data_row.addWidget(self.export_btn)
        
        self.import_btn = QPushButton("📥 导入数据")
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.setFixedHeight(38)
        self.import_btn.clicked.connect(self._import_data)
        data_row.addWidget(self.import_btn)
        
        self.dashboard_btn = QPushButton("📊 导出仪表盘")
        self.dashboard_btn.setCursor(Qt.PointingHandCursor)
        self.dashboard_btn.setFixedHeight(38)
        self.dashboard_btn.clicked.connect(self._export_dashboard)
        data_row.addWidget(self.dashboard_btn)
        
        data_row.addStretch()
        data_layout.addLayout(data_row)
        
        # === 开机启动 ===
        autostart_frame, autostart_layout = self._create_card(layout)
        self._create_title("🚀 开机启动", autostart_layout)
        
        autostart_desc = QLabel("开机时自动启动 Dayflow 并最小化到系统托盘")
        autostart_desc.setObjectName("cardDesc")
        self._descs.append(autostart_desc)
        autostart_layout.addWidget(autostart_desc)
        
        # 开机启动按钮
        autostart_btn_row = QHBoxLayout()
        autostart_btn_row.setSpacing(10)
        
        self.autostart_btn = QPushButton("⚪ 未启用")
        self.autostart_btn.setCursor(Qt.PointingHandCursor)
        self.autostart_btn.setFixedHeight(38)
        self.autostart_btn.setCheckable(True)
        self.autostart_btn.clicked.connect(self._toggle_autostart)
        autostart_btn_row.addWidget(self.autostart_btn)
        
        self.autostart_status = QLabel("")
        self.autostart_status.setObjectName("cardDesc")
        self._descs.append(self.autostart_status)
        autostart_btn_row.addWidget(self.autostart_status)
        
        autostart_btn_row.addStretch()
        autostart_layout.addLayout(autostart_btn_row)
        
        # 初始化自启动状态
        self._init_autostart_status()
        
        # === 分析设置 ===
        analysis_frame, analysis_layout = self._create_card(layout)
        self._create_title("📊 分析设置", analysis_layout)
        analysis_desc = QLabel("设置视频分析的批次大小，控制每次分析的视频数量")
        analysis_desc.setObjectName("cardDesc")
        self._descs.append(analysis_desc)
        analysis_layout.addWidget(analysis_desc)
        
        # 批次切片数量设置
        batch_chunk_row = QHBoxLayout()
        batch_chunk_label = QLabel("批次切片数量（个）")
        batch_chunk_label.setObjectName("inputLabel")
        self._descs.append(batch_chunk_label)
        batch_chunk_row.addWidget(batch_chunk_label)
        
        self.batch_chunk_input = QLineEdit()
        self.batch_chunk_input.setPlaceholderText("3")
        self.batch_chunk_input.setMinimumHeight(40)
        self.batch_chunk_input.setMaximumWidth(100)
        batch_chunk_row.addWidget(self.batch_chunk_input)
        batch_chunk_row.addStretch()
        analysis_layout.addLayout(batch_chunk_row)
        
        # 说明文字
        batch_hint = QLabel("较大的值会减少分析频率但每次处理时间更长，较小的值会增加分析频率")
        batch_hint.setObjectName("cardDesc")
        batch_hint.setStyleSheet("font-size: 11px; color: #888;")
        self._descs.append(batch_hint)
        analysis_layout.addWidget(batch_hint)
        
        # 保存按钮
        analysis_btn_row = QHBoxLayout()
        analysis_btn_row.addStretch()
        
        self.analysis_save_btn = QPushButton("保存分析设置")
        self.analysis_save_btn.setCursor(Qt.PointingHandCursor)
        self.analysis_save_btn.setFixedHeight(38)
        self.analysis_save_btn.clicked.connect(self._save_analysis_config)
        analysis_btn_row.addWidget(self.analysis_save_btn)
        
        analysis_layout.addLayout(analysis_btn_row)
        
        # === 健康提醒设置 ===
        health_frame, health_layout = self._create_card(layout)
        self._create_title("💪 健康提醒", health_layout)
        health_desc = QLabel("自动检测您的活动状态并提醒您适时休息")
        health_desc.setObjectName("cardDesc")
        self._descs.append(health_desc)
        health_layout.addWidget(health_desc)
        
        # 启用开关行
        health_enable_row = QHBoxLayout()
        self.health_enable_label = QLabel("启用健康提醒")
        self.health_enable_label.setObjectName("cardDesc")
        self._descs.append(self.health_enable_label)
        health_enable_row.addWidget(self.health_enable_label)
        health_enable_row.addStretch()
        
        self.health_enable_btn = QPushButton("已开启")
        self.health_enable_btn.setCheckable(True)
        self.health_enable_btn.setCursor(Qt.PointingHandCursor)
        self.health_enable_btn.setFixedSize(72, 30)
        self.health_enable_btn.clicked.connect(self._toggle_health_reminder)
        health_enable_row.addWidget(self.health_enable_btn)
        health_layout.addLayout(health_enable_row)
        
        # 工作阈值设置
        work_threshold_row = QHBoxLayout()
        work_threshold_label = QLabel("连续工作提醒阈值（分钟）")
        work_threshold_label.setObjectName("inputLabel")
        self._descs.append(work_threshold_label)
        work_threshold_row.addWidget(work_threshold_label)
        
        self.work_threshold_input = QLineEdit()
        self.work_threshold_input.setPlaceholderText("90")
        self.work_threshold_input.setMinimumHeight(40)
        self.work_threshold_input.setMaximumWidth(100)
        work_threshold_row.addWidget(self.work_threshold_input)
        work_threshold_row.addStretch()
        health_layout.addLayout(work_threshold_row)
        
        # 娱乐阈值设置
        entertainment_threshold_row = QHBoxLayout()
        entertainment_threshold_label = QLabel("连续娱乐提醒阈值（分钟）")
        entertainment_threshold_label.setObjectName("inputLabel")
        self._descs.append(entertainment_threshold_label)
        entertainment_threshold_row.addWidget(entertainment_threshold_label)
        
        self.entertainment_threshold_input = QLineEdit()
        self.entertainment_threshold_input.setPlaceholderText("60")
        self.entertainment_threshold_input.setMinimumHeight(40)
        self.entertainment_threshold_input.setMaximumWidth(100)
        entertainment_threshold_row.addWidget(self.entertainment_threshold_input)
        entertainment_threshold_row.addStretch()
        health_layout.addLayout(entertainment_threshold_row)
        
        # 冷却时间设置
        cooldown_row = QHBoxLayout()
        cooldown_label = QLabel("提醒冷却时间（分钟）")
        cooldown_label.setObjectName("inputLabel")
        self._descs.append(cooldown_label)
        cooldown_row.addWidget(cooldown_label)
        
        self.cooldown_input = QLineEdit()
        self.cooldown_input.setPlaceholderText("15")
        self.cooldown_input.setMinimumHeight(40)
        self.cooldown_input.setMaximumWidth(100)
        cooldown_row.addWidget(self.cooldown_input)
        cooldown_row.addStretch()
        health_layout.addLayout(cooldown_row)
        
        # 测试和保存按钮
        health_btn_row = QHBoxLayout()
        health_btn_row.addStretch()
        
        self.test_reminder_btn = QPushButton("🔔 测试提醒")
        self.test_reminder_btn.setCursor(Qt.PointingHandCursor)
        self.test_reminder_btn.setFixedHeight(38)
        self.test_reminder_btn.clicked.connect(self._test_health_reminder)
        health_btn_row.addWidget(self.test_reminder_btn)
        
        self.health_save_btn = QPushButton("保存健康提醒设置")
        self.health_save_btn.setCursor(Qt.PointingHandCursor)
        self.health_save_btn.setFixedHeight(38)
        self.health_save_btn.clicked.connect(self._save_health_reminder_config)
        health_btn_row.addWidget(self.health_save_btn)
        
        health_layout.addLayout(health_btn_row)
        
        # === 日志查看 ===
        log_frame, log_layout = self._create_card(layout)
        self._create_title("📋 运行日志", log_layout)
        
        log_desc = QLabel("查看应用运行日志，便于排查问题")
        log_desc.setObjectName("cardDesc")
        self._descs.append(log_desc)
        log_layout.addWidget(log_desc)
        
        # 日志按钮行
        log_btn_row = QHBoxLayout()
        log_btn_row.setSpacing(10)
        
        self.view_log_btn = QPushButton("📄 查看日志")
        self.view_log_btn.setCursor(Qt.PointingHandCursor)
        self.view_log_btn.setFixedHeight(38)
        self.view_log_btn.clicked.connect(self._toggle_log_view)
        log_btn_row.addWidget(self.view_log_btn)
        
        self.refresh_log_btn = QPushButton("🔄 刷新")
        self.refresh_log_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_log_btn.setFixedHeight(38)
        self.refresh_log_btn.clicked.connect(self._refresh_log)
        self.refresh_log_btn.hide()
        log_btn_row.addWidget(self.refresh_log_btn)
        
        self.open_log_folder_btn = QPushButton("📂 打开日志目录")
        self.open_log_folder_btn.setCursor(Qt.PointingHandCursor)
        self.open_log_folder_btn.setFixedHeight(38)
        self.open_log_folder_btn.clicked.connect(self._open_log_folder)
        log_btn_row.addWidget(self.open_log_folder_btn)
        
        log_btn_row.addStretch()
        log_layout.addLayout(log_btn_row)
        
        # 日志显示区域（初始隐藏）
        from PySide6.QtWidgets import QTextEdit
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(300)
        self.log_text.hide()
        self.log_text.setPlaceholderText("点击「查看日志」加载日志内容...")
        log_layout.addWidget(self.log_text)
        
        # === 关于 ===
        about_frame, about_layout = self._create_card(layout)
        self._create_title("ℹ️ 关于 Dayflow", about_layout)
        
        about_text = QLabel("智能时间追踪与生产力分析工具\n支持灵感收集与事件总结")
        about_text.setObjectName("cardDesc")
        about_text.setWordWrap(True)
        self._descs.append(about_text)
        about_layout.addWidget(about_text)
        
        # 底部留白
        layout.addSpacing(20)
        
        # 设置滚动区域
        self.scroll.setWidget(scroll_content)
        main_layout.addWidget(self.scroll)
    
    def apply_theme(self):
        """应用主题"""
        t = get_theme()
        
        # 滚动区域
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {t.bg_primary};
                border: none;
            }}
        """)
        
        # 页面标题 - 28px, 700
        self.page_title.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 700;
            color: {t.text_primary};
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            padding: 4px 0;
        """)
        
        # 所有卡片
        for frame in self._frames:
            frame.setStyleSheet(f"""
                QFrame#settingsCard {{
                    background-color: {t.bg_secondary};
                    border: 1px solid {t.border};
                    border-radius: 12px;
                }}
            """)
        
        # 标题
        for title in self._titles:
            title.setStyleSheet(f"""
                font-size: 15px;
                font-weight: 600;
                color: {t.text_primary};
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                padding: 2px 0;
            """)
        
        # 描述文字
        for desc in self._descs:
            desc.setStyleSheet(f"""
                font-size: 13px;
                color: {t.text_secondary};
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                padding: 2px 0;
            """)
        
        # API 输入框样式
        api_input_style = f"""
            QLineEdit {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                color: {t.text_primary};
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }}
            QLineEdit:focus {{
                border-color: {t.accent};
            }}
        """
        self.api_url_input.setStyleSheet(api_input_style)
        self.api_key_input.setStyleSheet(api_input_style)
        self.api_model_input.setStyleSheet(api_input_style)
        self.summary_model_input.setStyleSheet(api_input_style)
        
        # 分析设置输入框样式
        self.batch_chunk_input.setStyleSheet(api_input_style)
        self.work_threshold_input.setStyleSheet(api_input_style)
        self.entertainment_threshold_input.setStyleSheet(api_input_style)
        self.cooldown_input.setStyleSheet(api_input_style)
        
        # 恢复默认按钮样式
        reset_btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {t.accent};
                border: 1px solid {t.accent};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }}
            QPushButton:hover {{
                background-color: {t.accent};
                color: white;
            }}
        """
        self.reset_api_url_btn.setStyleSheet(reset_btn_style)
        
        # 单选按钮样式
        radio_style = f"""
            QRadioButton {{
                color: {t.text_primary};
                font-size: 14px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {t.border};
                border-radius: 9px;
                background-color: {t.bg_tertiary};
            }}
            QRadioButton::indicator:checked {{
                background-color: {t.accent};
                border-color: {t.accent};
            }}
            QRadioButton::indicator:checked:hover {{
                background-color: {t.accent};
            }}
            QRadioButton:hover {{
                color: {t.text_primary};
            }}
        """
        self.use_glm_radio.setStyleSheet(radio_style)
        self.use_custom_radio.setStyleSheet(radio_style)
        
        # 模型下拉框样式
        combo_style = f"""
            QComboBox {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                color: {t.text_primary};
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }}
            QComboBox:focus {{
                border-color: {t.accent};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {t.text_secondary};
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                selection-background-color: {t.accent};
                color: {t.text_primary};
            }}
        """
        self.api_model_combo.setStyleSheet(combo_style)
        self.visual_thinking_combo.setStyleSheet(combo_style)
        self.summary_model_combo.setStyleSheet(combo_style)
        self.summary_thinking_combo.setStyleSheet(combo_style)
        
        # 主要按钮（保存）
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.accent};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {t.accent_hover};
            }}
        """)
        
        # 测试按钮
        self.test_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.success};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
            QPushButton:disabled {{
                background-color: {t.text_muted};
            }}
        """)
        
        # 主题切换按钮
        self.theme_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {t.bg_hover};
            }}
        """)

        combo_style = f"""
            QComboBox {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
            }}
            QComboBox:focus {{
                border-color: {t.accent};
            }}
            QComboBox QAbstractItemView {{
                background-color: {t.bg_secondary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                selection-background-color: {t.accent};
            }}
        """
        if hasattr(self, 'monitor_combo'):
            self.monitor_combo.setStyleSheet(combo_style)
        
        # 健康提醒输入框样式
        health_input_style = f"""
            QLineEdit {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                color: {t.text_primary};
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }}
            QLineEdit:focus {{
                border-color: {t.accent};
            }}
        """
        if hasattr(self, 'work_threshold_input'):
            self.work_threshold_input.setStyleSheet(health_input_style)
        if hasattr(self, 'entertainment_threshold_input'):
            self.entertainment_threshold_input.setStyleSheet(health_input_style)
        if hasattr(self, 'cooldown_input'):
            self.cooldown_input.setStyleSheet(health_input_style)
        
        # 分析设置保存按钮
        if hasattr(self, 'analysis_save_btn'):
            self.analysis_save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.accent};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    padding: 0 20px;
                }}
                QPushButton:hover {{
                    background-color: {t.accent_hover};
                }}
            """)
        
        # 健康提醒保存按钮
        if hasattr(self, 'health_save_btn'):
            self.health_save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.accent};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    padding: 0 20px;
                }}
                QPushButton:hover {{
                    background-color: {t.accent_hover};
                }}
            """)
        
        # 测试提醒按钮
        if hasattr(self, 'test_reminder_btn'):
            self.test_reminder_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.bg_tertiary};
                    color: {t.text_primary};
                    border: 1px solid {t.border};
                    border-radius: 8px;
                    font-size: 13px;
                    padding: 0 16px;
                }}
                QPushButton:hover {{
                    background-color: {t.bg_hover};
                    border-color: {t.accent};
                }}
            """)
        
        # 数据管理按钮
        data_btn_style = f"""
            QPushButton {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                font-size: 13px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {t.bg_hover};
                border-color: {t.accent};
            }}
        """
        self.export_btn.setStyleSheet(data_btn_style)
        self.import_btn.setStyleSheet(data_btn_style)
        self.dashboard_btn.setStyleSheet(data_btn_style)
        if hasattr(self, 'monitor_save_btn'):
            self.monitor_save_btn.setStyleSheet(data_btn_style)
        
        # 日志按钮样式
        log_btn_style = f"""
            QPushButton {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                font-size: 13px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {t.bg_hover};
                border-color: {t.accent};
            }}
        """
        self.view_log_btn.setStyleSheet(log_btn_style)
        self.refresh_log_btn.setStyleSheet(log_btn_style)
        self.open_log_folder_btn.setStyleSheet(log_btn_style)
        
        # 日志文本框样式
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 12px;
                font-size: 12px;
                font-family: "Consolas", "Monaco", "Microsoft YaHei", monospace;
                line-height: 1.5;
            }}
        """)
    
    def _populate_monitor_options(self):
        """填充显示器选项。"""
        self.monitor_combo.clear()
        screens = QApplication.screens()
        if not screens:
            self.monitor_combo.addItem("显示器 1", 0)
            return

        for idx, screen in enumerate(screens):
            geom = screen.geometry()
            label = f"显示器 {idx + 1} ({geom.width()}x{geom.height()})"
            self.monitor_combo.addItem(label, idx)

    def _save_recording_settings(self):
        """保存录制相关配置。"""
        output_idx = self.monitor_combo.currentData()
        if output_idx is None:
            output_idx = 0
        self.storage.set_setting("record_output_idx", str(output_idx))
        show_information(self, "成功", "录制显示器设置已保存，下次开始录制时生效")

    def _load_settings(self):
        # 加载 GLM 模式设置
        use_glm = self.storage.get_setting("use_glm_model", "true") == "true"
        self.use_glm_radio.setChecked(use_glm)
        self.use_custom_radio.setChecked(not use_glm)
        
        # 加载 API 设置
        api_url = self.storage.get_setting("api_url", config.API_BASE_URL)
        api_key = self.storage.get_setting("api_key", "")
        api_model = self.storage.get_setting("api_model", config.API_MODEL)
        
        self.api_url_input.setText(api_url)
        self.api_key_input.setText(api_key)
        
        # 设置模型下拉框选中项
        model_index = self.api_model_combo.findData(api_model)
        if model_index >= 0:
            self.api_model_combo.setCurrentIndex(model_index)
        
        # 加载自定义模型名称（非GLM模式）
        custom_api_model = self.storage.get_setting("custom_api_model", "")
        self.api_model_input.setText(custom_api_model)
        
        # 加载每日总结模型设置
        summary_model = self.storage.get_setting("daily_summary_model", config.DAILY_SUMMARY_MODEL)
        summary_model_index = self.summary_model_combo.findData(summary_model)
        if summary_model_index >= 0:
            self.summary_model_combo.setCurrentIndex(summary_model_index)
        
        # 加载自定义每日总结模型名称（非GLM模式）
        custom_summary_model = self.storage.get_setting("custom_summary_model", "")
        self.summary_model_input.setText(custom_summary_model)
        
        # 加载视觉模型思考模式设置
        visual_thinking = self.storage.get_setting("visual_thinking_mode", config.VISUAL_THINKING_MODE)
        visual_thinking_index = self.visual_thinking_combo.findData(visual_thinking)
        if visual_thinking_index >= 0:
            self.visual_thinking_combo.setCurrentIndex(visual_thinking_index)
        
        # 加载每日总结思考模式设置
        summary_thinking = self.storage.get_setting("summary_thinking_mode", config.SUMMARY_THINKING_MODE)
        summary_thinking_index = self.summary_thinking_combo.findData(summary_thinking)
        if summary_thinking_index >= 0:
            self.summary_thinking_combo.setCurrentIndex(summary_thinking_index)
        
        # 根据GLM模式更新UI状态
        self._on_glm_mode_changed()
        
        # 根据模型是否支持 thinking 更新 UI 状态
        if model_index >= 0:
            self._on_model_changed(model_index)
        
        # 加载主题设置
        theme = self.storage.get_setting("theme", "dark")
        self._update_theme_button(theme == "dark")

        # 加载录制显示器设置
        saved_output_idx = self.storage.get_setting("record_output_idx", "0")
        try:
            saved_output_idx = int(saved_output_idx)
        except ValueError:
            saved_output_idx = 0
        combo_index = self.monitor_combo.findData(saved_output_idx)
        if combo_index >= 0:
            self.monitor_combo.setCurrentIndex(combo_index)
        
        # 加载分析设置
        batch_chunk = self.storage.get_setting("batch_chunk_count", str(config.BATCH_CHUNK_COUNT))
        self.batch_chunk_input.setText(batch_chunk)
        
        # 加载健康提醒设置
        health_enabled = self.storage.get_setting("health_reminder_enabled", "true") == "true"
        self.health_enable_btn.setChecked(health_enabled)
        self._update_health_reminder_button()
        
        work_threshold = self.storage.get_setting("health_work_threshold", str(config.HEALTH_REMINDER_WORK_THRESHOLD))
        self.work_threshold_input.setText(work_threshold)
        
        entertainment_threshold = self.storage.get_setting("health_entertainment_threshold", str(config.HEALTH_REMINDER_ENTERTAINMENT_THRESHOLD))
        self.entertainment_threshold_input.setText(entertainment_threshold)
        
        cooldown = self.storage.get_setting("health_cooldown", str(config.HEALTH_REMINDER_COOLDOWN))
        self.cooldown_input.setText(cooldown)
    
    def _reset_api_url(self):
        """恢复 API 地址为默认值"""
        default_url = "https://open.bigmodel.cn/api/paas/v4"
        self.api_url_input.setText(default_url)
        self.api_url_input.selectAll()
        show_information(self, "已恢复", f"API 地址已恢复为默认值：\n{default_url}")
    
    def _on_glm_mode_changed(self):
        """GLM模式切换时更新UI状态"""
        use_glm = self.use_glm_radio.isChecked()
        
        if use_glm:
            # 使用GLM模型
            self.api_model_combo.show()
            self.api_model_input.hide()
            self.summary_model_combo.show()
            self.summary_model_input.hide()
            self.visual_thinking_label.show()
            self.visual_thinking_combo.show()
            self.summary_thinking_label.show()
            self.summary_thinking_combo.show()
        else:
            # 使用其他模型
            self.api_model_combo.hide()
            self.api_model_input.show()
            self.summary_model_combo.hide()
            self.summary_model_input.show()
            self.visual_thinking_label.hide()
            self.visual_thinking_combo.hide()
            self.summary_thinking_label.hide()
            self.summary_thinking_combo.hide()
    
    def _on_model_changed(self, index: int):
        """模型选择变化时，更新思考模式的可用状态"""
        if 0 <= index < len(self.glm_models):
            supports_thinking = self.glm_models[index][2]
            self.visual_thinking_combo.setEnabled(supports_thinking)
            if not supports_thinking:
                self.visual_thinking_combo.setCurrentIndex(0)
    
    def _save_api_config(self):
        """保存 API 配置"""
        try:
            use_glm = self.use_glm_radio.isChecked()
            api_url = self.api_url_input.text().strip() or config.API_BASE_URL
            api_key = self.api_key_input.text().strip()
            
            # 保存GLM模式设置
            self.storage.set_setting("use_glm_model", "true" if use_glm else "false")
            
            # 保存通用设置
            self.storage.set_setting("api_url", api_url)
            self.storage.set_setting("api_key", api_key)
            
            if use_glm:
                # GLM模式：使用下拉框选择的模型
                api_model = self.api_model_combo.currentData() or config.API_MODEL
                summary_model = self.summary_model_combo.currentData() or config.DAILY_SUMMARY_MODEL
                visual_thinking_mode = self.visual_thinking_combo.currentData() or "disabled"
                summary_thinking_mode = self.summary_thinking_combo.currentData() or "disabled"
                
                self.storage.set_setting("api_model", api_model)
                self.storage.set_setting("daily_summary_model", summary_model)
                self.storage.set_setting("visual_thinking_mode", visual_thinking_mode)
                self.storage.set_setting("summary_thinking_mode", summary_thinking_mode)
                
                # 更新运行时配置
                config.API_BASE_URL = api_url
                config.API_KEY = api_key
                config.API_MODEL = api_model
                config.DAILY_SUMMARY_MODEL = summary_model
                config.VISUAL_THINKING_MODE = visual_thinking_mode
                config.SUMMARY_THINKING_MODE = summary_thinking_mode
            else:
                # 非GLM模式：使用自定义输入的模型名称
                custom_api_model = self.api_model_input.text().strip() or "gpt-4o"
                custom_summary_model = self.summary_model_input.text().strip() or "gpt-4"
                
                self.storage.set_setting("custom_api_model", custom_api_model)
                self.storage.set_setting("custom_summary_model", custom_summary_model)
                
                # 更新运行时配置（不传递思考模式等参数）
                config.API_BASE_URL = api_url
                config.API_KEY = api_key
                config.API_MODEL = custom_api_model
                config.DAILY_SUMMARY_MODEL = custom_summary_model
                config.VISUAL_THINKING_MODE = "disabled"
                config.SUMMARY_THINKING_MODE = "disabled"
            
            self.api_key_saved.emit(api_key)
            
            # 重新初始化分析管理器以使用新的模型配置
            if self.main_window and self.main_window.analysis_manager:
                logger.info("API 配置已更新，重新初始化分析管理器")
                old_running = self.main_window.analysis_manager.scheduler.is_running
                self.main_window.analysis_manager.stop_scheduler()
                from core.analysis import AnalysisManager
                self.main_window.analysis_manager = AnalysisManager(self.storage)
                if old_running:
                    self.main_window.analysis_manager.start_scheduler()
                    logger.info("分析管理器已重新初始化并恢复运行")
            
            show_information(self, "成功", "API 配置已保存")
            logger.info("API 配置保存成功")
        except Exception as e:
            logger.error(f"保存 API 配置失败: {e}", exc_info=True)
            show_critical(self, "保存失败", f"保存 API 配置时出错：{str(e)}")
    
    def _test_connection(self):
        """测试 API 连接"""
        import asyncio
        from core.llm_provider import DayflowBackendProvider
        
        use_glm = self.use_glm_radio.isChecked()
        api_url = self.api_url_input.text().strip() or config.API_BASE_URL
        api_key = self.api_key_input.text().strip()
        
        if not api_key:
            self._show_test_result(False, "请先输入 API Key")
            return
        
        if use_glm:
            # GLM模式：使用下拉框选择的模型
            api_model = self.api_model_combo.currentData() or config.API_MODEL
            visual_thinking_mode = self.visual_thinking_combo.currentData() or "disabled"
            summary_model = self.summary_model_combo.currentData() or config.DAILY_SUMMARY_MODEL
            summary_thinking_mode = self.summary_thinking_combo.currentData() or "disabled"
        else:
            # 非GLM模式：使用自定义输入的模型名称
            api_model = self.api_model_input.text().strip() or "gpt-4o"
            visual_thinking_mode = "disabled"
            summary_model = self.summary_model_input.text().strip() or "gpt-4"
            summary_thinking_mode = "disabled"
        
        # 禁用按钮，显示加载状态
        t = get_theme()
        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")
        self.test_result_label.setText("正在连接...")
        self.test_result_label.setStyleSheet(f"font-size: 13px; color: {t.text_muted}; padding: 8px 0;")
        self.test_result_label.show()
        
        # 在后台线程执行测试
        import threading
        def run_test():
            # 测试视觉模型
            provider = DayflowBackendProvider(
                api_base_url=api_url,
                api_key=api_key,
                model=api_model,
                thinking_mode=visual_thinking_mode
            )
            loop = asyncio.new_event_loop()
            try:
                visual_success, visual_message = loop.run_until_complete(provider.test_connection(test_image=True))
            finally:
                loop.run_until_complete(provider.close())
                loop.close()
            
            # 测试每日总结模型
            loop = asyncio.new_event_loop()
            try:
                summary_provider = DayflowBackendProvider(
                    api_base_url=api_url,
                    api_key=api_key,
                    model=summary_model,
                    thinking_mode=summary_thinking_mode
                )
                summary_success, summary_message = loop.run_until_complete(summary_provider.test_connection(test_image=False))
                loop.run_until_complete(summary_provider.close())
            finally:
                loop.close()
            
            # 合并测试结果，使用HTML格式，成功绿色，失败红色
            result_parts = []
            if visual_success:
                result_parts.append(f'<span style="color: #10B981;">✓ 视觉模型 ({api_model}): {visual_message}</span>')
            else:
                result_parts.append(f'<span style="color: #EF4444;">✗ 视觉模型 ({api_model}): {visual_message}</span>')
            
            if summary_success:
                result_parts.append(f'<span style="color: #10B981;">✓ 每日总结模型 ({summary_model}): {summary_message}</span>')
            else:
                result_parts.append(f'<span style="color: #EF4444;">✗ 每日总结模型 ({summary_model}): {summary_message}</span>')
            
            message = "<br>".join(result_parts)
            
            # 回到主线程更新 UI
            from PySide6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self, "_show_test_result",
                Qt.QueuedConnection,
                Q_ARG(str, message)
            )
        
        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()
    
    @Slot(str)
    def _show_test_result(self, message: str):
        """显示测试结果"""
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")
        self.test_result_label.show()
        
        self.test_result_label.setStyleSheet("""
            font-size: 13px;
            padding: 8px 0;
        """)
        self.test_result_label.setTextFormat(Qt.RichText)
        self.test_result_label.setText(f"{message}")
    
    def _toggle_theme(self):
        """切换主题"""
        print(f"[主题切换] 开始切换主题...")
        total_start = time.time()
        
        from ui.themes import get_theme_manager
        
        # 禁用更新以减少重绘
        self.setUpdatesEnabled(False)
        
        start_time = time.time()
        theme_manager = get_theme_manager()
        theme_manager.toggle_theme()
        toggle_time = time.time() - start_time
        print(f"[主题切换] theme_manager.toggle_theme() 耗时: {toggle_time*1000:.2f}ms")
        
        start_time = time.time()
        is_dark = theme_manager.is_dark
        self.storage.set_setting("theme", "dark" if is_dark else "light")
        self._update_theme_button(is_dark)
        settings_time = time.time() - start_time
        print(f"[主题切换] 保存设置和更新按钮耗时: {settings_time*1000:.2f}ms")
        
        # 重新启用更新
        self.setUpdatesEnabled(True)
        
        total_time = time.time() - total_start
        print(f"[主题切换] 总耗时: {total_time*1000:.2f}ms")
    
    def _update_theme_button(self, is_dark: bool):
        """更新主题按钮显示"""
        if is_dark:
            self.theme_toggle.setText("🌙 暗色")
        else:
            self.theme_toggle.setText("☀️ 亮色")
    
    def _export_dashboard(self):
        """导出仪表盘 HTML 报告"""
        from ui.date_range_dialog import DateRangeDialog
        from core.dashboard_exporter import DashboardExporter
        
        dialog = DateRangeDialog(self)
        
        def on_export(start_date, end_date):
            try:
                exporter = DashboardExporter(self.storage)
                path = exporter.export_and_open(start_date, end_date)
                show_information(
                    self, "导出成功", 
                    f"仪表盘已导出并在浏览器中打开\n\n文件位置:\n{path}"
                )
            except Exception as e:
                logger.error(f"导出仪表盘失败: {e}")
                show_critical(self, "导出失败", f"导出仪表盘时出错: {e}")
        
        dialog.range_selected.connect(on_export)
        dialog.exec()
    
    def _export_data(self):
        """导出数据"""
        import json
        import shutil
        from pathlib import Path
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出数据",
            f"dayflow_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON 文件 (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            # 获取所有数据
            data = {
                "version": "1.3.0",
                "exported_at": datetime.now().isoformat(),
                "cards": [],
                "inspirations": [],
                "daily_summaries": [],
                "settings": {}
            }
            
            # 导出所有卡片（获取最近一年的数据）
            with self.storage._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM timeline_cards ORDER BY start_time DESC")
                for row in cursor.fetchall():
                    card_data = {
                        "id": row["id"],
                        "category": row["category"],
                        "title": row["title"],
                        "summary": row["summary"],
                        "start_time": row["start_time"],
                        "end_time": row["end_time"],
                        "app_sites_json": row["app_sites_json"],
                        "distractions_json": row["distractions_json"],
                        "productivity_score": row["productivity_score"]
                    }
                    data["cards"].append(card_data)
                
                # 导出灵感卡片（快速记录的灵感、想法、待办）
                cursor = conn.execute("SELECT * FROM inspirations ORDER BY timestamp DESC")
                for row in cursor.fetchall():
                    inspiration_data = {
                        "id": row["id"],
                        "content": row["content"],
                        "timestamp": row["timestamp"],
                        "category": row["category"],
                        "notes_json": row["notes_json"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"]
                    }
                    data["inspirations"].append(inspiration_data)
                
                # 导出每日总结（事件总结和灵感总结）
                cursor = conn.execute("SELECT * FROM daily_summaries ORDER BY date DESC")
                for row in cursor.fetchall():
                    summary_data = {
                        "id": row["id"],
                        "date": row["date"],
                        "event_summary": row["event_summary"],
                        "inspiration_summary": row["inspiration_summary"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"]
                    }
                    data["daily_summaries"].append(summary_data)
                
                # 导出设置
                cursor = conn.execute("SELECT key, value FROM settings")
                for row in cursor.fetchall():
                    if row["key"] != "api_key":  # 不导出敏感信息
                        data["settings"][row["key"]] = row["value"]
            
            # 写入文件
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            show_information(
                self, "导出成功", 
                f"已导出 {len(data['cards'])} 条活动记录\n"
                f"{len(data['inspirations'])} 条灵感记录\n"
                f"{len(data['daily_summaries'])} 条每日总结\n"
                f"保存到: {file_path}"
            )
        except Exception as e:
            show_critical(self, "导出失败", f"导出数据时出错: {e}")
    
    def _import_data(self):
        """导入数据"""
        import json
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入数据",
            "",
            "JSON 文件 (*.json)"
        )
        
        if not file_path:
            return
        
        reply = show_question(
            self, "确认导入",
            "导入数据会与现有数据合并，重复的记录会被跳过。\n是否继续？"
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            imported_cards = 0
            skipped_cards = 0
            imported_inspirations = 0
            skipped_inspirations = 0
            imported_summaries = 0
            skipped_summaries = 0
            
            with self.storage._get_connection() as conn:
                # 导入活动卡片
                for card in data.get("cards", []):
                    # 检查是否已存在（根据时间判断）
                    cursor = conn.execute(
                        "SELECT id FROM timeline_cards WHERE start_time = ? AND end_time = ?",
                        (card["start_time"], card["end_time"])
                    )
                    if cursor.fetchone():
                        skipped_cards += 1
                        continue
                    
                    # 插入新记录
                    conn.execute("""
                        INSERT INTO timeline_cards 
                        (category, title, summary, start_time, end_time, 
                         app_sites_json, distractions_json, productivity_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        card["category"],
                        card["title"],
                        card["summary"],
                        card["start_time"],
                        card["end_time"],
                        card.get("app_sites_json", "[]"),
                        card.get("distractions_json", "[]"),
                        card.get("productivity_score", 0)
                    ))
                    imported_cards += 1
                
                # 导入灵感卡片
                for inspiration in data.get("inspirations", []):
                    # 检查是否已存在（根据内容和时间戳判断）
                    cursor = conn.execute(
                        "SELECT id FROM inspirations WHERE content = ? AND timestamp = ?",
                        (inspiration["content"], inspiration["timestamp"])
                    )
                    if cursor.fetchone():
                        skipped_inspirations += 1
                        continue
                    
                    # 插入新记录
                    conn.execute("""
                        INSERT INTO inspirations 
                        (content, timestamp, category, notes_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        inspiration["content"],
                        inspiration["timestamp"],
                        inspiration.get("category", "灵感"),
                        inspiration.get("notes_json", "[]"),
                        inspiration.get("created_at"),
                        inspiration.get("updated_at")
                    ))
                    imported_inspirations += 1
                
                # 导入每日总结
                for summary in data.get("daily_summaries", []):
                    # 检查是否已存在（根据日期判断）
                    cursor = conn.execute(
                        "SELECT id FROM daily_summaries WHERE date = ?",
                        (summary["date"],)
                    )
                    if cursor.fetchone():
                        skipped_summaries += 1
                        continue
                    
                    # 插入新记录
                    conn.execute("""
                        INSERT INTO daily_summaries 
                        (date, event_summary, inspiration_summary, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        summary["date"],
                        summary.get("event_summary"),
                        summary.get("inspiration_summary"),
                        summary.get("created_at"),
                        summary.get("updated_at")
                    ))
                    imported_summaries += 1
                
                # 导入设置（可选）
                for key, value in data.get("settings", {}).items():
                    if key not in ["api_key", "theme"]:  # 保留用户当前设置
                        conn.execute(
                            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                            (key, value)
                        )
            
            # 构建导入结果消息
            result_messages = []
            if imported_cards > 0 or skipped_cards > 0:
                result_messages.append(f"活动记录: 导入 {imported_cards} 条，跳过 {skipped_cards} 条")
            if imported_inspirations > 0 or skipped_inspirations > 0:
                result_messages.append(f"灵感记录: 导入 {imported_inspirations} 条，跳过 {skipped_inspirations} 条")
            if imported_summaries > 0 or skipped_summaries > 0:
                result_messages.append(f"每日总结: 导入 {imported_summaries} 条，跳过 {skipped_summaries} 条")
            
            total_imported = imported_cards + imported_inspirations + imported_summaries
            total_skipped = skipped_cards + skipped_inspirations + skipped_summaries
            
            show_information(
                self, "导入完成",
                f"成功导入 {total_imported} 条记录\n"
                f"跳过 {total_skipped} 条重复记录\n\n"
                f"{chr(10).join(result_messages)}"
            )
        except Exception as e:
            show_critical(self, "导入失败", f"导入数据时出错: {e}")
    



    def _toggle_log_view(self):
        """切换日志显示"""
        if self.log_text.isVisible():
            self.log_text.hide()
            self.refresh_log_btn.hide()
            self.view_log_btn.setText("📄 查看日志")
        else:
            self._refresh_log()
            self.log_text.show()
            self.refresh_log_btn.show()
            self.view_log_btn.setText("📄 收起日志")
    
    def _refresh_log(self):
        """刷新日志内容"""
        log_file = config.APP_DATA_DIR / "dayflow.log"
        
        if not log_file.exists():
            self.log_text.setPlainText("📭 暂无日志文件")
            return
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                # 读取最后 500 行
                lines = f.readlines()
                last_lines = lines[-500:] if len(lines) > 500 else lines
                content = ''.join(last_lines)
            
            self.log_text.setPlainText(content)
            # 滚动到底部
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            self.log_text.setPlainText(f"❌ 读取日志失败: {e}")
    
    def _open_log_folder(self):
        """打开日志所在目录"""
        import subprocess
        log_dir = config.APP_DATA_DIR
        
        if log_dir.exists():
            # Windows 打开文件夹
            subprocess.run(['explorer', str(log_dir)])
        else:
            show_warning(self, "提示", f"日志目录不存在:\n{log_dir}")
    
    def _init_autostart_status(self):
        """初始化自启动状态"""
        from core.autostart import is_autostart_enabled, is_frozen
        
        if not is_frozen():
            # 开发模式
            self.autostart_btn.setEnabled(False)
            self.autostart_btn.setText("⚪ 仅 EXE 可用")
            self.autostart_status.setText("开发模式下不可用")
        else:
            enabled = is_autostart_enabled()
            self.autostart_btn.setChecked(enabled)
            self._update_autostart_button()
    
    def _toggle_autostart(self):
        """切换开机启动状态"""
        from core.autostart import is_autostart_enabled, enable_autostart, disable_autostart
        
        currently_enabled = is_autostart_enabled()
        
        if currently_enabled:
            # 禁用
            success, msg = disable_autostart()
        else:
            # 启用
            success, msg = enable_autostart()
        
        if success:
            self._update_autostart_button()
            self.autostart_status.setText(msg)
            self.autostart_status.setStyleSheet("color: #10B981; font-size: 13px;")
        else:
            # 恢复按钮状态
            self.autostart_btn.setChecked(currently_enabled)
            self.autostart_status.setText(msg)
            self.autostart_status.setStyleSheet("color: #EF4444; font-size: 13px;")
    
    def _update_autostart_button(self):
        """更新自启动按钮显示"""
        from core.autostart import is_autostart_enabled
        
        t = get_theme()
        enabled = is_autostart_enabled()
        self.autostart_btn.setChecked(enabled)
        
        if enabled:
            self.autostart_btn.setText("🟢 已启用")
            self.autostart_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.accent};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 0 20px;
                }}
                QPushButton:hover {{
                    background-color: {t.accent_hover};
                }}
            """)
        else:
            self.autostart_btn.setText("⚪ 未启用")
            self.autostart_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.accent};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 0 20px;
                }}
                QPushButton:hover {{
                    background-color: {t.accent_hover};
                }}
            """)
    
    def _toggle_health_reminder(self):
        """切换健康提醒状态"""
        currently_enabled = self.health_enable_btn.isChecked()
        
        if currently_enabled:
            # 启用健康提醒
            if hasattr(self, 'health_reminder'):
                self.health_reminder.enable_reminder()
            self.storage.set_setting("health_reminder_enabled", "true")
            logger.info("健康提醒已启用")
        else:
            # 禁用健康提醒
            if hasattr(self, 'health_reminder'):
                self.health_reminder.disable_reminder()
            self.storage.set_setting("health_reminder_enabled", "false")
            logger.info("健康提醒已禁用")
        
        self._update_health_reminder_button()
    
    def _update_health_reminder_button(self):
        """更新健康提醒按钮显示"""
        t = get_theme()
        enabled = self.health_enable_btn.isChecked()
        
        if enabled:
            self.health_enable_btn.setText("已开启")
            self.health_enable_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.success};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    opacity: 0.9;
                }}
            """)
        else:
            self.health_enable_btn.setText("已关闭")
            self.health_enable_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.bg_tertiary};
                    color: {t.text_secondary};
                    border: 1px solid {t.border};
                    border-radius: 6px;
                    font-size: 12px;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background-color: {t.bg_hover};
                    border-color: {t.accent};
                }}
            """)
    
    def _save_analysis_config(self):
        """保存分析配置"""
        try:
            batch_chunk = self.batch_chunk_input.text().strip()
            
            if not batch_chunk:
                show_warning(self, "错误", "请输入批次切片数量")
                return
            
            # 验证数值范围
            try:
                batch_chunk_int = int(batch_chunk)
                
                if batch_chunk_int < 1 or batch_chunk_int > 20:
                    show_warning(self, "错误", "批次切片数量必须在 1-20 之间")
                    return
            except ValueError:
                show_warning(self, "错误", "请输入有效的数字")
                return
            
            # 保存设置
            self.storage.set_setting("batch_chunk_count", batch_chunk)
            
            # 更新运行时配置
            config.BATCH_CHUNK_COUNT = batch_chunk_int
            
            # 重新初始化分析管理器以使用新的批次配置
            if self.main_window and self.main_window.analysis_manager:
                logger.info("批次配置已更新，重新初始化分析管理器")
                old_running = self.main_window.analysis_manager.scheduler.is_running
                self.main_window.analysis_manager.stop_scheduler()
                from core.analysis import AnalysisManager
                self.main_window.analysis_manager = AnalysisManager(self.storage)
                if old_running:
                    self.main_window.analysis_manager.start_scheduler()
                    logger.info("分析管理器已重新初始化并恢复运行")
            
            show_information(self, "成功", "分析配置已保存")
            logger.info(f"分析配置已更新: 批次切片数量={batch_chunk_int}")
        except Exception as e:
            logger.error(f"保存分析配置失败: {e}", exc_info=True)
            show_critical(self, "保存失败", f"保存分析配置时出错：{str(e)}")
    
    def _save_health_reminder_config(self):
        """保存健康提醒配置"""
        try:
            # 验证输入
            work_threshold = self.work_threshold_input.text().strip()
            entertainment_threshold = self.entertainment_threshold_input.text().strip()
            cooldown = self.cooldown_input.text().strip()
            
            if not work_threshold:
                show_warning(self, "错误", "请输入工作阈值")
                return
            if not entertainment_threshold:
                show_warning(self, "错误", "请输入娱乐阈值")
                return
            if not cooldown:
                show_warning(self, "错误", "请输入冷却时间")
                return
            
            # 验证数值范围
            try:
                work_threshold_int = int(work_threshold)
                entertainment_threshold_int = int(entertainment_threshold)
                cooldown_int = int(cooldown)
                
                if work_threshold_int < 10 or work_threshold_int > 300:
                    show_warning(self, "错误", "工作阈值必须在 10-300 分钟之间")
                    return
                if entertainment_threshold_int < 10 or entertainment_threshold_int > 300:
                    show_warning(self, "错误", "娱乐阈值必须在 10-300 分钟之间")
                    return
                if cooldown_int < 1 or cooldown_int > 60:
                    show_warning(self, "错误", "冷却时间必须在 1-60 分钟之间")
                    return
            except ValueError:
                show_warning(self, "错误", "请输入有效的数字")
                return
            
            # 保存设置
            self.storage.set_setting("health_work_threshold", work_threshold)
            self.storage.set_setting("health_entertainment_threshold", entertainment_threshold)
            self.storage.set_setting("health_cooldown", cooldown)
            
            # 更新运行时配置
            config.HEALTH_REMINDER_WORK_THRESHOLD = work_threshold_int
            config.HEALTH_REMINDER_ENTERTAINMENT_THRESHOLD = entertainment_threshold_int
            config.HEALTH_REMINDER_COOLDOWN = cooldown_int
            
            # 重新初始化健康提醒器
            if hasattr(self, 'health_reminder'):
                self.health_reminder.update_config(
                    work_threshold_int, 
                    entertainment_threshold_int, 
                    cooldown_int
                )
            
            logger.info(f"健康提醒配置已更新: 工作={work_threshold_int}分钟, 娱乐={entertainment_threshold_int}分钟, 冷却={cooldown_int}分钟")
            show_information(self, "成功", "健康提醒配置已保存")
            
        except Exception as e:
            logger.error(f"保存健康提醒配置失败: {e}")
            show_critical(self, "错误", f"保存配置时出错: {e}")
    
    def _test_health_reminder(self):
        """测试健康提醒功能"""
        logger.info("开始测试健康提醒功能")
        try:
            work_threshold = self.work_threshold_input.text().strip()
            entertainment_threshold = self.entertainment_threshold_input.text().strip()
            cooldown = self.cooldown_input.text().strip()
            
            logger.info(f"测试参数 - 工作阈值: {work_threshold}, 娱乐阈值: {entertainment_threshold}, 冷却时间: {cooldown}")
            
            if not work_threshold or not entertainment_threshold or not cooldown:
                logger.warning("测试健康提醒失败: 参数不完整")
                show_warning(self, "提示", "请先设置健康提醒的各项参数")
                return
            
            work_threshold_int = int(work_threshold)
            entertainment_threshold_int = int(entertainment_threshold)
            
            message = f"工作阈值：{work_threshold_int} 分钟<br>"
            message += f"娱乐阈值：{entertainment_threshold_int} 分钟<br>"
            message += f"冷却时间：{cooldown} 分钟"
            
            reply = show_question(
                self,
                "健康提醒测试",
                message + "<br><br><b>是否发送测试提醒？</b>"
            )
            
            if reply == QMessageBox.Yes:
                logger.info("用户确认触发测试提醒，开始发送...")
                
                def send_test_reminder(message, reminder_type):
                    logger.info(f"准备发送测试{reminder_type}: {message}")
                    
                    try:
                        has_tray = hasattr(self.main_window, 'tray_icon') if self.main_window else False
                        logger.info(f"检查系统托盘 - has_main_window: {self.main_window is not None}, has_tray: {has_tray}")
                        
                        if has_tray:
                            tray_available = self.main_window.tray_icon.isSystemTrayAvailable()
                            logger.info(f"检查系统托盘可用性 - isSystemTrayAvailable: {tray_available}")
                            
                            if tray_available:
                                logger.info(f"通过系统托盘发送测试{reminder_type}")
                                self.main_window.tray_icon.showMessage(
                                    "健康提醒",
                                    message,
                                    QSystemTrayIcon.Warning,
                                    5000
                                )
                                logger.info(f"成功发送测试{reminder_type}")
                        
                        logger.info(f"使用对话框显示测试{reminder_type}")
                        msg_box = create_themed_message_box(self)
                        msg_box.setWindowTitle("健康提醒")
                        msg_box.setText(message)
                        msg_box.setIcon(QMessageBox.Information)
                        msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
                        msg_box.raise_()
                        
                        timeout_timer = QTimer()
                        timeout_timer.timeout.connect(msg_box.accept)
                        timeout_timer.start(3000)
                        
                        msg_box.exec()
                        timeout_timer.stop()
                        
                        logger.info(f"测试{reminder_type}发送完成")
                        
                    except Exception as e:
                        logger.error(f"发送测试{reminder_type}失败: {e}")
                        show_information(self, "健康提醒", message)
                
                work_message = f"【测试提醒】你已经连续工作了 {work_threshold_int} 分钟，该休息一下了！"
                entertainment_message = f"【测试提醒】你已经连续娱乐了 {entertainment_threshold_int} 分钟，该休息一下了！"
                
                send_test_reminder(work_message, "工作提醒")
                send_test_reminder(entertainment_message, "娱乐提醒")
            
        except ValueError:
            show_warning(self, "错误", "请输入有效的数字")
        except Exception as e:
            logger.error(f"测试健康提醒失败: {e}")
            show_critical(self, "错误", f"测试时出错: {e}")


class MainWindow(QMainWindow):
    """Dayflow 主窗口"""
    
    def __init__(self):
        super().__init__()
        
        logger.info("MainWindow 初始化开始")
        
        # 初始化组件
        self.storage = StorageManager()
        self.recording_manager = None
        self.analysis_manager = None
        self._stopping = False  # 防止重复点击停止按钮
        self._quitting = False  # 标记是否正在退出应用
        
        self._setup_window()
        self._setup_ui()
        self._setup_tray()
        self._setup_timers()
        
        logger.info("MainWindow 初始化完成")
        
        # 应用主题
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
        
        # 延迟加载数据，避免拖慢启动速度
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._load_data)
    
    def _setup_window(self):
        """设置窗口属性"""
        self.setWindowTitle(config.WINDOW_TITLE)
        self.setMinimumSize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)
        self.resize(1100, 700)
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        
        # 设置窗口图标
        self.setWindowIcon(self._create_tray_icon())
    
    def _setup_ui(self):
        """构建 UI"""
        central = QWidget()
        self.setCentralWidget(central)
        
        # 整体垂直布局：标题栏 + 内容区
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        
        # 自定义标题栏
        self.title_bar = CustomTitleBar(self)
        self.title_bar.minimize_to_tray.connect(self._minimize_to_tray)
        self.title_bar.minimize_window.connect(self.showMinimized)
        self.title_bar.maximize_window.connect(self._toggle_maximize)
        self.title_bar.close_window.connect(self.close)
        root_layout.addWidget(self.title_bar)
        
        # 内容区容器
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        root_layout.addWidget(content_widget)
        
        # ===== 侧边栏 =====
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 20)
        sidebar_layout.setSpacing(4)
        
        # Logo
        self.logo = QLabel("🌊 Dayflow")
        sidebar_layout.addWidget(self.logo)
        
        # 导航按钮
        self.nav_timeline = SidebarButton("每日事件", "📊")
        self.nav_timeline.setChecked(True)
        self.nav_timeline.clicked.connect(lambda: self._switch_page(0))
        sidebar_layout.addWidget(self.nav_timeline)
        
        self.nav_stats = SidebarButton("统计", "📈")
        self.nav_stats.clicked.connect(lambda: self._switch_page(1))
        sidebar_layout.addWidget(self.nav_stats)
        
        self.nav_settings = SidebarButton("设置", "⚙️")
        self.nav_settings.clicked.connect(lambda: self._switch_page(2))
        sidebar_layout.addWidget(self.nav_settings)
        
        sidebar_layout.addStretch()
        
        # 录制状态指示器
        self.recording_indicator = RecordingIndicator()
        sidebar_layout.addWidget(self.recording_indicator)
        
        # 分析控制按钮
        self.record_btn = QPushButton("开始追踪")
        self.record_btn.setCursor(Qt.PointingHandCursor)
        self.record_btn.setFixedHeight(44)
        self.record_btn.clicked.connect(self._toggle_recording)
        sidebar_layout.addWidget(self.record_btn)
        
        # 录屏控制按钮
        self.pause_btn = QPushButton("⏸ 暂停录屏")
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setFixedHeight(36)
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.pause_btn.setEnabled(False)
        sidebar_layout.addWidget(self.pause_btn)
        
        content_layout.addWidget(self.sidebar)
        
        # ===== 主内容区 =====
        self.stack = QStackedWidget()
        
        # 每日事件页面
        self.daily_event_view = DailyEventView(storage=self.storage)
        self.daily_event_view.card_selected.connect(self._on_card_selected)
        self.daily_event_view.date_changed.connect(self._on_date_changed)
        self.daily_event_view.export_requested.connect(self._on_export_requested)
        self.daily_event_view.card_updated.connect(self._on_card_updated)
        self.daily_event_view.card_deleted.connect(self._on_card_deleted)
        self.stack.addWidget(self.daily_event_view)
        
        # 统计页面
        self.stats_panel = StatsPanel(self.storage)
        self.stack.addWidget(self.stats_panel)
        
        # 设置页面
        self.settings_panel = SettingsPanel(self.storage, self)
        self.settings_panel.api_key_saved.connect(self._on_api_key_saved)
        self.stack.addWidget(self.settings_panel)
        
        content_layout.addWidget(self.stack)
    
    def _create_tray_icon(self) -> QIcon:
        """创建托盘图标"""
        logger.info("开始创建托盘图标")
        from PySide6.QtGui import QPixmap, QPainter, QBrush, QPen
        from PySide6.QtCore import QRect
        
        # 创建 64x64 的图标
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        logger.info(f"创建托盘图标 pixmap: {not pixmap.isNull()}")
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 画一个蓝色圆形背景
        painter.setBrush(QBrush(QColor("#4F46E5")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 56, 56)
        
        # 画一个白色的时钟图案
        painter.setPen(QPen(QColor("white"), 4))
        painter.drawEllipse(14, 14, 36, 36)
        
        # 时钟指针
        painter.drawLine(32, 32, 32, 20)  # 分针
        painter.drawLine(32, 32, 42, 32)  # 时针
        
        painter.end()
        
        return QIcon(pixmap)
    
    def _setup_tray(self):
        """设置系统托盘"""
        logger.info("开始初始化系统托盘")
        self.tray_icon = QSystemTrayIcon(self)
        logger.info(f"系统托盘对象已创建: {hasattr(self, 'tray_icon')}")
        logger.info(f"系统托盘是否可用: {self.tray_icon.isSystemTrayAvailable()}")
        
        # 创建托盘图标
        tray_icon = self._create_tray_icon()
        self.tray_icon.setIcon(tray_icon)
        self.tray_icon.setToolTip("Dayflow - 智能时间追踪")
        
        tray_menu = QMenu()
        
        # 显示窗口
        show_action = QAction("📱 显示窗口", self)
        show_action.triggered.connect(self._show_window)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        # 追踪控制
        self.tray_record_action = QAction("▶ 开始追踪", self)
        self.tray_record_action.triggered.connect(self._toggle_recording)
        tray_menu.addAction(self.tray_record_action)
        
        # 录屏控制
        self.tray_pause_action = QAction("⏸ 暂停录屏", self)
        self.tray_pause_action.triggered.connect(self._toggle_pause)
        self.tray_pause_action.setEnabled(False)
        tray_menu.addAction(self.tray_pause_action)
        
        tray_menu.addSeparator()
        
        # 退出
        quit_action = QAction("❌ 退出", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        logger.info("系统托盘初始化完成")
    
    def _setup_timers(self):
        """设置定时器"""
        # 刷新时间轴定时器
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_timeline)
        self.refresh_timer.start(30000)  # 每 30 秒刷新
        
        # 健康提醒定时器 - 每 5 分钟检查一次
        self.health_reminder = HealthReminder(
            storage=self.storage
        )
        self.health_timer = QTimer(self)
        self.health_timer.timeout.connect(self._check_health_reminder)
        self.health_timer.start(config.HEALTH_REMINDER_CHECK_INTERVAL)
        
        # 活动状态监控定时器 - 每 5 秒检查一次
        self.activity_timer = QTimer(self)
        self.activity_timer.timeout.connect(self._check_activity_status)
        self.activity_timer.start(5000)  # 每 5 秒检查
    
    def _load_data(self):
        """加载数据"""
        # 加载 API 配置
        api_url = self.storage.get_setting("api_url", "")
        api_key = self.storage.get_setting("api_key", "")
        api_model = self.storage.get_setting("api_model", "")
        
        if api_url:
            config.API_BASE_URL = api_url
        if api_key:
            config.API_KEY = api_key
        if api_model:
            config.API_MODEL = api_model
        
        # 加载健康提醒配置并更新运行时对象
        work_threshold_str = self.storage.get_setting("health_work_threshold")
        entertainment_threshold_str = self.storage.get_setting("health_entertainment_threshold")
        cooldown_str = self.storage.get_setting("health_cooldown")
        
        if work_threshold_str:
            try:
                work_threshold_int = int(work_threshold_str)
                config.HEALTH_REMINDER_WORK_THRESHOLD = work_threshold_int
                if hasattr(self, 'health_reminder'):
                    self.health_reminder.work_threshold_minutes = work_threshold_int
            except ValueError:
                pass
        
        if entertainment_threshold_str:
            try:
                entertainment_threshold_int = int(entertainment_threshold_str)
                config.HEALTH_REMINDER_ENTERTAINMENT_THRESHOLD = entertainment_threshold_int
                if hasattr(self, 'health_reminder'):
                    self.health_reminder.entertainment_threshold_minutes = entertainment_threshold_int
            except ValueError:
                pass
        
        if cooldown_str:
            try:
                cooldown_int = int(cooldown_str)
                config.HEALTH_REMINDER_COOLDOWN = cooldown_int
                if hasattr(self, 'health_reminder'):
                    self.health_reminder.cooldown_minutes = cooldown_int
            except ValueError:
                pass
        
        # 加载今日时间轴
        self._refresh_timeline()
    
    def _refresh_timeline(self):
        """刷新时间轴"""
        # 检查用户当前是否在查看今天的日期
        current_date = self.daily_event_view.get_current_date()
        today = datetime.now()
        today_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        current_date_normalized = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 只有当用户正在查看今天的日期时，才执行刷新
        if current_date_normalized != today_date:
            return
        
        cards = self.storage.get_cards_for_date(today)
        self.daily_event_view.set_cards(cards)
    
    def _check_health_reminder(self):
        """检查是否需要健康提醒"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[健康提醒] _check_health_reminder() 被调用")
        try:
            # 检查健康提醒是否启用
            health_enabled = self.storage.get_setting("health_reminder_enabled", "true") == "true"
            logger.info(f"[健康提醒] 健康提醒启用状态: {health_enabled}")
            if not health_enabled:
                return
            
            result = self.health_reminder.should_notify()
            if result:
                # 发送系统托盘通知
                if hasattr(self, 'tray_icon') and self.tray_icon.isSystemTrayAvailable():
                    self.tray_icon.showMessage(
                        result["title"],
                        result["message"],
                        QSystemTrayIcon.Warning,
                        5000
                    )
                    logger.info(f"健康提醒已通过系统托盘发送: {result['type']}")
                
                # 显示对话框提醒
                logger.info(f"显示对话框健康提醒: {result['type']}")
                msg_box = create_themed_message_box(self)
                msg_box.setWindowTitle(result["title"])
                msg_box.setText(result["message"])
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
                msg_box.raise_()
                
                # 10秒后自动关闭
                timeout_timer = QTimer()
                timeout_timer.timeout.connect(msg_box.accept)
                timeout_timer.start(10000)
                
                msg_box.exec()
                timeout_timer.stop()
                
                logger.info(f"健康提醒已显示对话框: {result['type']}")
        except Exception as e:
            logger.error(f"健康提醒检查失败: {e}")
    
    def _check_activity_status(self):
        """检查活动状态并更新UI"""
        try:
            if not self.recording_manager or not self.recording_manager.is_recording:
                return
            
            # 检查是否自动暂停
            if self.recording_manager.is_auto_paused():
                # 显示自动暂停状态
                if not self.recording_indicator._paused:
                    idle_time = self.recording_manager.get_idle_time()
                    self.recording_indicator.set_recording(True, paused=True)
                    # 更新暂停按钮UI
                    self._update_pause_button(True)
            else:
                # 恢复正常录制
                if self.recording_indicator._paused:
                    self.recording_indicator.set_recording(True, paused=False)
                    # 更新暂停按钮UI
                    self._update_pause_button(False)
        except Exception as e:
            pass
    
    def _switch_page(self, index: int):
        """切换页面"""
        self.stack.setCurrentIndex(index)
        self.nav_timeline.setChecked(index == 0)
        self.nav_stats.setChecked(index == 1)
        self.nav_settings.setChecked(index == 2)
        
        # 切换到统计页面时刷新数据
        if index == 1:
            self.stats_panel.refresh()
    
    def auto_start_recording(self):
        """自启动后自动开始录制（静默模式）"""
        # 从存储中重新加载 API Key，确保使用最新配置
        api_key = self.storage.get_setting("api_key", "")
        if api_key:
            config.API_KEY = api_key
        
        # 检查 API Key 是否已配置
        if not config.API_KEY:
            logger.warning("自启动时未检测到 API Key，跳过自动录制")
            # 静默启动时不弹窗，只在日志中记录
            return
        
        # 延迟一小段时间，确保窗口和组件已完全初始化
        QTimer.singleShot(1000, self._do_auto_start_recording)
    
    def _do_auto_start_recording(self):
        """执行自动开始录制"""
        try:
            # 先启动分析调度器（如果有必要）
            self._start_analysis()
            
            if self.recording_manager is None:
                from core.recorder import RecordingManager
                scheduler = self.analysis_manager.scheduler if self.analysis_manager else None
                self.recording_manager = RecordingManager(self.storage, scheduler=scheduler)
            
            # 如果已经在录制，则跳过
            if self.recording_manager.is_recording:
                logger.info("录制已在进行中，跳过自动启动")
                return
            
            logger.info("自启动后自动开始录制...")
            self.recording_manager.start_recording()
            
            self._update_record_button(True)
            self.recording_indicator.set_recording(True)
            self.tray_record_action.setText("⏹ 停止追踪")
            self.tray_icon.setToolTip("Dayflow - 录制中...")
            self.pause_btn.setEnabled(True)
            self.tray_pause_action.setEnabled(True)
            self._update_pause_button(False)
            
            # 显示托盘提示
            self.tray_icon.showMessage(
                "Dayflow",
                "已自动开始录制 ✓",
                QSystemTrayIcon.Information,
                2000
            )
            logger.info("自动录制已启动")
        except Exception as e:
            logger.error(f"自动开始录制失败: {e}")
    
    def _toggle_recording(self):
        """切换录制状态"""
        if self.recording_manager is None:
            from core.recorder import RecordingManager
            scheduler = self.analysis_manager.scheduler if self.analysis_manager else None
            self.recording_manager = RecordingManager(self.storage, scheduler=scheduler)
        
        if self.recording_manager.is_recording:
            # 防止重复点击
            if self._stopping:
                logger.debug("已在停止中，忽略重复点击")
                return
            self._stopping = True
            
            # 立即更新 UI，让用户知道正在停止
            self.record_btn.setEnabled(False)
            self.record_btn.setText("停止中，请耐心等候")
            self.pause_btn.setEnabled(False)
            self.tray_record_action.setEnabled(False)
            
            # 显示提示消息
            self.tray_icon.showMessage(
                "Dayflow",
                "正在保存数据并结束录制，请稍候...",
                QSystemTrayIcon.Information,
                3000  # 显示 3 秒
            )
            
            # 在后台线程中执行停止操作
            import threading
            def stop_in_background():
                try:
                    self.recording_manager.stop_recording()
                    self._stop_analysis()
                except Exception as e:
                    logger.error(f"停止录制时出错: {e}")
                finally:
                    # 回到主线程更新 UI
                    from PySide6.QtCore import QMetaObject, Qt
                    QMetaObject.invokeMethod(self, "_on_recording_stopped", Qt.QueuedConnection)
            
            threading.Thread(target=stop_in_background, daemon=True).start()
        else:
            # 检查 API Key
            if not config.API_KEY:
                show_warning(
                    self, 
                    "提示", 
                    "请先在设置中配置 API Key"
                )
                self._switch_page(2)
                return
            
            # 先启动分析调度器
            self._start_analysis()
            
            self.recording_manager.start_recording()
            self._update_record_button(True)
            self.recording_indicator.set_recording(True)
            self.tray_record_action.setText("⏹ 停止追踪")
            self.tray_icon.setToolTip("Dayflow - 录制中...")
            self.pause_btn.setEnabled(True)
            self.tray_pause_action.setEnabled(True)
    
    def _start_analysis(self):
        """启动分析调度器"""
        if self.analysis_manager is None:
            from core.analysis import AnalysisManager
            self.analysis_manager = AnalysisManager(self.storage)
        
        self.analysis_manager.start_scheduler()
        
        logger.info("分析调度器已启动")
    
    def _stop_analysis(self):
        """停止分析调度器"""
        if self.analysis_manager:
            self.analysis_manager.stop_scheduler()
            logger.info("分析调度器已停止")
    
    @Slot()
    def _on_recording_stopped(self):
        """录制停止后的 UI 更新（在主线程中调用）"""
        self._stopping = False  # 重置停止标志
        self.record_btn.setEnabled(True)
        self._update_record_button(False)
        self.recording_indicator.set_recording(False)
        self.tray_record_action.setEnabled(True)
        self.tray_record_action.setText("▶ 开始追踪")
        self.tray_icon.setToolTip("Dayflow - 智能时间追踪")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸ 暂停录屏")
        self.tray_pause_action.setEnabled(False)
        self.tray_pause_action.setText("⏸ 暂停录屏")
        
        # 强制分析剩余切片（录制停止时）
        if self.analysis_manager and self.analysis_manager.scheduler:
            try:
                logger.info("录制已停止，开始分析剩余的视频片段")
                self.analysis_manager.scheduler.analyze_remaining_chunks()
                logger.info("剩余片段分析完成")
            except Exception as e:
                logger.error(f"分析剩余片段失败: {e}")
        
        # 显示完成提示
        self.tray_icon.showMessage(
            "Dayflow",
            "录制已停止，数据已保存 ✓",
            QSystemTrayIcon.Information,
            2000
        )
    
    def _toggle_pause(self):
        """切换暂停状态"""
        if self.recording_manager is None:
            return
        
        if self.recording_manager.is_paused:
            # 继续录制
            self.recording_manager.resume_recording()
            self.pause_btn.setText("⏸ 暂停录屏")
            self.tray_pause_action.setText("⏸ 暂停录屏")
            self.recording_indicator.set_recording(True, paused=False)
            self.tray_icon.setToolTip("Dayflow - 录制中...")
            logger.info("录制已继续")
        else:
            # 暂停录制
            self.recording_manager.pause_recording()
            self.pause_btn.setText("▶ 继续录屏")
            self.tray_pause_action.setText("▶ 继续录屏")
            self.recording_indicator.set_recording(True, paused=True)
            elapsed = self.recording_indicator.get_elapsed_time()
            self.tray_icon.setToolTip(f"Dayflow - 已暂停 {elapsed}")
            logger.info("录制已暂停")
    
    def _update_pause_button(self, paused: bool):
        """更新暂停按钮状态"""
        if paused:
            self.pause_btn.setText("▶ 继续录屏")
            self.tray_pause_action.setText("▶ 继续录屏")
            elapsed = self.recording_indicator.get_elapsed_time()
            self.tray_icon.setToolTip(f"Dayflow - 已暂停 {elapsed}")
        else:
            self.pause_btn.setText("⏸ 暂停录屏")
            self.tray_pause_action.setText("⏸ 暂停录屏")
            self.tray_icon.setToolTip("Dayflow - 录制中...")
    
    def _update_record_button(self, recording: bool):
        """更新录制按钮状态"""
        t = get_theme()
        if recording:
            self.record_btn.setText("⏹ 停止追踪")
            self.record_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.error};
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: #FF6961;
                }}
            """)
        else:
            self.record_btn.setText("● 开始追踪")
            self.record_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.accent};
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {t.accent_hover};
                }}
            """)
    
    def apply_theme(self):
        """应用主题到主窗口组件"""
        t = get_theme()
        
        # 主窗口背景（确保无边框窗口背景色正确）
        self.setStyleSheet(f"background-color: {t.bg_secondary};")
        
        # 侧边栏
        self.sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {t.bg_sidebar};
                border-right: 1px solid {t.border};
            }}
        """)
        
        # Logo
        self.logo.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            color: {t.text_primary};
            padding: 8px 12px;
            margin-bottom: 16px;
        """)
        
        # 主内容区
        self.stack.setStyleSheet(f"background-color: {t.bg_primary};")
        
        # 暂停按钮
        self.pause_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: none;
                border-radius: 10px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {t.bg_hover};
            }}
            QPushButton:disabled {{
                background-color: {t.bg_secondary};
                color: {t.text_muted};
            }}
        """)
        
        # 更新录制按钮（根据当前状态）
        is_recording = self.recording_manager and self.recording_manager.is_recording
        self._update_record_button(is_recording)
    
    def _on_card_selected(self, card: ActivityCard):
        """卡片被点击"""
        logger.info(f"卡片被点击: {card.title}")
        # 现在由 TimelineView 内部处理编辑对话框
    
    def _on_card_updated(self, card: ActivityCard):
        """卡片更新"""
        success = self.storage.update_card(
            card_id=card.id,
            category=card.category,
            title=card.title,
            summary=card.summary,
            productivity_score=card.productivity_score
        )
        if success:
            logger.info(f"卡片已更新: {card.id} - {card.title}")
        else:
            show_warning(self, "更新失败", "无法保存修改，请重试")
    
    def _on_card_deleted(self, card_id: int):
        """卡片删除"""
        success = self.storage.delete_card(card_id)
        if success:
            logger.info(f"卡片已删除: {card_id}")
        else:
            show_warning(self, "删除失败", "无法删除记录，请重试")
    
    def _on_api_key_saved(self, api_key: str):
        """API Key 保存后"""
        logger.info("API Key 已更新")
    
    def _on_date_changed(self, date: datetime):
        """日期切换时加载对应数据"""
        logger.info(f"切换到日期: {date.strftime('%Y-%m-%d')}")
        cards = self.storage.get_cards_for_date(date)
        self.daily_event_view.set_cards(cards)
    
    def _on_export_requested(self, date: datetime, cards: list):
        """导出数据到 CSV"""
        import csv
        from PySide6.QtWidgets import QFileDialog
        
        if not cards:
            show_information(self, "提示", "当前日期没有数据可导出")
            return
        
        # 选择保存路径
        default_name = f"dayflow_{date.strftime('%Y%m%d')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 CSV",
            default_name,
            "CSV 文件 (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow([
                    '开始时间', '结束时间', '时长(分钟)', 
                    '类别', '标题', '摘要', 
                    '应用程序', '生产力评分'
                ])
                
                # 写入数据
                for card in cards:
                    apps = ', '.join([app.name for app in card.app_sites]) if card.app_sites else ''
                    writer.writerow([
                        card.start_time.strftime('%Y-%m-%d %H:%M:%S') if card.start_time else '',
                        card.end_time.strftime('%Y-%m-%d %H:%M:%S') if card.end_time else '',
                        f"{card.duration_minutes:.1f}",
                        card.category or '',
                        card.title or '',
                        card.summary or '',
                        apps,
                        f"{card.productivity_score:.0f}"
                    ])
            
            show_information(self, "成功", f"数据已导出到:\n{file_path}")
            logger.info(f"导出 CSV 成功: {file_path}")
            
        except Exception as e:
            show_critical(self, "错误", f"导出失败: {e}")
            logger.error(f"导出 CSV 失败: {e}")
    
    def _show_window(self):
        """显示主窗口"""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def _minimize_to_tray(self):
        """最小化到系统托盘"""
        self.hide()
        self.tray_icon.showMessage(
            "Dayflow",
            "应用已最小化到系统托盘",
            QSystemTrayIcon.Information,
            2000
        )
    
    def _toggle_maximize(self):
        """切换最大化/还原"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        # 更新标题栏按钮图标
        self.title_bar.update_maximize_button(self.isMaximized())
    
    def _on_tray_activated(self, reason):
        """托盘图标被点击"""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()
        elif reason == QSystemTrayIcon.Trigger:
            # 单击也显示窗口
            self._show_window()
    
    def nativeEvent(self, eventType, message):
        """处理 Windows 原生事件，实现无边框窗口的边缘调整大小"""
        if sys.platform == 'win32' and eventType == b'windows_generic_MSG':
            msg = ctypes.wintypes.MSG.from_address(message.__int__())
            if msg.message == 0x0084:  # WM_NCHITTEST
                # 获取鼠标屏幕坐标（WM_NCHITTEST lParam中的坐标是屏幕坐标）
                x = ctypes.wintypes.LPARAM(msg.lParam).value & 0xFFFF
                y = (ctypes.wintypes.LPARAM(msg.lParam).value >> 16) & 0xFFFF
                
                # 获取窗口在屏幕上的实际位置和大小（使用Windows API获取物理像素）
                hwnd = int(self.winId())
                try:
                    from ctypes import wintypes
                    GetWindowRect = ctypes.windll.user32.GetWindowRect
                    GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
                    GetWindowRect.restype = wintypes.BOOL
                    
                    rect = wintypes.RECT()
                    if GetWindowRect(hwnd, ctypes.byref(rect)):
                        window_width = rect.right - rect.left
                        window_height = rect.bottom - rect.top
                        
                        # 计算鼠标相对于窗口左上角的偏移（屏幕坐标 - 窗口左上角屏幕坐标）
                        rel_x = x - rect.left
                        rel_y = y - rect.top
                        
                        # 边缘检测区域（物理像素）
                        border = 8
                        
                        # 判断鼠标位置
                        result = 0
                        if rel_x <= border:
                            # 左边框区域 - 检查是否在标题栏区域
                            # 标题栏高度约40像素（物理像素）
                            title_bar_height = 40
                            if rel_y < title_bar_height:
                                # 在标题栏区域，让Qt正常处理
                                return False, 0
                            
                            if rel_y <= border:
                                result = 13  # HTTOPLEFT
                            elif rel_y >= window_height - border:
                                result = 16  # HTBOTTOMLEFT
                            else:
                                result = 10  # HTLEFT
                        elif rel_x >= window_width - border:
                            # 右边框区域
                            if rel_y <= border:
                                result = 14  # HTTOPRIGHT
                            elif rel_y >= window_height - border:
                                result = 17  # HTBOTTOMRIGHT
                            else:
                                result = 11  # HTRIGHT
                        elif rel_y <= border:
                            # 上边框区域（左右角已在左右边框检测中处理）
                            result = 12  # HTTOP
                        elif rel_y >= window_height - border:
                            # 下边框区域
                            result = 15  # HTBOTTOM
                        else:
                            # 如果不在边缘区域，返回 False 让 Qt 处理
                            return False, 0
                        
                        return True, result
                except Exception:
                    pass
        return super().nativeEvent(eventType, message)
    
    def _is_ancestor_of_type(self, widget, type_name):
        """检查 widget 或其祖先是否是某种类型"""
        current = widget
        while current:
            if current.metaObject().className() == type_name:
                return True
            current = current.parent()
        return False
    
    def _quit_app(self):
        """退出应用"""
        self._quitting = True  # 标记正在退出
        
        # 停止录制
        if self.recording_manager and self.recording_manager.is_recording:
            self.recording_manager.stop_recording()
        
        # 停止分析
        self._stop_analysis()
        
        # 关闭数据库连接，确保数据写入
        if self.storage:
            self.storage.close()
        
        QApplication.quit()
    
    def closeEvent(self, event):
        """窗口关闭事件 - 询问是否退出"""
        if self._quitting:
            # 真正退出，接受关闭事件
            event.accept()
        else:
            # 询问用户
            msg_box = create_themed_message_box(self)
            msg_box.setWindowTitle("退出确认")
            msg_box.setText("确定要退出 Dayflow 吗？\n\n点击「否」将最小化到系统托盘。")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            msg_box.setDefaultButton(QMessageBox.Yes)
            reply = msg_box.exec()
            
            if reply == QMessageBox.Yes:
                event.ignore()
                self._quit_app()
            elif reply == QMessageBox.No:
                event.ignore()
                self._minimize_to_tray()
            else:
                event.ignore()
    


