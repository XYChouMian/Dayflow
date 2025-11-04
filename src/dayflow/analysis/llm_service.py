"""Abstract base class for LLM services."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime


class ActivitySegment:
    """Represents a detected activity segment."""

    def __init__(
        self,
        start_time: datetime,
        end_time: datetime,
        title: str,
        summary: str,
        category: Optional[str] = None,
    ):
        self.start_time = start_time
        self.end_time = end_time
        self.title = title
        self.summary = summary
        self.category = category

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "title": self.title,
            "summary": self.summary,
            "category": self.category,
        }


class LLMService(ABC):
    """
    Abstract base class for LLM services.
    Provides interface for analyzing screen recordings and generating activity summaries.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM service.

        Args:
            api_key: Optional API key for cloud services
        """
        self.api_key = api_key

    @abstractmethod
    def analyze_video(
        self,
        video_path: Path,
        context: Optional[str] = None,
    ) -> List[ActivitySegment]:
        """
        Analyze a video file and extract activity segments.

        Args:
            video_path: Path to video file
            context: Optional context from previous activities

        Returns:
            List of ActivitySegment objects
        """
        pass

    @abstractmethod
    def analyze_frames(
        self,
        frame_paths: List[Path],
        timestamps: List[datetime],
        context: Optional[str] = None,
    ) -> List[ActivitySegment]:
        """
        Analyze individual frames and extract activity segments.
        Used for local models that don't support direct video input.

        Args:
            frame_paths: List of paths to frame images
            timestamps: Corresponding timestamps for each frame
            context: Optional context from previous activities

        Returns:
            List of ActivitySegment objects
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if the service is available and configured correctly.

        Returns:
            True if service is available
        """
        pass

    def get_analysis_prompt(self, is_video: bool = True) -> str:
        """
        Get the analysis prompt template.

        Args:
            is_video: Whether analyzing video or frames

        Returns:
            Prompt string
        """
        if is_video:
            return """
请分析这段屏幕录制，识别出发生的不同活动。

对于每个活动，请提供：
1. 大致的开始和结束时间（相对于视频）
2. 简短的描述性标题（最多50个字符）
3. 对正在做什么的详细摘要（2-3句话）
4. 建议的分类：工作、会议、休息、效率、学习、娱乐 或 其他

请专注于有意义的活动（而不仅仅是切换标签或瞬时操作）。
将相似的连续活动组合在一起。

请使用中文回复，并将响应格式化为JSON数组：
[
  {
    "start_minutes": 0,
    "end_minutes": 5,
    "title": "在VS Code中进行代码审查",
    "summary": "审查新功能的拉取请求。检查代码更改，在特定行留下评论。在验证测试通过后批准了PR。",
    "category": "工作"
  },
  ...
]
"""
        else:
            return """
请分析这些随时间拍摄的屏幕截图，识别出发生了什么活动。

对于每个不同的活动，请提供：
1. 基于屏幕截图序列的大致时间范围
2. 简短的描述性标题（最多50个字符）
3. 对正在做什么的详细摘要（2-3句话）
4. 建议的分类：工作、会议、休息、效率、学习、娱乐 或 其他

请专注于有意义的活动。将相似的连续屏幕截图组合在一起。

请使用中文回复，并将响应格式化为JSON数组：
[
  {
    "start_index": 0,
    "end_index": 3,
    "title": "邮件管理",
    "summary": "处理收件箱，回复电子邮件，整理文件夹。",
    "category": "工作"
  },
  ...
]
"""

    def parse_category(self, category_str: str) -> str:
        """
        Normalize category string to known categories.

        Args:
            category_str: Raw category string from LLM

        Returns:
            Normalized category name
        """
        category_map = {
            # 中文分类
            "工作": "工作",
            "会议": "会议",
            "休息": "休息",
            "效率": "效率",
            "学习": "学习",
            "娱乐": "娱乐",
            "编程": "工作",
            "开发": "工作",
            "研究": "学习",
            "阅读": "学习",
            "视频": "娱乐",
            "游戏": "娱乐",
            # English fallback
            "work": "工作",
            "meeting": "会议",
            "break": "休息",
            "productivity": "效率",
            "learning": "学习",
            "entertainment": "娱乐",
            "coding": "工作",
            "development": "工作",
            "research": "学习",
            "reading": "学习",
            "video": "娱乐",
            "gaming": "娱乐",
        }

        normalized = category_str.lower().strip()
        return category_map.get(normalized, "其他")
