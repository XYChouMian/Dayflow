"""Storage management for video files and database operations."""

import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from sqlalchemy.orm import Session

from dayflow.models.database import get_session_direct
from dayflow.models.recording_chunk import RecordingChunk
from dayflow.models.timeline_activity import TimelineActivity

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manages video file storage and database records.
    Handles file organization, cleanup, and disk space management.
    """

    def __init__(self, base_dir: Path, retention_days: int = 3):
        """
        Initialize storage manager.

        Args:
            base_dir: Base directory for all recordings
            retention_days: Days to keep recordings before cleanup (default: 3)
        """
        self.base_dir = Path(base_dir)
        self.retention_days = retention_days

        # Create directory structure
        self.recordings_dir = self.base_dir / "recordings"
        self.timelapses_dir = self.base_dir / "timelapses"
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.timelapses_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"StorageManager initialized: {self.base_dir}")

    def get_chunks_dir(self, date: datetime) -> Path:
        """
        Get directory for recording chunks on a specific date.

        Args:
            date: Date for the chunks

        Returns:
            Path to chunks directory
        """
        date_str = date.strftime("%Y-%m-%d")
        chunks_dir = self.recordings_dir / date_str / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        return chunks_dir

    def get_timelapse_dir(self, date: datetime) -> Path:
        """
        Get directory for timelapse videos on a specific date.

        Args:
            date: Date for the timelapses

        Returns:
            Path to timelapse directory
        """
        date_str = date.strftime("%Y-%m-%d")
        timelapse_dir = self.timelapses_dir / date_str
        timelapse_dir.mkdir(parents=True, exist_ok=True)
        return timelapse_dir

    def save_chunk_record(
        self,
        file_path: Path,
        start_time: datetime,
        end_time: datetime,
        display_id: int = 1,
    ) -> RecordingChunk:
        """
        Save recording chunk metadata to database.

        Args:
            file_path: Path to video file
            start_time: Chunk start time
            end_time: Chunk end time
            display_id: Monitor ID

        Returns:
            Created RecordingChunk instance
        """
        session = get_session_direct()
        try:
            chunk = RecordingChunk(
                start_time=start_time,
                end_time=end_time,
                file_path=str(file_path),
                display_id=display_id,
                file_size=file_path.stat().st_size if file_path.exists() else 0,
            )
            session.add(chunk)
            session.commit()
            logger.debug(f"Saved chunk record: {chunk.id}")
            return chunk
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving chunk record: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def get_chunks_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        display_id: Optional[int] = None,
    ) -> List[RecordingChunk]:
        """
        Get recording chunks within a time range.

        Args:
            start_time: Start of range
            end_time: End of range
            display_id: Optional filter by display

        Returns:
            List of RecordingChunk instances
        """
        session = get_session_direct()
        try:
            query = session.query(RecordingChunk).filter(
                RecordingChunk.start_time >= start_time,
                RecordingChunk.end_time <= end_time,
            )

            if display_id is not None:
                query = query.filter(RecordingChunk.display_id == display_id)

            chunks = query.order_by(RecordingChunk.start_time).all()
            return chunks
        finally:
            session.close()

    def cleanup_old_recordings(self) -> dict:
        """
        Delete recordings older than retention period.

        Returns:
            Dict with cleanup statistics
        """
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_files = 0
        deleted_records = 0
        freed_bytes = 0

        logger.info(f"Starting cleanup for recordings before {cutoff_date}")

        session = get_session_direct()
        try:
            # Get old chunks
            old_chunks = (
                session.query(RecordingChunk)
                .filter(RecordingChunk.start_time < cutoff_date)
                .all()
            )

            for chunk in old_chunks:
                try:
                    # Delete file
                    file_path = Path(chunk.file_path)
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        freed_bytes += file_size
                        deleted_files += 1

                    # Delete database record
                    session.delete(chunk)
                    deleted_records += 1

                except Exception as e:
                    logger.error(f"Error deleting chunk {chunk.id}: {e}")

            session.commit()

            # Clean up empty directories
            self._cleanup_empty_dirs()

            stats = {
                "deleted_files": deleted_files,
                "deleted_records": deleted_records,
                "freed_mb": freed_bytes / (1024 * 1024),
                "cutoff_date": cutoff_date,
            }

            logger.info(
                f"Cleanup complete: {deleted_files} files, "
                f"{stats['freed_mb']:.1f} MB freed"
            )

            return stats

        except Exception as e:
            session.rollback()
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def _cleanup_empty_dirs(self) -> None:
        """Remove empty date directories."""
        try:
            for date_dir in self.recordings_dir.iterdir():
                if date_dir.is_dir():
                    # Check if directory is empty or only has empty subdirs
                    if not any(date_dir.rglob("*")):
                        shutil.rmtree(date_dir)
                        logger.debug(f"Removed empty directory: {date_dir}")
        except Exception as e:
            logger.error(f"Error cleaning empty directories: {e}")

    def get_storage_stats(self) -> dict:
        """
        Get storage usage statistics.

        Returns:
            Dict with storage information
        """
        try:
            # Calculate total size of recordings
            recordings_size = sum(
                f.stat().st_size
                for f in self.recordings_dir.rglob("*")
                if f.is_file()
            )

            # Calculate total size of timelapses
            timelapses_size = sum(
                f.stat().st_size
                for f in self.timelapses_dir.rglob("*")
                if f.is_file()
            )

            # Count files
            session = get_session_direct()
            try:
                chunk_count = session.query(RecordingChunk).count()
                activity_count = session.query(TimelineActivity).count()
            finally:
                session.close()

            return {
                "recordings_mb": recordings_size / (1024 * 1024),
                "timelapses_mb": timelapses_size / (1024 * 1024),
                "total_mb": (recordings_size + timelapses_size) / (1024 * 1024),
                "chunk_count": chunk_count,
                "activity_count": activity_count,
            }

        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}

    def export_date_data(self, date: datetime, export_path: Path) -> bool:
        """
        Export all data for a specific date.

        Args:
            date: Date to export
            export_path: Path to export archive

        Returns:
            True if successful
        """
        try:
            date_str = date.strftime("%Y-%m-%d")
            temp_dir = export_path.parent / f"dayflow_export_{date_str}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Copy recordings
            recordings_src = self.recordings_dir / date_str
            if recordings_src.exists():
                shutil.copytree(
                    recordings_src,
                    temp_dir / "recordings",
                    dirs_exist_ok=True,
                )

            # Copy timelapses
            timelapses_src = self.timelapses_dir / date_str
            if timelapses_src.exists():
                shutil.copytree(
                    timelapses_src,
                    temp_dir / "timelapses",
                    dirs_exist_ok=True,
                )

            # Create archive
            shutil.make_archive(
                str(export_path.with_suffix("")),
                "zip",
                temp_dir,
            )

            # Cleanup temp directory
            shutil.rmtree(temp_dir)

            logger.info(f"Exported data for {date_str} to {export_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting data: {e}", exc_info=True)
            return False

    def get_date_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Get the date range of available recordings.

        Returns:
            Tuple of (earliest_date, latest_date)
        """
        session = get_session_direct()
        try:
            from sqlalchemy import func

            result = session.query(
                func.min(RecordingChunk.start_time),
                func.max(RecordingChunk.start_time),
            ).first()

            return result if result else (None, None)
        finally:
            session.close()
