"""Windows notification system."""

from plyer import notification
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def show_notification(
    title: str,
    message: str,
    timeout: int = 5,
    app_icon: Path = None,
) -> None:
    """
    Show Windows toast notification.

    Args:
        title: Notification title
        message: Notification message
        timeout: Display duration in seconds
        app_icon: Optional path to app icon
    """
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Dayflow",
            timeout=timeout,
            toast=True,
        )
    except Exception as e:
        logger.error(f"Failed to show notification: {e}")


def notify_recording_started() -> None:
    """Notify user that recording has started."""
    show_notification(
        title="Dayflow Recording",
        message="Screen recording started",
        timeout=3,
    )


def notify_recording_paused() -> None:
    """Notify user that recording has been paused."""
    show_notification(
        title="Dayflow Recording",
        message="Screen recording paused",
        timeout=3,
    )


def notify_analysis_complete(activity_count: int) -> None:
    """Notify user that analysis is complete."""
    show_notification(
        title="Dayflow Analysis",
        message=f"Analysis complete: {activity_count} activities detected",
        timeout=5,
    )


def notify_error(error_message: str) -> None:
    """Notify user of an error."""
    show_notification(
        title="Dayflow Error",
        message=error_message,
        timeout=10,
    )
