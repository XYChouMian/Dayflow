"""
Dayflow Windows - 时间轴视图组件
"""
from datetime import datetime, timedelta
from typing import List, Optional
import time
import sys
import ctypes

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QSizePolicy, QProgressBar, QGraphicsDropShadowEffect,
    QPushButton, QFileDialog, QLineEdit, QDialog, QComboBox,
    QSpinBox, QMenu, QMessageBox, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QColor, QFont, QPalette, QLinearGradient, QPainter, QBrush, QAction
from ui.themes import show_question

from core.types import ActivityCard
from ui.themes import get_theme_manager, get_theme, get_efficiency_color, get_category_color


class CardEditDialog(QDialog):
    """卡片编辑对话框"""
    
    card_updated = Signal(object)  # 发送更新后的卡片
    card_deleted = Signal(int)     # 发送删除的卡片 ID
    
    # 可选类别列表
    CATEGORIES = ["工作", "学习", "编程", "会议", "娱乐", "社交", "休息", "其他"]
    
    def __init__(self, card: 'ActivityCard', parent=None):
        super().__init__(parent)
        self.card = card
        self.setWindowTitle("编辑活动")
        self.setMinimumWidth(450)
        self.setModal(True)
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 时间信息（只读）
        time_label = QLabel(self._format_time())
        time_label.setObjectName("timeInfo")
        layout.addWidget(time_label)
        
        # 类别选择
        cat_layout = QHBoxLayout()
        cat_label = QLabel("类别")
        cat_label.setFixedWidth(80)
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.CATEGORIES)
        # 设置当前类别
        if self.card.category in self.CATEGORIES:
            self.category_combo.setCurrentText(self.card.category)
        else:
            self.category_combo.setCurrentText("其他")
        cat_layout.addWidget(cat_label)
        cat_layout.addWidget(self.category_combo)
        layout.addLayout(cat_layout)
        
        # 标题输入
        title_layout = QHBoxLayout()
        title_label = QLabel("标题")
        title_label.setFixedWidth(80)
        self.title_input = QLineEdit(self.card.title or "")
        self.title_input.setPlaceholderText("活动标题")
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_input)
        layout.addLayout(title_layout)
        
        # 摘要输入
        summary_layout = QVBoxLayout()
        summary_label = QLabel("摘要")
        self.summary_input = QTextEdit()
        self.summary_input.setPlainText(self.card.summary or "")
        self.summary_input.setPlaceholderText("活动摘要描述")
        self.summary_input.setMaximumHeight(100)
        summary_layout.addWidget(summary_label)
        summary_layout.addWidget(self.summary_input)
        layout.addLayout(summary_layout)
        
        # 生产力评分
        score_layout = QHBoxLayout()
        score_label = QLabel("效率评分")
        score_label.setFixedWidth(80)
        self.score_spin = QSpinBox()
        self.score_spin.setRange(0, 100)
        self.score_spin.setValue(int(self.card.productivity_score))
        self.score_spin.setSuffix(" %")
        self.score_spin.setMinimumWidth(120)
        self.score_spin.setFixedHeight(40)  # 固定高度
        score_layout.addWidget(score_label)
        score_layout.addWidget(self.score_spin)
        score_layout.addStretch()
        layout.addLayout(score_layout)
        
        # 应用列表（只读）
        if self.card.app_sites:
            apps_label = QLabel("应用程序")
            apps_text = ", ".join([app.name for app in self.card.app_sites[:5]])
            if len(self.card.app_sites) > 5:
                apps_text += f" (+{len(self.card.app_sites) - 5})"
            apps_value = QLabel(apps_text)
            apps_value.setObjectName("appsInfo")
            apps_value.setWordWrap(True)
            layout.addWidget(apps_label)
            layout.addWidget(apps_value)
        
        layout.addStretch()
        
        # 按钮行
        btn_layout = QHBoxLayout()
        
        # 删除按钮
        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
    
    def _format_time(self) -> str:
        """格式化时间范围"""
        if self.card.start_time and self.card.end_time:
            start = self.card.start_time.strftime("%Y-%m-%d %H:%M")
            end = self.card.end_time.strftime("%H:%M")
            duration = self.card.duration_minutes
            if duration >= 60:
                hours = int(duration // 60)
                mins = int(duration % 60)
                dur_str = f"{hours}h {mins}m" if mins else f"{hours}h"
            else:
                dur_str = f"{int(duration)}m"
            return f"🕐 {start} - {end} ({dur_str})"
        return ""
    
    def _on_save(self):
        """保存修改"""
        # 更新卡片对象
        self.card.category = self.category_combo.currentText()
        self.card.title = self.title_input.text().strip()
        self.card.summary = self.summary_input.toPlainText().strip()
        self.card.productivity_score = self.score_spin.value()
        
        self.card_updated.emit(self.card)
        self.accept()
    
    def _on_delete(self):
        """删除卡片"""
        reply = show_question(
            self,
            "确认删除",
            f"确定要删除这条活动记录吗？\n\n「{self.card.title or '未命名活动'}」\n\n此操作不可撤销。"
        )
        
        if reply == QMessageBox.Yes:
            self.card_deleted.emit(self.card.id)
            self.accept()
    
    def _set_dark_title_bar(self, is_dark: bool = True):
        """设置 Windows 原生标题栏颜色"""
        if sys.platform == 'win32':
            try:
                hwnd = self.winId()
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                
                use_immersive_dark_mode = 1 if is_dark else 0
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_void_p(int(hwnd)),
                    ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE),
                    ctypes.byref(ctypes.c_int(use_immersive_dark_mode)),
                    ctypes.sizeof(ctypes.c_int)
                )
            except Exception as e:
                pass
    
    def apply_theme(self):
        t = get_theme()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg_primary};
            }}
            QLabel {{
                color: {t.text_primary};
                font-size: 14px;
            }}
            QLabel#timeInfo {{
                color: {t.text_muted};
                font-size: 13px;
                padding: 8px 0;
            }}
            QLabel#appsInfo {{
                color: {t.text_secondary};
                font-size: 12px;
                padding: 4px 0;
            }}
            QLineEdit, QTextEdit {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 10px;
                color: {t.text_primary};
                font-size: 14px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {t.accent};
            }}
            QComboBox {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 8px 12px;
                color: {t.text_primary};
                font-size: 14px;
            }}
            QComboBox:hover {{
                border-color: {t.accent};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                selection-background-color: {t.accent_light};
            }}
            QSpinBox {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 8px 16px;
                color: {"#000000" if t.name == "light" else "#FFFFFF"};
                font-size: 14px;
                font-weight: 500;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                min-width: 80px;
            }}
            QSpinBox:focus {{
                border-color: {t.accent};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 20px;
            }}
        """)
        
        # 删除按钮 - 红色
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.error};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #FF6961;
            }}
        """)
        
        # 取消按钮
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {t.bg_hover};
            }}
        """)
        
        # 保存按钮 - 强调色
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.accent};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {t.accent_hover};
            }}
        """)
        
        # 设置 Windows 原生标题栏颜色
        if sys.platform == 'win32':
            self._set_dark_title_bar(is_dark=(t.name == "dark"))


class StatsSummaryWidget(QFrame):
    """统计汇总组件 - 显示时间分布（可折叠）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {}  # category -> minutes
        self._total_minutes = 0
        self._collapsed = False
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
    
    def _setup_ui(self):
        self.setObjectName("statsSummary")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        
        # 标题栏（可点击折叠）
        title_layout = QHBoxLayout()
        self.title_label = QLabel("📊 时间分布")
        title_layout.addWidget(self.title_label)
        
        self.total_label = QLabel("0h 0m")
        title_layout.addWidget(self.total_label)
        title_layout.addStretch()
        
        # 折叠按钮
        self.collapse_btn = QPushButton("▼")
        self.collapse_btn.setObjectName("collapseArrowButton")
        self.collapse_btn.setFixedSize(28, 28)
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        title_layout.addWidget(self.collapse_btn)
        
        layout.addLayout(title_layout)
        
        # 图表容器（用于折叠）- 详细列表
        self.chart_widget = QWidget()
        self.chart_container = QVBoxLayout(self.chart_widget)
        self.chart_container.setContentsMargins(0, 0, 0, 0)
        self.chart_container.setSpacing(8)
        layout.addWidget(self.chart_widget)
    
    def _toggle_collapse(self):
        """切换折叠状态"""
        self._collapsed = not self._collapsed
        self.chart_widget.setVisible(not self._collapsed)
        self.collapse_btn.setText("▶" if self._collapsed else "▼")
        
        # 更新按钮提示
        self.collapse_btn.setToolTip("展开" if self._collapsed else "折叠")
    
    def apply_theme(self):
        """应用主题"""
        t = get_theme()
        self.setStyleSheet(f"""
            QFrame#statsSummary {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 12px;
            }}
        """)
        self.title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {t.text_primary};
        """)
        self.total_label.setStyleSheet(f"""
            font-size: 13px;
            color: {t.text_muted};
        """)
        # 折叠按钮样式 - 更明显
        # 亮色模式使用更深的颜色以提高对比度
        collapse_color = "#1a1a1a" if t.name == "light" else t.text_primary
        self.collapse_btn.setStyleSheet(f"""
            QPushButton#collapseArrowButton {{
                background-color: {t.bg_tertiary} !important;
                color: {collapse_color} !important;
                border: 1px solid {t.border} !important;
                border-radius: 6px !important;
                font-size: 16px !important;
                font-weight: bold !important;
                padding: 0 !important;
            }}
            QPushButton#collapseArrowButton:hover {{
                background-color: {t.bg_hover} !important;
                border-color: {t.accent} !important;
                color: {collapse_color} !important;
            }}
        """)
        
        # 重新生成图表以应用新主题
        if self._data:
            self._regenerate_bars()
    
    def _regenerate_bars(self):
        """重新生成所有柱状图"""
        # 清除现有柱状图
        while self.chart_container.count():
            item = self.chart_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self._data:
            return
        
        # 按时间排序并重新创建
        sorted_data = sorted(self._data.items(), key=lambda x: x[1], reverse=True)
        for category, minutes in sorted_data:
            self._add_bar(category, minutes)
    
    def set_data(self, cards: list):
        """根据卡片数据设置统计 - 优化版本"""
        # 统计各类别时间
        new_data = {}
        for card in cards:
            category = card.category or "其他"
            minutes = card.duration_minutes
            new_data[category] = new_data.get(category, 0) + minutes
        
        # 如果数据没变化，跳过更新
        if new_data == self._data:
            return
        
        self._data = new_data
        self._total_minutes = sum(self._data.values())
        
        # 更新总时间
        hours = int(self._total_minutes // 60)
        mins = int(self._total_minutes % 60)
        self.total_label.setText(f"共 {hours}h {mins}m")
        
        # 暂停更新以减少重绘
        self.chart_widget.setUpdatesEnabled(False)
        
        try:
            # 清除旧数据
            while self.chart_container.count():
                item = self.chart_container.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            if not self._data:
                t = get_theme()
                empty = QLabel("暂无数据")
                empty.setStyleSheet(f"color: {t.text_muted}; font-size: 13px;")
                self.chart_container.addWidget(empty)
                return
            
            # 按时间排序
            sorted_data = sorted(self._data.items(), key=lambda x: x[1], reverse=True)
            
            # 创建柱状图
            for category, minutes in sorted_data:
                self._add_bar(category, minutes)
        finally:
            self.chart_widget.setUpdatesEnabled(True)
    
    def _add_bar(self, category: str, minutes: float):
        """添加一个统计条"""
        t = get_theme()
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        
        # 类别名 - 使用主题文字颜色
        cat_label = QLabel(category)
        cat_label.setFixedWidth(60)
        cat_label.setStyleSheet(f"""
            font-size: 12px;
            color: {t.text_primary};
        """)
        row_layout.addWidget(cat_label)
        
        # 进度条
        percentage = (minutes / self._total_minutes * 100) if self._total_minutes > 0 else 0
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(percentage))
        bar.setTextVisible(False)
        bar.setFixedHeight(12)
        
        color = get_category_color(category)
        bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {t.bg_tertiary};
                border: none;
                border-radius: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)
        row_layout.addWidget(bar, 1)
        
        # 时间
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        time_str = f"{hours}h {mins}m" if hours else f"{mins}m"
        time_label = QLabel(time_str)
        time_label.setFixedWidth(50)
        time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        time_label.setStyleSheet(f"""
            font-size: 12px;
            color: {t.text_muted};
        """)
        row_layout.addWidget(time_label)
        
        self.chart_container.addWidget(row)


class ActivityCardWidget(QFrame):
    """单个活动卡片组件"""
    
    clicked = Signal(ActivityCard)
    edit_requested = Signal(ActivityCard)
    delete_requested = Signal(int)  # card_id
    
    def __init__(self, card: ActivityCard, parent=None):
        super().__init__(parent)
        self.card = card
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _setup_ui(self):
        t = get_theme()
        self.setObjectName("activityCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFrameShape(QFrame.StyledPanel)
        
        # 获取效率颜色
        efficiency_color = get_efficiency_color(self.card.productivity_score)
        
        # 获取类别颜色
        category_color = get_category_color(self.card.category)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        
        # 顶部：类别标签 + 时间 + 深度工作徽章
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)
        
        # 类别标签
        category_label = QLabel(self.card.category or "活动")
        
        # 解析颜色并转换为 rgba 格式
        color = QColor(category_color)
        r, g, b = color.red(), color.green(), color.blue()
        
        # 使用 rgba() 格式设置带透明度的背景颜色
        category_label.setStyleSheet(f"""
            background-color: rgba({r}, {g}, {b}, 0.4);
            color: {t.text_primary};
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        """)
        top_layout.addWidget(category_label)
        
        # 深度工作徽章 (duration >= 60 分钟，且类别为工作相关)
        work_categories = ["工作", "学习", "编程", "会议"]
        if self.card.duration_minutes >= 60 and self.card.category in work_categories:
            deep_work_badge = QLabel("🔥 深度工作")
            deep_work_badge._is_deep_work_badge = True
            deep_work_badge.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF6B6B, stop:1 #FF8E53);
                color: white;
                padding: 4px 10px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
            """)
            top_layout.addWidget(deep_work_badge)
        
        # 时间范围
        time_str = self._format_time_range()
        time_label = QLabel(time_str)
        time_label.setObjectName("timeLabel")
        time_label.setStyleSheet(f"""
            QLabel#timeLabel {{
                color: {t.text_muted};
                font-size: 12px;
            }}
        """)
        top_layout.addWidget(time_label)
        top_layout.addStretch()
        
        # 生产力评分
        if self.card.productivity_score > 0:
            score_label = QLabel(f"⚡ {int(self.card.productivity_score)}%")
            score_label._is_score_label = True
            score_label.setStyleSheet(f"""
                color: {efficiency_color};
                font-size: 12px;
                font-weight: 600;
            """)
            top_layout.addWidget(score_label)
        
        layout.addLayout(top_layout)
        
        # 标题
        title_label = QLabel(self.card.title or "未命名活动")
        title_label.setObjectName("titleLabel")
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"""
            QLabel#titleLabel {{
                color: {t.text_primary};
                font-size: 16px;
                font-weight: 600;
            }}
        """)
        layout.addWidget(title_label)
        
        # 摘要
        if self.card.summary:
            summary_label = QLabel(self.card.summary)
            summary_label.setObjectName("summaryLabel")
            summary_label.setWordWrap(True)
            summary_label.setStyleSheet(f"""
                QLabel#summaryLabel {{
                    color: {t.text_secondary};
                    font-size: 13px;
                    line-height: 1.5;
                }}
            """)
            layout.addWidget(summary_label)
        
        # 应用/网站标签
        if self.card.app_sites:
            apps_layout = QHBoxLayout()
            apps_layout.setSpacing(6)
            
            for i, app in enumerate(self.card.app_sites[:4]):  # 最多显示4个
                app_label = QLabel(app.name)
                app_label._is_app_label = True
                app_label.setStyleSheet(f"""
                    background-color: {t.bg_tertiary};
                    color: {t.text_secondary};
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                """)
                apps_layout.addWidget(app_label)
            
            if len(self.card.app_sites) > 4:
                more_label = QLabel(f"+{len(self.card.app_sites) - 4}")
                more_label.setStyleSheet(f"""
                    color: {t.text_muted};
                    font-size: 11px;
                """)
                apps_layout.addWidget(more_label)
            
            apps_layout.addStretch()
            layout.addLayout(apps_layout)
        
        # 卡片样式 - 左侧效率指示条 + 右侧圆角
        self.setStyleSheet(f"""
            QFrame#activityCard {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-left: 4px solid {efficiency_color};
                border-radius: 0px 16px 16px 0px;
            }}
            QFrame#activityCard:hover {{
                background-color: {t.bg_hover};
                border-color: {t.accent};
                border-left: 4px solid {efficiency_color};
            }}
        """)
        
        # 添加柔和阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 30 if t.name == "dark" else 15))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)
    
    def apply_theme(self):
        """应用主题"""
        t = get_theme()
        efficiency_color = get_efficiency_color(self.card.productivity_score)
        category_color = get_category_color(self.card.category)
        
        # 解析颜色并转换为 rgba 格式
        color = QColor(category_color)
        r, g, b = color.red(), color.green(), color.blue()
        
        # 更新所有标签的样式
        for child in self.findChildren(QLabel):
            object_name = child.objectName()
            
            if object_name == "titleLabel":
                child.setStyleSheet(f"""
                    QLabel#titleLabel {{
                        color: {t.text_primary};
                        font-size: 16px;
                        font-weight: 600;
                    }}
                """)
            elif object_name == "summaryLabel":
                child.setStyleSheet(f"""
                    QLabel#summaryLabel {{
                        color: {t.text_secondary};
                        font-size: 13px;
                        line-height: 1.5;
                    }}
                """)
            elif object_name == "timeLabel":
                child.setStyleSheet(f"""
                    QLabel#timeLabel {{
                        color: {t.text_muted};
                        font-size: 12px;
                    }}
                """)
            else:
                # 类别标签或其他标签
                child.setStyleSheet(f"""
                    background-color: rgba({r}, {g}, {b}, 0.4);
                    color: {t.text_primary};
                    padding: 5px 12px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 600;
                """)
        
        # 更新应用/网站标签样式
        for child in self.findChildren(QLabel):
            if hasattr(child, '_is_app_label'):
                child.setStyleSheet(f"""
                    background-color: {t.bg_tertiary};
                    color: {t.text_secondary};
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                """)
        
        # 更新深度工作徽章
        if self.card.duration_minutes >= 60:
            for child in self.findChildren(QLabel):
                if hasattr(child, '_is_deep_work_badge'):
                    child.setStyleSheet(f"""
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF6B6B, stop:1 #FF8E53);
                        color: white;
                        padding: 4px 10px;
                        border-radius: 10px;
                        font-size: 11px;
                        font-weight: 600;
                    """)
        
        # 更新生产力评分标签
        if self.card.productivity_score > 0:
            for child in self.findChildren(QLabel):
                if hasattr(child, '_is_score_label'):
                    child.setStyleSheet(f"""
                        color: {efficiency_color};
                        font-size: 12px;
                        font-weight: 600;
                    """)
        
        # 更新卡片样式
        self.setStyleSheet(f"""
            QFrame#activityCard {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-left: 4px solid {efficiency_color};
                border-radius: 0px 16px 16px 0px;
            }}
            QFrame#activityCard:hover {{
                background-color: {t.bg_hover};
                border-color: {t.accent};
                border-left: 4px solid {efficiency_color};
            }}
        """)
    
    def _format_time_range(self) -> str:
        """格式化时间范围"""
        if self.card.start_time and self.card.end_time:
            start = self.card.start_time.strftime("%H:%M")
            end = self.card.end_time.strftime("%H:%M")
            duration = self.card.duration_minutes
            
            if duration >= 60:
                hours = int(duration // 60)
                mins = int(duration % 60)
                duration_str = f"{hours}h {mins}m" if mins else f"{hours}h"
            else:
                duration_str = f"{int(duration)}m"
            
            return f"{start} - {end} ({duration_str})"
        return ""
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            t = get_theme()
            efficiency_color = get_efficiency_color(self.card.productivity_score)
            self.setStyleSheet(f"""
                QFrame#activityCard {{
                    background-color: {t.bg_hover};
                    border: 2px solid {t.accent};
                    border-left: 4px solid {efficiency_color};
                    border-radius: 0px 16px 16px 0px;
                }}
            """)
            self.clicked.emit(self.card)
            try:
                super().mousePressEvent(event)
            except RuntimeError:
                pass
        else:
            super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        # 恢复原始样式
        t = get_theme()
        efficiency_color = get_efficiency_color(self.card.productivity_score)
        self.setStyleSheet(f"""
            QFrame#activityCard {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-left: 4px solid {efficiency_color};
                border-radius: 0px 16px 16px 0px;
            }}
            QFrame#activityCard:hover {{
                background-color: {t.bg_hover};
                border-color: {t.accent};
                border-left: 4px solid {efficiency_color};
            }}
        """)
        super().mouseReleaseEvent(event)
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        t = get_theme()
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
        """)
        
        # 编辑
        edit_action = QAction("✏️ 编辑", self)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.card))
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        # 删除
        delete_action = QAction("🗑️ 删除", self)
        delete_action.triggered.connect(lambda: self._confirm_delete())
        menu.addAction(delete_action)
        
        menu.exec(self.mapToGlobal(pos))
    
    def _confirm_delete(self):
        """确认删除"""
        reply = show_question(
            self,
            "确认删除",
            f"确定要删除这条活动记录吗？\n\n「{self.card.title or '未命名活动'}」"
        )
        if reply == QMessageBox.Yes:
            self.delete_requested.emit(self.card.id)


class EmptyStateWidget(QWidget):
    """空状态组件 - 显示引导信息"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 60, 40, 60)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignCenter)
        
        # 大图标
        self.icon_label = QLabel("⏱️")
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)
        
        # 标题
        self.title_label = QLabel("开始记录你的一天")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
        # 描述
        self.desc_label = QLabel("点击左侧「开始录制」按钮，Dayflow 将\n自动追踪你的屏幕活动并生成时间轴")
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)
    
    def apply_theme(self):
        t = get_theme()
        self.icon_label.setStyleSheet(f"""
            font-size: 64px;
            padding: 20px;
        """)
        self.title_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 600;
            color: {t.text_primary};
        """)
        self.desc_label.setStyleSheet(f"""
            font-size: 14px;
            color: {t.text_muted};
            line-height: 1.6;
        """)
    
    def set_search_mode(self, is_search: bool):
        """切换搜索模式显示"""
        if is_search:
            self.icon_label.setText("🔍")
            self.title_label.setText("未找到匹配的活动")
            self.desc_label.setText("尝试使用其他关键词搜索")
        else:
            self.icon_label.setText("⏱️")
            self.title_label.setText("开始记录你的一天")
            self.desc_label.setText("点击左侧「开始录制」按钮，Dayflow 将\n自动追踪你的屏幕活动并生成时间轴")


class TimelineView(QWidget):
    """时间轴主视图"""
    
    card_selected = Signal(ActivityCard)
    export_requested = Signal(datetime, list)  # 日期, 卡片列表
    card_updated = Signal(ActivityCard)  # 卡片更新信号
    card_deleted = Signal(int)  # 卡片删除信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: List[ActivityCard] = []
        self._filtered_cards: List[ActivityCard] = []
        self._current_date = datetime.now()
        self._search_text = ""
        
        # 搜索防抖定时器
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
        self._pending_search = ""
        
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 搜索栏
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(24, 12, 24, 12)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索活动标题或摘要...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input)
        
        main_layout.addWidget(search_container)
        
        # 统计汇总（带边距）
        stats_container = QWidget()
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(24, 0, 24, 12)
        self.stats_widget = StatsSummaryWidget()
        stats_layout.addWidget(self.stats_widget)
        main_layout.addWidget(stats_container)
        
        # 滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 卡片容器
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(24, 8, 24, 24)
        self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch()
        
        self.scroll.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll)
        
        # 空状态组件
        self.empty_widget = EmptyStateWidget()
        self.cards_layout.insertWidget(0, self.empty_widget)
    
    def apply_theme(self):
        """应用主题"""
        print(f"[TimelineView] apply_theme 开始")
        start_time = time.time()
        
        t = get_theme()
        
        # 搜索框样式
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 10px;
                padding: 10px 16px;
                font-size: 14px;
                color: {t.text_primary};
            }}
            QLineEdit:focus {{
                border-color: {t.accent};
                background-color: {t.bg_primary};
            }}
            QLineEdit::placeholder {{
                color: {t.text_muted};
            }}
        """)
        
        search_time = time.time() - start_time
        print(f"[TimelineView] 搜索框样式设置耗时: {search_time*1000:.2f}ms")
        
        # 只更新现有卡片的样式，不重新创建卡片
        if self._cards:
            cards_start = time.time()
            card_count = 0
            for i in range(self.cards_layout.count()):
                item = self.cards_layout.itemAt(i)
                widget = item.widget()
                if widget and hasattr(widget, 'apply_theme'):
                    card_start = time.time()
                    widget.apply_theme()
                    card_time = time.time() - card_start
                    card_count += 1
                    if card_count <= 3:  # 只打印前3个卡片的耗时
                        print(f"[TimelineView] 卡片 {card_count} apply_theme 耗时: {card_time*1000:.2f}ms")
            cards_time = time.time() - cards_start
            print(f"[TimelineView] 更新 {card_count} 个卡片样式总耗时: {cards_time*1000:.2f}ms, 平均: {(cards_time*1000/card_count if card_count > 0 else 0):.2f}ms/卡片")
        
        total_time = time.time() - start_time
        print(f"[TimelineView] apply_theme 总耗时: {total_time*1000:.2f}ms")
    
    def _on_search_changed(self, text: str):
        """搜索文本变化 - 使用防抖"""
        self._pending_search = text.strip().lower()
        # 300ms 防抖，避免频繁刷新
        self._search_timer.start(300)
    
    def _do_search(self):
        """执行搜索"""
        self._search_text = self._pending_search
        self._refresh_cards()
    
    def _get_filtered_cards(self) -> List[ActivityCard]:
        """获取过滤后的卡片"""
        if not self._search_text:
            return self._cards
        
        filtered = []
        for card in self._cards:
            # 搜索标题和摘要
            title = (card.title or "").lower()
            summary = (card.summary or "").lower()
            category = (card.category or "").lower()
            
            if (self._search_text in title or 
                self._search_text in summary or 
                self._search_text in category):
                filtered.append(card)
        
        return filtered
    
    def set_cards(self, cards: List[ActivityCard]):
        """设置卡片列表"""
        import logging
        self._cards = cards
        self._refresh_cards()
    
    def add_card(self, card: ActivityCard):
        """添加单个卡片"""
        self._cards.append(card)
        self._add_card_widget(card)
        self._update_empty_state()
    
    def _refresh_cards(self, scroll_to_bottom: bool = False):
        """刷新所有卡片 - 优化版本"""
        # 保存当前滚动位置
        scrollbar = self.scroll.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 50
        old_scroll_value = scrollbar.value()
        
        # 暂停界面更新，减少重绘
        self.cards_container.setUpdatesEnabled(False)
        
        try:
            # 清除现有卡片
            widgets_to_delete = []
            while self.cards_layout.count() > 1:  # 保留 stretch
                item = self.cards_layout.takeAt(0)
                if item.widget() and item.widget() != self.empty_widget:
                    widget = item.widget()
                    # 先断开所有信号连接，防止在删除后仍有信号访问
                    try:
                        widget.blockSignals(True)
                    except:
                        pass
                    widgets_to_delete.append(widget)
            
            # 删除所有旧的 widget
            for widget in widgets_to_delete:
                try:
                    widget.setParent(None)
                    widget.deleteLater()
                except:
                    pass
            
            # 获取过滤后的卡片
            filtered_cards = self._get_filtered_cards()
            
            # 批量添加新卡片
            for card in filtered_cards:
                self._add_card_widget(card, animate=False)
            
            self._update_empty_state(filtered_cards)
            
            # 更新统计图表
            self.stats_widget.set_data(self._cards)
        finally:
            # 恢复界面更新
            self.cards_container.setUpdatesEnabled(True)
        
        # 使用单次定时器恢复滚动位置
        def restore_scroll():
            if scroll_to_bottom or was_at_bottom:
                scrollbar.setValue(scrollbar.maximum())
            else:
                scrollbar.setValue(min(old_scroll_value, scrollbar.maximum()))
        
        QTimer.singleShot(10, restore_scroll)
    
    def _add_card_widget(self, card: ActivityCard, animate: bool = True):
        """添加卡片组件"""
        widget = ActivityCardWidget(card)
        widget.clicked.connect(self._on_card_clicked)
        widget.edit_requested.connect(self._on_edit_card)
        widget.delete_requested.connect(self._on_delete_card)
        
        # 插入到 stretch 之前
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, widget)
    
    def _on_card_clicked(self, card: ActivityCard):
        """卡片点击 - 打开编辑对话框"""
        self._on_edit_card(card)
    
    def _on_edit_card(self, card: ActivityCard):
        """打开编辑对话框"""
        dialog = CardEditDialog(card, self)
        dialog.card_updated.connect(self._handle_card_updated)
        dialog.card_deleted.connect(self._handle_card_deleted)
        dialog.exec()
    
    def _on_delete_card(self, card_id: int):
        """处理删除请求"""
        self._handle_card_deleted(card_id)
    
    def _handle_card_updated(self, card: ActivityCard):
        """处理卡片更新"""
        self.card_updated.emit(card)
        # 刷新显示
        self._refresh_cards()
    
    def _handle_card_deleted(self, card_id: int):
        """处理卡片删除"""
        self.card_deleted.emit(card_id)
        # 从本地列表移除
        self._cards = [c for c in self._cards if c.id != card_id]
        # 刷新显示
        self._refresh_cards()
    
    def _update_empty_state(self, cards: List[ActivityCard] = None):
        """更新空状态显示"""
        if cards is None:
            cards = self._cards
        
        if len(cards) == 0:
            self.empty_widget.set_search_mode(bool(self._search_text))
            self.empty_widget.setVisible(True)
        else:
            self.empty_widget.setVisible(False)
    
    def set_date(self, date: datetime):
        """设置当前日期"""
        self._current_date = date
    
    def clear(self):
        """清空时间轴"""
        self._cards = []
        self._refresh_cards()
    
    def get_current_date(self) -> datetime:
        """获取当前显示的日期"""
        return self._current_date
