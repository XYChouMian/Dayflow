"""Modern theme system with colors, gradients, and styles."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ColorPalette:
    """Color palette inspired by Dayflow macOS design."""

    # Primary gradients - warm tones
    gradient_orange_start = "#FFB84D"  # Warm orange
    gradient_orange_end = "#FF8A4D"    # Deep orange
    gradient_peach_start = "#FFE5CC"   # Light peach
    gradient_peach_end = "#FFD4A8"     # Darker peach

    # Secondary gradients - cool tones
    gradient_blue_start = "#A8D5FF"    # Light blue
    gradient_blue_end = "#5FB3FF"      # Bright blue
    gradient_purple_start = "#E5D4FF"  # Light purple
    gradient_purple_end = "#C5A8FF"    # Medium purple

    # Background colors
    bg_primary = "#FAFAFA"             # Light gray background
    bg_card = "#FFFFFF"                # White cards
    bg_sidebar = "#2C3E50"             # Dark blue sidebar
    bg_hover = "#F5F5F5"               # Hover state

    # Text colors
    text_primary = "#2C3E50"           # Dark blue-gray
    text_secondary = "#7F8C8D"         # Medium gray
    text_tertiary = "#BDC3C7"          # Light gray
    text_white = "#FFFFFF"             # White text
    text_accent = "#FF8A4D"            # Orange accent

    # Category colors (for badges)
    category_work = "#5FB3FF"          # Blue
    category_meeting = "#A078FF"       # Purple
    category_break = "#FF9EAA"         # Pink
    category_productivity = "#FFB84D"  # Orange
    category_learning = "#7ED957"      # Green
    category_entertainment = "#FF6B9D" # Coral
    category_other = "#95A5A6"         # Gray

    # Accent colors
    success = "#27AE60"                # Green
    warning = "#F39C12"                # Yellow-orange
    error = "#E74C3C"                  # Red
    info = "#3498DB"                   # Blue

    # Chart colors (for dashboard)
    chart_colors = [
        "#FFB84D",  # Orange
        "#5FB3FF",  # Blue
        "#A078FF",  # Purple
        "#7ED957",  # Green
        "#FF9EAA",  # Pink
        "#FFD700",  # Gold
        "#8B7AF5",  # Lavender
        "#50E3C2",  # Teal
    ]


class Theme:
    """Central theme configuration."""

    colors = ColorPalette()

    # Font sizes
    font_size_h1 = 28
    font_size_h2 = 24
    font_size_h3 = 18
    font_size_body = 14
    font_size_small = 12

    # Spacing
    spacing_xs = 4
    spacing_sm = 8
    spacing_md = 16
    spacing_lg = 24
    spacing_xl = 32

    # Border radius
    radius_sm = 8
    radius_md = 12
    radius_lg = 16
    radius_xl = 20

    # Shadows
    shadow_sm = "0 2px 8px rgba(0, 0, 0, 0.08)"
    shadow_md = "0 4px 16px rgba(0, 0, 0, 0.12)"
    shadow_lg = "0 8px 32px rgba(0, 0, 0, 0.16)"
    shadow_card = "0 2px 12px rgba(0, 0, 0, 0.08)"
    shadow_hover = "0 4px 20px rgba(0, 0, 0, 0.15)"

    @staticmethod
    def get_gradient_style(start_color: str, end_color: str, direction: str = "to bottom") -> str:
        """Generate CSS gradient style."""
        return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {start_color}, stop:1 {end_color})"

    @staticmethod
    def get_card_style(hover: bool = True) -> str:
        """Get modern card style."""
        style = f"""
            QFrame {{
                background-color: {Theme.colors.bg_card};
                border-radius: {Theme.radius_md}px;
                border: 1px solid rgba(0, 0, 0, 0.06);
                padding: {Theme.spacing_lg}px;
            }}
        """

        if hover:
            style += f"""
            QFrame:hover {{
                border-color: {Theme.colors.text_accent};
                box-shadow: {Theme.shadow_hover};
            }}
            """

        return style

    @staticmethod
    def get_button_style(
        bg_color: str = None,
        text_color: str = None,
        hover_bg: str = None,
    ) -> str:
        """Get modern button style."""
        bg = bg_color or Theme.colors.text_accent
        text = text_color or Theme.colors.text_white
        hover = hover_bg or "#FF7A3D"

        return f"""
            QPushButton {{
                background-color: {bg};
                color: {text};
                border: none;
                border-radius: {Theme.radius_sm}px;
                padding: {Theme.spacing_sm}px {Theme.spacing_md}px;
                font-size: {Theme.font_size_body}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                padding-top: {Theme.spacing_sm + 1}px;
            }}
        """

    @staticmethod
    def get_sidebar_style() -> str:
        """Get modern sidebar style."""
        return f"""
            QWidget#sidebar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34495E, stop:1 #2C3E50);
                border-right: 1px solid rgba(0, 0, 0, 0.1);
            }}
            QPushButton {{
                background-color: transparent;
                color: {Theme.colors.text_white};
                border: none;
                text-align: left;
                padding: {Theme.spacing_md}px {Theme.spacing_lg}px;
                font-size: {Theme.font_size_body}px;
                border-left: 3px solid transparent;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border-left: 3px solid {Theme.colors.text_accent};
            }}
            QPushButton:checked {{
                background-color: rgba(255, 138, 77, 0.15);
                border-left: 3px solid {Theme.colors.text_accent};
                font-weight: 600;
            }}
            QLabel {{
                color: {Theme.colors.text_white};
                padding: {Theme.spacing_lg}px;
                font-size: {Theme.font_size_h2}px;
                font-weight: bold;
            }}
        """

    @staticmethod
    def get_category_color(category_name: str) -> str:
        """
        Get color for activity category.

        Supports both Chinese and English category names for compatibility.

        Args:
            category_name: Category name in Chinese or English

        Returns:
            Hex color code for the category
        """
        category_map = {
            # Chinese category names
            "工作": Theme.colors.category_work,
            "会议": Theme.colors.category_meeting,
            "休息": Theme.colors.category_break,
            "效率": Theme.colors.category_productivity,
            "学习": Theme.colors.category_learning,
            "娱乐": Theme.colors.category_entertainment,
            "其他": Theme.colors.category_other,
            # English category names (for compatibility)
            "Work": Theme.colors.category_work,
            "Meeting": Theme.colors.category_meeting,
            "Break": Theme.colors.category_break,
            "Productivity": Theme.colors.category_productivity,
            "Learning": Theme.colors.category_learning,
            "Entertainment": Theme.colors.category_entertainment,
            "Other": Theme.colors.category_other,
        }
        return category_map.get(category_name, Theme.colors.category_other)

    @staticmethod
    def translate_category_to_chinese(category_name: str) -> str:
        """
        Translate category name to Chinese for display.

        Args:
            category_name: Category name in English or Chinese

        Returns:
            Chinese category name
        """
        translation_map = {
            "Work": "工作",
            "Meeting": "会议",
            "Break": "休息",
            "Productivity": "效率",
            "Learning": "学习",
            "Entertainment": "娱乐",
            "Other": "其他",
        }
        # If already in Chinese, return as is
        # Otherwise translate from English
        return translation_map.get(category_name, category_name)

    @staticmethod
    def is_productive_category(category_name: str) -> bool:
        """
        Check if a category is considered productive.

        Args:
            category_name: Category name in English or Chinese

        Returns:
            True if category is productive
        """
        productive_categories = {
            # Chinese
            "工作", "效率", "学习",
            # English
            "Work", "Productivity", "Learning"
        }
        return category_name in productive_categories
