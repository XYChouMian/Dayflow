"""Analysis manager - schedules and coordinates video analysis."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from dayflow.analysis.llm_service import LLMService, ActivitySegment
from dayflow.core.video_processor import VideoProcessor
from dayflow.core.storage import StorageManager
from dayflow.models.database import get_session_direct
from dayflow.models.timeline_activity import TimelineActivity
from dayflow.models.category import TimelineCategory

logger = logging.getLogger(__name__)


class AnalysisManager:
    """
    Manages scheduled analysis of recorded video chunks.
    Runs every 15 minutes to process new recordings.
    """

    def __init__(
        self,
        llm_service: LLMService,
        storage_manager: StorageManager,
        analysis_interval_minutes: int = 15,
        context_window_minutes: int = 60,
    ):
        """
        Initialize analysis manager.

        Args:
            llm_service: LLM service for analysis
            storage_manager: Storage manager for accessing recordings
            analysis_interval_minutes: How often to run analysis (default: 15)
            context_window_minutes: Context window for better analysis (default: 60)
        """
        self.llm_service = llm_service
        self.storage_manager = storage_manager
        self.analysis_interval = analysis_interval_minutes
        self.context_window = context_window_minutes

        self.video_processor = VideoProcessor()
        self.scheduler = BackgroundScheduler()
        self.is_running = False

        logger.info(f"AnalysisManager initialized (interval: {self.analysis_interval} min)")

    def start(self, run_immediately: bool = False) -> None:
        """
        Start scheduled analysis.

        Args:
            run_immediately: If True, run analysis immediately before starting schedule
        """
        if self.is_running:
            logger.warning("Analysis already running")
            return

        # Add scheduled job
        self.scheduler.add_job(
            self._analysis_job,
            trigger=IntervalTrigger(minutes=self.analysis_interval),
            id="analysis_job",
            name="Video Analysis",
            max_instances=1,  # Prevent overlapping runs
        )

        self.scheduler.start()
        self.is_running = True

        logger.info("Analysis scheduling started")

        # Optionally run immediately
        if run_immediately:
            logger.info("Running immediate analysis...")
            self._analysis_job()

    def stop(self) -> None:
        """Stop scheduled analysis."""
        if not self.is_running:
            return

        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("Analysis scheduling stopped")

    def _analysis_job(self) -> None:
        """Main analysis job - runs on schedule."""
        try:
            logger.info("Starting analysis job...")

            # Define time range to analyze
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=self.analysis_interval)

            # Get recording chunks in this range
            chunks = self.storage_manager.get_chunks_in_range(start_time, end_time)

            if not chunks:
                logger.info("No new chunks to analyze")
                return

            logger.info(f"Found {len(chunks)} chunks to analyze")

            # Merge chunks into single video
            merged_video = self._merge_batch(chunks, start_time, end_time)
            if not merged_video:
                logger.error("Failed to merge chunks")
                return

            # Get context from recent activities
            context = self._get_recent_context(start_time)

            # Analyze video
            activities = self.llm_service.analyze_video(merged_video, context)

            if not activities:
                logger.warning("No activities detected")
                return

            logger.info(f"Detected {len(activities)} activities")

            # Process each activity
            for activity in activities:
                self._process_activity(activity, merged_video)

            # Cleanup merged video
            try:
                merged_video.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete merged video: {e}")

            logger.info("Analysis job completed successfully")

        except Exception as e:
            logger.error(f"Error in analysis job: {e}", exc_info=True)

    def _merge_batch(
        self, chunks: list, start_time: datetime, end_time: datetime
    ) -> Optional[Path]:
        """
        Merge video chunks into single file for analysis.

        Args:
            chunks: List of RecordingChunk objects
            start_time: Batch start time
            end_time: Batch end time

        Returns:
            Path to merged video or None
        """
        try:
            chunk_paths = [Path(chunk.file_path) for chunk in chunks]

            # Filter existing files
            existing_paths = [p for p in chunk_paths if p.exists()]
            if not existing_paths:
                logger.error("No chunk files exist")
                return None

            # Create output path
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            output_path = (
                self.storage_manager.base_dir / "temp" / f"batch_{timestamp}.mp4"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Merge videos
            success = self.video_processor.merge_chunks(
                existing_paths, output_path, delete_chunks=False
            )

            if success:
                return output_path
            return None

        except Exception as e:
            logger.error(f"Error merging batch: {e}", exc_info=True)
            return None

    def _get_recent_context(self, before_time: datetime) -> Optional[str]:
        """
        Get context from recent activities for better analysis.

        Args:
            before_time: Get activities before this time

        Returns:
            Context string or None
        """
        try:
            session = get_session_direct()
            try:
                # Get last few activities
                recent_activities = (
                    session.query(TimelineActivity)
                    .filter(TimelineActivity.end_time <= before_time)
                    .order_by(TimelineActivity.end_time.desc())
                    .limit(3)
                    .all()
                )

                if not recent_activities:
                    return None

                context_parts = []
                for activity in reversed(recent_activities):
                    context_parts.append(
                        f"- {activity.title}: {activity.summary[:100]}"
                    )

                return "Recent activities:\n" + "\n".join(context_parts)

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return None

    def _process_activity(
        self, activity: ActivitySegment, source_video: Path
    ) -> None:
        """
        Process detected activity: create timelapse and save to database.

        Args:
            activity: Detected activity segment
            source_video: Source video file
        """
        try:
            # Generate timelapse video
            timelapse_dir = self.storage_manager.get_timelapse_dir(
                activity.start_time
            )
            timelapse_name = (
                f"activity_{activity.start_time.strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            timelapse_path = timelapse_dir / timelapse_name

            # Calculate trim times (if needed)
            # For now, use entire source video
            success = self.video_processor.create_timelapse(
                source_video, timelapse_path, speedup=20
            )

            if not success:
                logger.warning(f"Failed to create timelapse for {activity.title}")
                timelapse_path = None

            # Get or create category
            category_id = self._get_category_id(activity.category)

            # Save to database
            session = get_session_direct()
            try:
                db_activity = TimelineActivity(
                    start_time=activity.start_time,
                    end_time=activity.end_time,
                    title=activity.title,
                    summary=activity.summary,
                    category_id=category_id,
                    timelapse_path=str(timelapse_path) if timelapse_path else None,
                )
                session.add(db_activity)
                session.commit()

                logger.info(f"Saved activity: {activity.title}")

            except Exception as e:
                session.rollback()
                logger.error(f"Error saving activity to database: {e}")
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error processing activity: {e}", exc_info=True)

    def _get_category_id(self, category_name: Optional[str]) -> Optional[int]:
        """
        Get or create category ID.

        Args:
            category_name: Category name (Chinese or English)

        Returns:
            Category ID or None
        """
        if not category_name:
            return None

        # Category name mapping: Chinese <-> English
        category_mapping = {
            # Chinese to English
            "工作": "Work",
            "会议": "Meeting",
            "休息": "Break",
            "效率": "Productivity",
            "学习": "Learning",
            "娱乐": "Entertainment",
            # English to Chinese
            "Work": "工作",
            "Meeting": "会议",
            "Break": "休息",
            "Productivity": "效率",
            "Learning": "学习",
            "Entertainment": "娱乐",
        }

        try:
            session = get_session_direct()
            try:
                # Try to find existing category with original name
                category = (
                    session.query(TimelineCategory)
                    .filter(TimelineCategory.name == category_name)
                    .first()
                )

                if category:
                    return category.id

                # Create default categories if none exist
                count = session.query(TimelineCategory).count()
                if count == 0:
                    self._create_default_categories(session)

                # Try again with original name
                category = (
                    session.query(TimelineCategory)
                    .filter(TimelineCategory.name == category_name)
                    .first()
                )

                if category:
                    return category.id

                # Try with translated name (fallback for legacy data)
                translated_name = category_mapping.get(category_name)
                if translated_name:
                    category = (
                        session.query(TimelineCategory)
                        .filter(TimelineCategory.name == translated_name)
                        .first()
                    )
                    if category:
                        return category.id

                return None

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error getting category: {e}")
            return None

    def _create_default_categories(self, session) -> None:
        """Create default categories in database."""
        try:
            defaults = TimelineCategory.get_default_categories()

            for cat_data in defaults:
                category = TimelineCategory(
                    name=cat_data["name"],
                    color=cat_data["color"],
                    icon=cat_data["icon"],
                )
                session.add(category)

            session.commit()
            logger.info("Created default categories")

        except Exception as e:
            session.rollback()
            logger.error(f"Error creating default categories: {e}")

    def analyze_date(self, date: datetime) -> int:
        """
        Manually trigger analysis for a specific date.

        Args:
            date: Date to analyze

        Returns:
            Number of activities created
        """
        try:
            logger.info(f"Manual analysis for date: {date.strftime('%Y-%m-%d')}")

            # Get all chunks for this date
            start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)

            chunks = self.storage_manager.get_chunks_in_range(start_time, end_time)

            if not chunks:
                logger.info("No chunks found for this date")
                return 0

            # Process in batches of 15 minutes
            activities_created = 0
            current_time = start_time

            while current_time < end_time:
                batch_end = current_time + timedelta(minutes=self.analysis_interval)
                batch_chunks = [
                    c
                    for c in chunks
                    if current_time <= c.start_time < batch_end
                ]

                if batch_chunks:
                    merged = self._merge_batch(batch_chunks, current_time, batch_end)
                    if merged:
                        context = self._get_recent_context(current_time)
                        activities = self.llm_service.analyze_video(merged, context)

                        for activity in activities:
                            self._process_activity(activity, merged)
                            activities_created += 1

                        merged.unlink(missing_ok=True)

                current_time = batch_end

            logger.info(f"Created {activities_created} activities for date")
            return activities_created

        except Exception as e:
            logger.error(f"Error in manual analysis: {e}", exc_info=True)
            return 0
