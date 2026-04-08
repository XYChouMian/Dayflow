"""
Dayflow Windows - 主题管理
IDE 风格的亮色/暗色主题
"""
from dataclasses import dataclass
from typing import Optional
import sys
import time
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog, QWidget
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QPalette, QColor

if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes


# 类别颜色映射
CATEGORY_COLORS = {
    "工作": "#4F46E5",      # Indigo
    "Work": "#4F46E5",
    "学习": "#0EA5E9",      # Sky Blue
    "Study": "#0EA5E9",
    "编程": "#10B981",      # Emerald
    "Coding": "#10B981",
    "会议": "#F59E0B",      # Amber
    "Meeting": "#F59E0B",
    "娱乐": "#EC4899",      # Pink
    "Entertainment": "#EC4899",
    "社交": "#8B5CF6",      # Violet
    "Social": "#8B5CF6",
    "休息": "#6B7280",      # Gray
    "Break": "#6B7280",
    "其他": "#78716C",      # Stone
    "Other": "#78716C",
    "灵感": "#9B59B6",      # Purple
    "想法": "#06B6D4",      # Cyan
    "待办": "#EF4444",      # Red
}


@dataclass
class Theme:
    """主题颜色定义"""
    name: str
    
    # 背景色
    bg_primary: str      # 主背景
    bg_secondary: str    # 次背景（卡片、面板）
    bg_tertiary: str     # 第三背景（输入框）
    bg_hover: str        # 悬停背景
    bg_sidebar: str      # 侧边栏
    
    # 边框
    border: str
    border_hover: str
    
    # 文字
    text_primary: str    # 主文字
    text_secondary: str  # 次文字
    text_muted: str      # 弱化文字
    
    # 强调色
    accent: str          # 主强调色
    accent_hover: str    # 强调色悬停
    accent_light: str    # 浅强调色（背景用）
    
    # 功能色
    success: str
    warning: str
    error: str
    
    # 滚动条
    scrollbar: str
    scrollbar_hover: str
    
    # 卡片阴影
    shadow: str


# 暗色主题 - Apple 风格深色
DARK_THEME = Theme(
    name="dark",
    bg_primary="#1C1C1E",       # Apple 深灰背景
    bg_secondary="#2C2C2E",     # 卡片背景 - 略浅
    bg_tertiary="#3A3A3C",      # 输入框背景
    bg_hover="#48484A",         # 悬停背景
    bg_sidebar="#1C1C1E",       # 侧边栏
    border="#3A3A3C",           # 柔和边框
    border_hover="#545456",
    text_primary="#FFFFFF",     # 纯白
    text_secondary="#EBEBF5",   # 次要文字 - Apple 风格
    text_muted="#8E8E93",       # 弱化文字 - Apple 灰
    accent="#0A84FF",           # Apple 蓝
    accent_hover="#409CFF",
    accent_light="rgba(10, 132, 255, 0.15)",
    success="#30D158",          # Apple 绿
    warning="#FF9F0A",          # Apple 橙
    error="#FF453A",            # Apple 红
    scrollbar="#48484A",
    scrollbar_hover="#636366",
    shadow="rgba(0, 0, 0, 0.35)",
)


# 亮色主题 - Apple 风格浅色
LIGHT_THEME = Theme(
    name="light",
    bg_primary="#FFFFFF",       # 纯白
    bg_secondary="#F2F2F7",     # Apple 浅灰背景
    bg_tertiary="#E5E5EA",      # 输入框背景
    bg_hover="#D1D1D6",         # 悬停
    bg_sidebar="#F2F2F7",       # 侧边栏
    border="#C6C6C8",           # Apple 边框
    border_hover="#AEAEB2",
    text_primary="#000000",     # 纯黑
    text_secondary="#3C3C43",   # 次要文字
    text_muted="#8E8E93",       # 弱化文字
    accent="#007AFF",           # Apple 蓝
    accent_hover="#0056CC",
    accent_light="rgba(0, 122, 255, 0.12)",
    success="#34C759",          # Apple 绿
    warning="#FF9500",          # Apple 橙
    error="#FF3B30",            # Apple 红
    scrollbar="#C6C6C8",
    scrollbar_hover="#AEAEB2",
    shadow="rgba(0, 0, 0, 0.08)",
)


class ThemeManager(QObject):
    """主题管理器"""
    
    theme_changed = Signal(object)  # 传递 Theme 对象
    
    _instance: Optional['ThemeManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._current_theme = LIGHT_THEME
        self._initialized = True
    
    @property
    def current_theme(self) -> Theme:
        return self._current_theme
    
    @property
    def is_dark(self) -> bool:
        return self._current_theme.name == "dark"
    
    def set_theme(self, theme: Theme, emit_signal: bool = True):
        """设置主题
        
        Args:
            theme: 主题对象
            emit_signal: 是否立即发出主题变化信号
        """
        if self._current_theme == theme:
            return  # 避免重复切换
        self._current_theme = theme
        
        start_time = time.time()
        self._apply_global_theme()
        global_theme_time = time.time() - start_time
        print(f"[主题切换] _apply_global_theme 耗时: {global_theme_time*1000:.2f}ms")
        
        if emit_signal:
            start_time = time.time()
            self.theme_changed.emit(theme)
            signal_time = time.time() - start_time
            print(f"[主题切换] theme_changed 信号发出耗时: {signal_time*1000:.2f}ms")
    
    def toggle_theme(self):
        """切换主题"""
        if self.is_dark:
            self.set_theme(LIGHT_THEME, emit_signal=False)
        else:
            self.set_theme(DARK_THEME, emit_signal=False)
        
        # 延迟发出信号，让全局样式先应用完成
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._delayed_theme_changed)
    
    def _delayed_theme_changed(self):
        """延迟发出主题变化信号"""
        self.theme_changed.emit(self._current_theme)
    
    def _apply_global_theme(self):
        """应用全局样式"""
        app = QApplication.instance()
        if app:
            start_time = time.time()
            app.setStyleSheet(self.get_global_stylesheet())
            stylesheet_time = time.time() - start_time
            print(f"[主题切换] setStyleSheet 耗时: {stylesheet_time*1000:.2f}ms")
            
            start_time = time.time()
            self._apply_palette(app)
            palette_time = time.time() - start_time
            print(f"[主题切换] _apply_palette 耗时: {palette_time*1000:.2f}ms")
    
    def _apply_palette(self, app):
        """应用调色板以控制对话框标题栏颜色"""
        palette = app.palette()
        t = self._current_theme
        
        # 只设置必要的颜色，减少调色板刷新开销
        palette.setColor(QPalette.Window, QColor(t.bg_primary))
        palette.setColor(QPalette.WindowText, QColor(t.text_primary))
        
        if t.name == "dark":
            palette.setColor(QPalette.Base, QColor(t.bg_secondary))
            palette.setColor(QPalette.ToolTipBase, QColor(t.bg_primary))
        else:
            palette.setColor(QPalette.Base, QColor("#FFFFFF"))
            palette.setColor(QPalette.ToolTipBase, QColor("#FFFFF0"))
        
        palette.setColor(QPalette.Text, QColor(t.text_primary))
        palette.setColor(QPalette.Button, QColor(t.bg_tertiary))
        palette.setColor(QPalette.ButtonText, QColor(t.text_primary))
        palette.setColor(QPalette.Link, QColor(t.accent))
        palette.setColor(QPalette.Highlight, QColor(t.accent))
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        
        app.setPalette(palette)
    
    def get_global_stylesheet(self) -> str:
        """生成全局样式表"""
        t = self._current_theme
        return f"""
            /* ===== 全局基础 ===== */
            QMainWindow {{
                background-color: {t.bg_primary};
            }}
            
            QWidget {{
                color: {t.text_primary};
                font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
            }}
            
            /* ===== 滚动条 ===== */
            QScrollBar:vertical {{
                width: 14px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {t.scrollbar};
                border-radius: 0px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t.scrollbar_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            
            /* ===== 输入框 ===== */
            QLineEdit {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 10px 14px;
                color: {t.text_primary};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {t.accent};
            }}
            
            /* ===== 按钮 ===== */
            QPushButton {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {t.bg_hover};
            }}
            QPushButton:disabled {{
                background-color: {t.bg_secondary};
                color: {t.text_muted};
            }}
            
            /* ===== 对话框 ===== */
            QDialog {{
                background-color: {t.bg_primary};
                color: {t.text_primary};
            }}
            
            /* ===== 表头 ===== */
            QHeaderView::section {{
                background-color: {t.bg_secondary};
                color: {t.text_primary};
                padding: 6px 12px;
                border: none;
                border-right: 1px solid {t.border};
                border-bottom: 1px solid {t.border};
                font-weight: 600;
            }}
            
            /* ===== 菜单 ===== */
            QMenu {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 8px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
        """


# 全局函数
def get_theme_manager() -> ThemeManager:
    """获取主题管理器实例"""
    return ThemeManager()


def get_efficiency_color(score: float, theme: 'Theme' = None) -> str:
    """根据效率分数获取对应颜色
    
    Args:
        score: 效率分数 (0-100)
        theme: 主题对象，默认使用当前主题
    
    Returns:
        颜色值字符串
    """
    if theme is None:
        theme = get_theme()
    
    if score >= 70:
        return theme.success  # 绿色 - 高效
    elif score >= 40:
        return theme.warning  # 橙色 - 中等
    else:
        return theme.text_muted  # 灰色 - 低效


def get_theme() -> Theme:
    """获取当前主题"""
    return get_theme_manager().current_theme


def is_dark_theme() -> bool:
    """是否为暗色主题"""
    return get_theme_manager().is_dark


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
            logger = __import__('logging').getLogger(__name__)
            logger.debug(f"设置标题栏颜色失败: {e}")


def create_themed_message_box(parent: Optional[QWidget] = None) -> QMessageBox:
    """创建应用主题的消息框"""
    msg_box = QMessageBox(parent)
    msg_box.setStyleSheet(get_theme_manager().get_global_stylesheet())
    
    # 设置 QPalette 以修复暗色主题下的标题栏颜色
    theme = get_theme()
    palette = msg_box.palette()
    
    if theme.name == "dark":
        # 暗色主题 - 设置窗口颜色
        palette.setColor(QPalette.Window, QColor(theme.bg_primary))
        palette.setColor(QPalette.WindowText, QColor(theme.text_primary))
        palette.setColor(QPalette.Base, QColor(theme.bg_secondary))
        palette.setColor(QPalette.Text, QColor(theme.text_primary))
        palette.setColor(QPalette.Button, QColor(theme.bg_tertiary))
        palette.setColor(QPalette.ButtonText, QColor(theme.text_primary))
        
        # 设置 Windows 原生标题栏为暗色
        if sys.platform == 'win32':
            _set_dark_title_bar(msg_box, is_dark=True)
    else:
        # 亮色主题
        palette.setColor(QPalette.Window, QColor(theme.bg_primary))
        palette.setColor(QPalette.WindowText, QColor(theme.text_primary))
        palette.setColor(QPalette.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.Text, QColor(theme.text_primary))
    
    msg_box.setPalette(palette)
    return msg_box


def create_themed_dialog(parent: Optional[QWidget] = None) -> QDialog:
    """创建应用主题的对话框"""
    dialog = QDialog(parent)
    dialog.setStyleSheet(get_theme_manager().get_global_stylesheet())
    return dialog


def show_information(parent: Optional[QWidget], title: str, message: str) -> None:
    """显示信息弹窗（应用主题）"""
    msg_box = create_themed_message_box(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Information)
    msg_box.exec()


def show_warning(parent: Optional[QWidget], title: str, message: str) -> None:
    """显示警告弹窗（应用主题）"""
    msg_box = create_themed_message_box(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Warning)
    msg_box.exec()


def show_critical(parent: Optional[QWidget], title: str, message: str) -> None:
    """显示错误弹窗（应用主题）"""
    msg_box = create_themed_message_box(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.exec()


def show_question(parent: Optional[QWidget], title: str, message: str, buttons=QMessageBox.Yes | QMessageBox.No) -> int:
    """显示问题弹窗（应用主题）"""
    msg_box = create_themed_message_box(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(buttons)
    msg_box.setDefaultButton(QMessageBox.Yes)
    return msg_box.exec()


def get_category_color(category: str) -> str:
    """获取类别对应的颜色"""
    return CATEGORY_COLORS.get(category, "#78716C")
