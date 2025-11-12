"""Daily summary service - generates AI summaries from timeline activities."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from dayflow.models.database import get_session_direct
from dayflow.models.timeline_activity import TimelineActivity
from dayflow.models.daily_summary import DailySummary
from dayflow.analysis.gemini_service import GeminiService
from dayflow.utils.security import SecureStorage
from dayflow.ui.theme import Theme

logger = logging.getLogger(__name__)


class DailySummaryService:
    """Service for generating and managing daily summaries."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-lite"):
        """
        Initialize daily summary service.

        Args:
            api_key: API key for LLM service (if None, will try to get from secure storage)
            model_name: LLM model to use for summary generation
        """
        self.model_name = model_name
        self.api_key = api_key or self._get_api_key()
        self.llm_service = None

        if self.api_key:
            try:
                self.llm_service = GeminiService(api_key=self.api_key, model_name=self.model_name)
                logger.info(f"Daily summary service initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize LLM service: {e}")

    def _get_api_key(self) -> Optional[str]:
        """Get API key from secure storage."""
        try:
            return SecureStorage.get_api_key("gemini")
        except Exception as e:
            logger.error(f"Failed to get API key: {e}")
            return None

    def generate_summary(
        self,
        date: datetime,
        user_notes: Optional[str] = None,
        force_regenerate: bool = False
    ) -> Optional[DailySummary]:
        """
        Generate daily summary for a specific date.

        Args:
            date: Date to generate summary for
            user_notes: Optional user notes to include in summary
            force_regenerate: If True, regenerate even if summary exists

        Returns:
            DailySummary object or None if generation failed
        """
        if not self.llm_service:
            logger.error("LLM service not initialized")
            return None

        session = get_session_direct()
        try:
            # Normalize date to start of day
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            # Check if summary already exists
            existing_summary = (
                session.query(DailySummary)
                .filter(DailySummary.date == day_start.date())
                .first()
            )

            if existing_summary and not force_regenerate:
                logger.info(f"Summary already exists for {day_start.date()}")
                # Update user notes if provided
                if user_notes:
                    existing_summary.user_notes = user_notes
                    existing_summary.updated_at = datetime.utcnow()
                    session.commit()
                return existing_summary

            # Query activities for the date
            activities = (
                session.query(TimelineActivity)
                .filter(
                    TimelineActivity.start_time >= day_start,
                    TimelineActivity.start_time < day_end,
                )
                .order_by(TimelineActivity.start_time)
                .all()
            )

            if not activities:
                logger.info(f"No activities found for {day_start.date()}")
                # Still create/update summary with user notes
                if existing_summary:
                    existing_summary.user_notes = user_notes
                    existing_summary.ai_summary = "今天没有记录到活动。"
                    existing_summary.activity_count = 0
                    existing_summary.total_minutes = 0
                    existing_summary.productive_minutes = 0
                    existing_summary.updated_at = datetime.utcnow()
                    session.commit()
                    return existing_summary
                else:
                    new_summary = DailySummary(
                        date=day_start.date(),
                        user_notes=user_notes,
                        ai_summary="今天没有记录到活动。",
                        activity_count=0,
                        total_minutes=0,
                        productive_minutes=0,
                    )
                    session.add(new_summary)
                    session.commit()
                    return new_summary

            # Calculate statistics
            stats = self._calculate_statistics(activities)

            # Generate AI summary
            ai_summary = self._generate_ai_summary(day_start, activities, stats, user_notes)

            # Save or update summary
            if existing_summary:
                existing_summary.ai_summary = ai_summary
                existing_summary.user_notes = user_notes
                existing_summary.total_minutes = stats["total_minutes"]
                existing_summary.productive_minutes = stats["productive_minutes"]
                existing_summary.activity_count = stats["activity_count"]
                existing_summary.top_category = stats["top_category"]
                existing_summary.updated_at = datetime.utcnow()
                session.commit()
                logger.info(f"Updated summary for {day_start.date()}")
                return existing_summary
            else:
                new_summary = DailySummary(
                    date=day_start.date(),
                    ai_summary=ai_summary,
                    user_notes=user_notes,
                    total_minutes=stats["total_minutes"],
                    productive_minutes=stats["productive_minutes"],
                    activity_count=stats["activity_count"],
                    top_category=stats["top_category"],
                )
                session.add(new_summary)
                session.commit()
                logger.info(f"Created new summary for {day_start.date()}")
                return new_summary

        except Exception as e:
            logger.error(f"Error generating daily summary: {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()

    def _calculate_statistics(self, activities: list) -> dict:
        """Calculate statistics from activities."""
        total_minutes = sum(a.duration_minutes for a in activities)

        # Calculate productive time
        productive_activities = [
            a for a in activities
            if a.category and Theme.is_productive_category(a.category.name)
        ]
        productive_minutes = sum(a.duration_minutes for a in productive_activities)

        # Find top category
        category_time = {}
        for activity in activities:
            if activity.category:
                cat_name = activity.category.name
                category_time[cat_name] = category_time.get(cat_name, 0) + activity.duration_minutes

        top_category = max(category_time.items(), key=lambda x: x[1])[0] if category_time else None

        return {
            "total_minutes": int(total_minutes),
            "total_hours": round(total_minutes / 60, 1),
            "productive_minutes": int(productive_minutes),
            "productive_hours": round(productive_minutes / 60, 1),
            "activity_count": len(activities),
            "top_category": top_category,
            "category_breakdown": category_time,
        }

    def _generate_ai_summary(
        self,
        date: datetime,
        activities: list,
        stats: dict,
        user_notes: Optional[str] = None
    ) -> str:
        """Generate AI summary from activities and stats."""
        # Build activity list for prompt
        activities_text = []
        for i, activity in enumerate(activities, 1):
            cat_name = activity.category.name if activity.category else "未分类"
            cat_emoji = activity.category.icon if activity.category else "📋"
            time_str = activity.start_time.strftime("%H:%M")
            duration = activity.duration_minutes

            activities_text.append(
                f"{i}. {time_str} - {cat_emoji} {cat_name}: {activity.title} "
                f"({duration:.0f}分钟)\n   {activity.summary or '无详情'}"
            )

        activities_list = "\n\n".join(activities_text)

        # Build category breakdown
        category_summary = []
        for cat, minutes in stats["category_breakdown"].items():
            hours = minutes / 60
            percentage = (minutes / stats["total_minutes"] * 100) if stats["total_minutes"] > 0 else 0
            category_summary.append(f"  • {cat}: {hours:.1f}小时 ({percentage:.0f}%)")
        category_text = "\n".join(category_summary)

        # Build user notes section
        user_notes_section = ""
        if user_notes and user_notes.strip():
            user_notes_section = f"\n\n用户今天记录的总结：\n{user_notes}\n"

        # Create prompt
        prompt = f"""请为以下一天的活动生成一份富有洞察力和鼓励性的每日总结。

日期：{date.strftime('%Y年%m月%d日')}

活动列表：
{activities_list}

统计数据：
• 总追踪时间：{stats['total_hours']:.1f}小时
• 生产时间：{stats['productive_hours']:.1f}小时
• 活动数量：{stats['activity_count']}个
• 主要分类：{stats['top_category']}

分类时间分布：
{category_text}
{user_notes_section}

请生成一份每日总结，包括：
1. **今日概览**：用2-3句话总结今天的主要成就和完成的任务
2. **时间分配分析**：分析时间如何分配在不同类别的活动中，指出重点领域
3. **生产力洞察**：提供关于工作模式、专注度和效率的洞察
4. **简短评价**：用温暖、鼓励的语气给出一句话评价，肯定今天的努力或提出改进建议

要求：
- 使用友好、温暖、鼓励的中文语气
- 保持简洁但富有洞察力
- 如果用户提供了笔记，要结合用户的反思进行分析
- 适当使用emoji增加亲和力
- 总结长度控制在4-6段话之内
"""

        try:
            response = self.llm_service.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error calling LLM for summary: {e}", exc_info=True)
            return f"生成总结时出错：{str(e)}"

    def get_summary(self, date: datetime) -> Optional[DailySummary]:
        """
        Get existing summary for a date.

        Args:
            date: Date to get summary for

        Returns:
            DailySummary object or None if not found
        """
        session = get_session_direct()
        try:
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            summary = (
                session.query(DailySummary)
                .filter(DailySummary.date == day_start.date())
                .first()
            )
            return summary
        finally:
            session.close()

    def save_user_notes(self, date: datetime, user_notes: str) -> bool:
        """
        Save or update user notes for a date.

        Args:
            date: Date to save notes for
            user_notes: User notes content

        Returns:
            True if successful, False otherwise
        """
        session = get_session_direct()
        try:
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            summary = (
                session.query(DailySummary)
                .filter(DailySummary.date == day_start.date())
                .first()
            )

            if summary:
                summary.user_notes = user_notes
                summary.updated_at = datetime.utcnow()
            else:
                summary = DailySummary(
                    date=day_start.date(),
                    user_notes=user_notes,
                )
                session.add(summary)

            session.commit()
            logger.info(f"Saved user notes for {day_start.date()}")
            return True
        except Exception as e:
            logger.error(f"Error saving user notes: {e}", exc_info=True)
            session.rollback()
            return False
        finally:
            session.close()
