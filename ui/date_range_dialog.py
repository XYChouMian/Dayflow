"""
Dayflow - 日期范围选择对话框
用于 Web Dashboard 导出功能
"""
import sys
import ctypes
from datetime import date, timedelta

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QDateEdit, QPushButton, QFrame
)
from PySide6.QtCore import Signal, QDate, Qt
from PySide6.QtGui import QFont, QPalette, QColor

from .themes import get_theme, get_theme_manager, ThemeManager


class DateRangeDialog(QDialog):
    """日期范围选择对话框"""
    
    # 信号：选择完成后发出 (start_date, end_date)
    range_selected = Signal(date, date)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择日期范围")
        self.setFixedSize(400, 280)
        self.setModal(True)
        
        self._setup_ui()
        self._connect_signals()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
        
        # 默认选择今日
        self._on_preset_changed(0)
    
    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 标题
        self.title = QLabel("📊 导出生产力报告")
        self.title.setFont(QFont("", 14, QFont.Bold))
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)
        
        # 说明
        self.desc = QLabel("选择要导出的日期范围，将生成 HTML 格式的报告")
        self.desc.setStyleSheet("color: #888;")
        self.desc.setAlignment(Qt.AlignCenter)
        self.desc.setWordWrap(True)
        layout.addWidget(self.desc)
        
        # 分隔线
        self.line = QFrame()
        self.line.setFrameShape(QFrame.HLine)
        self.line.setStyleSheet("background: #3a3a50;")
        layout.addWidget(self.line)
        
        # 预设选项
        self.preset_layout = QHBoxLayout()
        self.preset_label = QLabel("快速选择:")
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["今日", "昨日", "本周", "上周", "本月", "自定义"])
        self.preset_combo.setMinimumWidth(150)
        self.preset_layout.addWidget(self.preset_label)
        self.preset_layout.addWidget(self.preset_combo)
        self.preset_layout.addStretch()
        layout.addLayout(self.preset_layout)
        
        # 日期选择器
        date_layout = QHBoxLayout()
        
        start_layout = QVBoxLayout()
        self.start_label = QLabel("开始日期")
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        start_layout.addWidget(self.start_label)
        start_layout.addWidget(self.start_date)
        
        end_layout = QVBoxLayout()
        self.end_label = QLabel("结束日期")
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        end_layout.addWidget(self.end_label)
        end_layout.addWidget(self.end_date)
        
        date_layout.addLayout(start_layout)
        date_layout.addSpacing(20)
        date_layout.addLayout(end_layout)
        layout.addLayout(date_layout)
        
        layout.addStretch()
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumWidth(80)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.export_btn = QPushButton("导出报告")
        self.export_btn.setMinimumWidth(100)
        self.export_btn.clicked.connect(self._on_export)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)
    
    def _connect_signals(self):
        """连接信号"""
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
    
    def _on_preset_changed(self, index: int):
        """预设选项变化"""
        today = date.today()
        
        if index == 0:  # 今日
            start = end = today
        elif index == 1:  # 昨日
            start = end = today - timedelta(days=1)
        elif index == 2:  # 本周
            start = today - timedelta(days=today.weekday())
            end = today
        elif index == 3:  # 上周
            start = today - timedelta(days=today.weekday() + 7)
            end = start + timedelta(days=6)
        elif index == 4:  # 本月
            start = today.replace(day=1)
            end = today
        else:  # 自定义
            # 不修改日期，让用户自己选择
            self.start_date.setEnabled(True)
            self.end_date.setEnabled(True)
            return
        
        # 更新日期选择器
        self.start_date.setDate(QDate(start.year, start.month, start.day))
        self.end_date.setDate(QDate(end.year, end.month, end.day))
        
        # 非自定义模式下禁用日期选择器
        is_custom = (index == 5)
        self.start_date.setEnabled(is_custom)
        self.end_date.setEnabled(is_custom)
    
    def _on_export(self):
        """导出按钮点击"""
        start = self.start_date.date().toPython()
        end = self.end_date.date().toPython()
        
        # 确保开始日期不晚于结束日期
        if start > end:
            start, end = end, start
        
        self.range_selected.emit(start, end)
        self.accept()
    
    def get_date_range(self) -> tuple[date, date]:
        """获取选择的日期范围"""
        start = self.start_date.date().toPython()
        end = self.end_date.date().toPython()
        
        if start > end:
            start, end = end, start
        
        return start, end
    
    def apply_theme(self):
        """应用主题"""
        t = get_theme()
        
        # 对话框完整样式
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg_primary};
                color: {t.text_primary};
            }}
            QDateEdit {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 4px 8px;
                selection-background-color: {t.accent};
            }}
            QDateEdit::drop-down {{
                border: none;
                width: 20px;
            }}
            QDateEdit QAbstractItemView {{
                background-color: {t.bg_secondary};
                color: {t.text_primary};
                selection-background-color: {t.accent};
                border: 1px solid {t.border};
            }}
            QDateEdit QCalendarWidget QTableView {{
                background-color: {t.bg_secondary};
                color: {t.text_primary};
                selection-background-color: {t.accent};
            }}
            QCalendarWidget {{
                background-color: {t.bg_secondary};
                color: {t.text_primary};
            }}
            QCalendarWidget QToolButton {{
                background-color: {t.bg_secondary};
                color: {t.text_primary};
                border: none;
                padding: 4px;
            }}
            QCalendarWidget QMenu {{
                background-color: {t.bg_secondary};
                color: {t.text_primary};
            }}
            QCalendarWidget QSpinBox {{
                background-color: {t.bg_secondary};
                color: {t.text_primary};
                border: 1px solid {t.border};
            }}
            QComboBox {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QComboBox:hover {{
                border-color: {t.accent};
            }}
            QComboBox QAbstractItemView {{
                background-color: {t.bg_secondary};
                color: {t.text_primary};
                selection-background-color: {t.accent};
                border: 1px solid {t.border};
            }}
        """)
        
        # 设置 QPalette 以修复暗色主题下的标题栏颜色
        palette = self.palette()
        
        if t.name == "dark":
            # 暗色主题 - 设置窗口颜色
            palette.setColor(QPalette.Window, QColor(t.bg_primary))
            palette.setColor(QPalette.WindowText, QColor(t.text_primary))
            palette.setColor(QPalette.Base, QColor(t.bg_secondary))
            palette.setColor(QPalette.Text, QColor(t.text_primary))
            palette.setColor(QPalette.Button, QColor(t.bg_tertiary))
            palette.setColor(QPalette.ButtonText, QColor(t.text_primary))
            
            # 设置 Windows 原生标题栏为暗色
            if sys.platform == 'win32':
                try:
                    hwnd = self.winId()
                    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                    use_immersive_dark_mode = 1
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        ctypes.c_void_p(int(hwnd)),
                        ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE),
                        ctypes.byref(ctypes.c_int(use_immersive_dark_mode)),
                        ctypes.sizeof(ctypes.c_int)
                    )
                except Exception as e:
                    pass
        else:
            # 亮色主题
            palette.setColor(QPalette.Window, QColor(t.bg_primary))
            palette.setColor(QPalette.WindowText, QColor(t.text_primary))
            palette.setColor(QPalette.Base, QColor("#FFFFFF"))
            palette.setColor(QPalette.Text, QColor(t.text_primary))
        
        self.setPalette(palette)
        
        # 标题样式
        self.title.setStyleSheet(f"color: {t.text_primary};")
        
        # 说明文字样式
        self.desc.setStyleSheet(f"color: {t.text_muted};")
        
        # 标签样式
        for label in self.findChildren(QLabel):
            if label not in [self.title, self.desc]:
                label.setStyleSheet(f"color: {t.text_primary};")
        
        # 日期标签样式
        if hasattr(self, 'start_label'):
            self.start_label.setStyleSheet(f"color: {t.text_muted}; font-size: 12px;")
        if hasattr(self, 'end_label'):
            self.end_label.setStyleSheet(f"color: {t.text_muted}; font-size: 12px;")
        if hasattr(self, 'preset_label'):
            self.preset_label.setStyleSheet(f"color: {t.text_muted}; font-size: 12px;")
        
        # 分隔线样式
        self.line.setStyleSheet(f"background: {t.border};")
        
        # 取消按钮样式
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.bg_tertiary};
                    color: {t.text_primary};
                    border: 1px solid {t.border};
                    border-radius: 6px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background-color: {t.bg_hover};
                    border-color: {t.accent};
                }}
            """)
        
        # 导出按钮样式
        if hasattr(self, 'export_btn'):
            self.export_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.accent};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {t.accent_hover};
                }}
            """)
