"""
Dayflow Windows - 灵感视图组件
"""
import logging
from datetime import datetime
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QSizePolicy, QPushButton, QTextEdit, QDialog,
    QMessageBox, QLineEdit, QMenu, QComboBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QAction, QColor, QPalette
from ui.themes import show_information, show_warning, show_critical, show_question

from core.types import InspirationCard
from ui.themes import get_theme_manager, get_theme, get_category_color
import sys
import ctypes

logger = logging.getLogger(__name__)


class InspirationEditDialog(QDialog):
    """灵感编辑对话框"""
    
    inspiration_saved = Signal(object)
    inspiration_deleted = Signal(int)
    
    def __init__(self, card: Optional[InspirationCard], parent=None, category: str = "灵感"):
        super().__init__(parent)
        self.card = card
        self._is_new = card is None or card.id is None
        self._default_category = category
        self.setWindowTitle("快速记录")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 时间信息（只读）
        if self.card and self.card.timestamp:
            time_label = QLabel(f"🕐 记录时间: {self.card.timestamp.strftime('%Y-%m-%d %H:%M')}")
            time_label.setObjectName("timeInfo")
            layout.addWidget(time_label)
        
        # 类别选择
        category_layout = QHBoxLayout()
        category_label = QLabel("类别")
        category_label.setFixedWidth(60)
        self.category_input = QComboBox()
        self.category_input.addItems(["灵感", "想法", "待办"])
        if self.card:
            self.category_input.setCurrentText(self.card.category)
        else:
            self.category_input.setCurrentText(self._default_category)
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_input)
        layout.addLayout(category_layout)
        
        # 灵感内容输入
        content_layout = QVBoxLayout()
        content_label = QLabel("灵感内容")
        self.content_input = QTextEdit()
        self.content_input.setPlainText(self.card.content if self.card else "")
        self.content_input.setPlaceholderText("记录你的想法...")
        self.content_input.setMinimumHeight(150)
        content_layout.addWidget(content_label)
        content_layout.addWidget(self.content_input)
        layout.addLayout(content_layout)
        
        # 备注输入
        notes_layout = QHBoxLayout()
        notes_label = QLabel("备注")
        notes_label.setFixedWidth(60)
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("用逗号分隔备注，如：重要,待处理,需要讨论")
        if self.card and self.card.notes:
            self.notes_input.setText(",".join(self.card.notes))
        notes_layout.addWidget(notes_label)
        notes_layout.addWidget(self.notes_input)
        layout.addLayout(notes_layout)
        
        layout.addStretch()
        
        # 按钮行
        btn_layout = QHBoxLayout()
        
        if not self._is_new:
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
    
    def _on_save(self):
        """保存"""
        content = self.content_input.toPlainText().strip()
        if not content:
            show_warning(self, "提示", "请输入灵感内容")
            return
        
        # 解析类别
        category = self.category_input.currentText().strip() or "灵感"
        
        # 解析备注
        notes_text = self.notes_input.text().strip()
        notes = [note.strip() for note in notes_text.split(",") if note.strip()] if notes_text else []
        
        # 更新或创建卡片
        if self.card:
            self.card.content = content
            self.card.category = category
            self.card.notes = notes
            if not self.card.timestamp:
                self.card.timestamp = datetime.now()
        else:
            self.card = InspirationCard(
                content=content,
                timestamp=datetime.now(),
                category=category,
                notes=notes
            )
        
        self.inspiration_saved.emit(self.card)
        self.accept()
    
    def _on_delete(self):
        """删除"""
        if not self.card or self.card.id is None:
            return
        
        reply = show_question(
            self,
            "确认删除",
            "确定要删除这条灵感记录吗？\n\n此操作不可撤销。"
        )
        
        if reply == QMessageBox.Yes:
            self.inspiration_deleted.emit(self.card.id)
            self.accept()
    
    def _set_dark_title_bar(self, is_dark: bool = True):
        """设置 Windows 原生标题栏颜色为暗色"""
        try:
            hwnd = self.winId()
            
            # 定义 DWM 窗口属性常量
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
    
    def apply_theme(self):
        t = get_theme()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg_primary};
                border: 1px solid {t.border};
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
            QTextEdit {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 12px;
                color: {t.text_primary};
                font-size: 14px;
            }}
            QTextEdit:focus {{
                border-color: {t.accent};
            }}
            QLineEdit {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 10px;
                color: {t.text_primary};
                font-size: 14px;
            }}
            QLineEdit:focus {{
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
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {t.text_primary};
                width: 0;
                height: 0;
            }}
            QComboBox QAbstractItemView {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                selection-background-color: {t.bg_hover};
                selection-color: {t.text_primary};
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
                self._set_dark_title_bar(is_dark=True)
        else:
            # 亮色主题
            palette.setColor(QPalette.Window, QColor(t.bg_primary))
            palette.setColor(QPalette.WindowText, QColor(t.text_primary))
            palette.setColor(QPalette.Base, QColor("#FFFFFF"))
            palette.setColor(QPalette.Text, QColor(t.text_primary))
        
        self.setPalette(palette)
        
        if not self._is_new:
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


class InspirationCardWidget(QFrame):
    """单个灵感卡片组件"""
    
    edit_requested = Signal(InspirationCard)
    delete_requested = Signal(int)
    
    def __init__(self, card: InspirationCard, parent=None):
        super().__init__(parent)
        self.card = card
        self._setup_ui()
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
    
    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.edit_requested.emit(self.card)
        super().mousePressEvent(event)
    
    def _setup_ui(self):
        t = get_theme()
        self.setObjectName("inspirationCard")
        self.setFrameShape(QFrame.StyledPanel)
        
        # 获取类别颜色
        category_text = self.card.category or "灵感"
        category_color = get_category_color(category_text)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        
        # 顶部：类别标签 + 时间
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)
        
        # 类别标签 - 使用用户定义的类别
        self.category_label = QLabel(category_text)
        
        # 解析颜色并转换为 rgba 格式
        color = QColor(category_color)
        self.category_color_rgb = (color.red(), color.green(), color.blue())
        
        # 使用 rgba() 格式设置带透明度的背景颜色
        r, g, b = self.category_color_rgb
        self.category_label.setStyleSheet(f"""
            background-color: rgba({r}, {g}, {b}, 0.4);
            color: {t.text_primary};
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        """)
        top_layout.addWidget(self.category_label)
        
        # 时间点
        time_str = self.card.timestamp.strftime("%H:%M") if self.card.timestamp else ""
        self.time_label = QLabel(time_str)
        self.time_label.setObjectName("timeLabel")
        self.time_label.setStyleSheet(f"""
            QLabel#timeLabel {{
                color: {t.text_muted};
                font-size: 12px;
            }}
        """)
        top_layout.addWidget(self.time_label)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        # 内容（作为主要文本）
        self.content_label = QLabel(self.card.content)
        self.content_label.setObjectName("contentLabel")
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet(f"""
            QLabel#contentLabel {{
                color: {t.text_primary};
                font-size: 15px;
                line-height: 1.6;
                padding: 4px 0;
            }}
        """)
        layout.addWidget(self.content_label)
        
        # 备注
        self.note_labels = []
        if self.card.notes:
            self.notes_layout = QHBoxLayout()
            self.notes_layout.setSpacing(6)
            
            for note in self.card.notes[:4]:
                note_label = QLabel(f"#{note}")
                note_label.setStyleSheet(f"""
                    background-color: {t.bg_tertiary};
                    color: {t.text_secondary};
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                """)
                self.notes_layout.addWidget(note_label)
                self.note_labels.append(note_label)
            
            if len(self.card.notes) > 4:
                self.more_label = QLabel(f"+{len(self.card.notes) - 4}")
                self.more_label.setStyleSheet(f"""
                    color: {t.text_muted};
                    font-size: 11px;
                """)
                self.notes_layout.addWidget(self.more_label)
                self.note_labels.append(self.more_label)
            
            self.notes_layout.addStretch()
            layout.addLayout(self.notes_layout)
    
    def apply_theme(self):
        t = get_theme()
        category_text = self.card.category or "灵感"
        category_color = get_category_color(category_text)
        r, g, b = self.category_color_rgb
        
        # 更新类别标签颜色
        self.category_label.setStyleSheet(f"""
            background-color: rgba({r}, {g}, {b}, 0.4);
            color: {t.text_primary};
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        """)
        
        # 更新时间标签颜色
        self.time_label.setStyleSheet(f"""
            QLabel#timeLabel {{
                color: {t.text_muted};
                font-size: 12px;
            }}
        """)
        
        # 更新内容标签颜色
        self.content_label.setStyleSheet(f"""
            QLabel#contentLabel {{
                color: {t.text_primary};
                font-size: 15px;
                line-height: 1.6;
                padding: 4px 0;
            }}
        """)
        
        # 更新备注标签颜色
        for note_label in self.note_labels:
            if hasattr(note_label, 'text') and note_label.text().startswith('#'):
                note_label.setStyleSheet(f"""
                    background-color: {t.bg_tertiary};
                    color: {t.text_secondary};
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                """)
            else:
                note_label.setStyleSheet(f"""
                    color: {t.text_muted};
                    font-size: 11px;
                """)
        
        # 更新卡片边框和背景
        self.setStyleSheet(f"""
            QFrame#inspirationCard {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-left: 4px solid {category_color};
                border-radius: 0px 16px 16px 0px;
            }}
            QFrame#inspirationCard:hover {{
                background-color: {t.bg_hover};
                border-color: {t.accent};
            }}
        """)
    
    def _set_dark_title_bar(self, is_dark: bool = True):
        """设置 Windows 原生标题栏颜色为暗色"""
        try:
            hwnd = self.winId()
            
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
        
        edit_action = QAction("✏️ 编辑", self)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.card))
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        delete_action = QAction("🗑️ 删除", self)
        delete_action.triggered.connect(lambda: self._confirm_delete())
        menu.addAction(delete_action)
        
        menu.exec(self.mapToGlobal(pos))
    
    def _confirm_delete(self):
        """确认删除"""
        reply = show_question(
            self,
            "确认删除",
            f"确定要删除这条灵感吗？\n\n「{self.card.content[:30]}...」"
        )
        if reply == QMessageBox.Yes:
            self.delete_requested.emit(self.card.id)


class InspirationView(QWidget):
    """灵感视图"""
    
    inspiration_updated = Signal()
    
    def __init__(self, storage=None, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._date = datetime.now()
        self._cards: List[InspirationCard] = []
        self._setup_ui()
        self.apply_theme()
        get_theme_manager().theme_changed.connect(self.apply_theme)
        self._load_inspirations()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 操作按钮区域
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(24, 16, 24, 16)
        action_layout.addStretch()
        
        # 快速添加按钮 - 灵感
        self.add_btn_inspiration = QPushButton("💡 灵感")
        self.add_btn_inspiration.setMinimumWidth(100)
        self.add_btn_inspiration.setFixedHeight(44)
        self.add_btn_inspiration.setCursor(Qt.PointingHandCursor)
        self.add_btn_inspiration.clicked.connect(lambda: self._on_add_inspiration("灵感"))
        action_layout.addWidget(self.add_btn_inspiration)
        
        # 快速添加按钮 - 想法
        self.add_btn_idea = QPushButton("💭 想法")
        self.add_btn_idea.setMinimumWidth(100)
        self.add_btn_idea.setFixedHeight(44)
        self.add_btn_idea.setCursor(Qt.PointingHandCursor)
        self.add_btn_idea.clicked.connect(lambda: self._on_add_inspiration("想法"))
        action_layout.addWidget(self.add_btn_idea)
        
        # 快速添加按钮 - 待办
        self.add_btn_todo = QPushButton("📋 待办")
        self.add_btn_todo.setMinimumWidth(100)
        self.add_btn_todo.setFixedHeight(44)
        self.add_btn_todo.setCursor(Qt.PointingHandCursor)
        self.add_btn_todo.clicked.connect(lambda: self._on_add_inspiration("待办"))
        action_layout.addWidget(self.add_btn_todo)
        
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        # 灵感卡片列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(24, 8, 24, 24)
        self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch()
        
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)
    
    def apply_theme(self):
        """应用主题"""
        t = get_theme()
        
        # 灵感按钮样式 - 紫色
        self.add_btn_inspiration.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9B59B6, stop:1 #8E44AD);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8E44AD, stop:1 #9B59B6);
            }}
            QPushButton:pressed {{
                background-color: #9B59B6;
            }}
        """)
        
        # 想法按钮样式 - 青色
        self.add_btn_idea.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #06B6D4, stop:1 #0891B2);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0891B2, stop:1 #06B6D4);
            }}
            QPushButton:pressed {{
                background-color: #06B6D4;
            }}
        """)
        
        # 待办按钮样式 - 红色
        self.add_btn_todo.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EF4444, stop:1 #DC2626);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #DC2626, stop:1 #EF4444);
            }}
            QPushButton:pressed {{
                background-color: #EF4444;
            }}
        """)
        
        # 滚动区域样式
        self.cards_container.setStyleSheet(f"""
            background-color: {t.bg_primary};
        """)
    
    def _on_add_inspiration(self, category: str = "灵感"):
        """添加新灵感"""
        dialog = InspirationEditDialog(None, self, category)
        dialog.inspiration_saved.connect(self._on_inspiration_saved)
        dialog.exec()
    
    def _on_inspiration_saved(self, card: InspirationCard):
        """灵感保存"""
        try:
            if self._storage:
                if card.id is None:
                    card_id = self._storage.save_inspiration(card)
                    card.id = card_id
                    logger.info(f"已保存新灵感，ID: {card_id}")
                else:
                    self._storage.update_inspiration(card)
                    logger.info(f"已更新灵感，ID: {card.id}")
            
            # 刷新列表
            self._load_inspirations()
            self.inspiration_updated.emit()
        except Exception as e:
            logger.error(f"保存灵感失败: {e}")
            show_critical(self, "错误", f"保存灵感失败:\n{e}")
    
    def _on_inspiration_deleted(self, card_id: int):
        """灵感删除"""
        try:
            if self._storage:
                self._storage.delete_inspiration(card_id)
                logger.info(f"已删除灵感，ID: {card_id}")
            
            # 刷新列表
            self._load_inspirations()
            self.inspiration_updated.emit()
        except Exception as e:
            logger.error(f"删除灵感失败: {e}")
            show_critical(self, "错误", f"删除灵感失败:\n{e}")
    
    def _on_edit_card(self, card: InspirationCard):
        """编辑卡片"""
        dialog = InspirationEditDialog(card, self)
        dialog.inspiration_saved.connect(self._on_inspiration_saved)
        dialog.inspiration_deleted.connect(self._on_inspiration_deleted)
        dialog.exec()
    
    def _load_inspirations(self):
        """加载灵感列表"""
        if not self._storage:
            return
        
        try:
            logger.info(f"正在加载灵感记录，日期: {self._date}")
            self._cards = self._storage.get_inspirations_by_date(self._date)
            logger.info(f"加载灵感记录完成，数量: {len(self._cards) if self._cards else 0}")
            self._update_cards_display()
        except Exception as e:
            logger.error(f"加载灵感失败: {e}")
    
    def _update_cards_display(self):
        """更新卡片显示"""
        # 清除现有卡片（保留最后的stretch）
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self._cards:
            # 显示空状态
            t = get_theme()
            empty_label = QLabel("还没有记录任何灵感\n点击上方的按钮开始记录你的想法")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet(f"""
                color: {t.text_muted};
                font-size: 14px;
                line-height: 1.8;
                padding: 40px;
            """)
            self.cards_layout.insertWidget(0, empty_label)
            return
        
        # 添加卡片（倒序插入）
        for card in reversed(self._cards):
            card_widget = InspirationCardWidget(card)
            card_widget.edit_requested.connect(self._on_edit_card)
            card_widget.delete_requested.connect(self._on_inspiration_deleted)
            self.cards_layout.insertWidget(0, card_widget)
    
    def set_date(self, date: datetime):
        """设置日期"""
        self._date = date
        self._load_inspirations()
    
    def set_storage(self, storage):
        """设置存储管理器"""
        self._storage = storage
        self._load_inspirations()
    
    def get_cards(self) -> List[InspirationCard]:
        """获取灵感卡片列表"""
        return self._cards
