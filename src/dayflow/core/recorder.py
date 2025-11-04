"""Screen recorder using mss and OpenCV for 0.2 FPS capture (1 frame per 5 seconds)."""

import logging
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable
import mss
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ScreenRecorder:
    """
    Screen recorder that captures at 0.2 FPS (1 frame per 5 seconds) and creates 15-second video chunks.
    """

    def __init__(
        self,
        output_dir: Path,
        chunk_duration: int = 15,
        fps: float = 0.2,
        display_id: int = 1,
        on_chunk_complete: Optional[Callable[[Path, datetime, datetime], None]] = None,
    ):
        """
        Initialize screen recorder.

        Args:
            output_dir: Directory to save video chunks
            chunk_duration: Duration of each chunk in seconds (default: 15)
            fps: Frames per second to capture (default: 0.2, i.e., 1 frame per 5 seconds)
            display_id: Monitor ID to record (1 for primary, 2+ for secondary)
            on_chunk_complete: Callback when chunk is saved (path, start_time, end_time)
        """
        self.output_dir = Path(output_dir)
        self.chunk_duration = chunk_duration
        self.fps = fps
        self.display_id = display_id
        self.on_chunk_complete = on_chunk_complete

        self.is_recording = False
        self.is_paused = False
        self.recording_thread: Optional[threading.Thread] = None

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # MSS will be created in the recording thread (thread-safe)
        self.sct: Optional[mss.mss] = None
        self.monitor: Optional[dict] = None

        # Get monitor info temporarily
        with mss.mss() as sct:
            monitors = sct.monitors
            if display_id >= len(monitors):
                logger.warning(
                    f"Display {display_id} not found, using primary monitor"
                )
                self.monitor = monitors[1]  # 0 is all monitors, 1 is primary
            else:
                self.monitor = monitors[display_id]

        logger.info(
            f"ScreenRecorder initialized: {self.monitor['width']}x{self.monitor['height']}"
        )

    def start(self) -> None:
        """Start recording in a background thread."""
        if self.is_recording:
            logger.warning("Recording already in progress")
            return

        self.is_recording = True
        self.is_paused = False
        self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.recording_thread.start()
        logger.info("Screen recording started")

    def stop(self) -> None:
        """Stop recording."""
        if not self.is_recording:
            return

        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join(timeout=5.0)
        logger.info("Screen recording stopped")

    def pause(self) -> None:
        """Pause recording (system lock/sleep)."""
        self.is_paused = True
        logger.info("Screen recording paused")

    def resume(self) -> None:
        """Resume recording after pause."""
        self.is_paused = False
        logger.info("Screen recording resumed")

    def _recording_loop(self) -> None:
        """Main recording loop - captures frames and creates chunks."""
        # Create mss object in this thread (thread-safe)
        self.sct = mss.mss()

        try:
            frames_buffer = []
            chunk_start_time = datetime.now()
            frame_interval = 1.0 / self.fps

            while self.is_recording:
                try:
                    if self.is_paused:
                        time.sleep(1.0)
                        continue

                    frame_start = time.time()

                    # Capture frame
                    frame = self._capture_frame()
                    if frame is not None:
                        frames_buffer.append(frame)

                        # Check if chunk duration reached
                        elapsed = (datetime.now() - chunk_start_time).total_seconds()
                        if elapsed >= self.chunk_duration:
                            # Save chunk
                            chunk_end_time = datetime.now()
                            self._save_chunk(frames_buffer, chunk_start_time, chunk_end_time)

                            # Reset for next chunk
                            frames_buffer = []
                            chunk_start_time = datetime.now()

                    # Sleep to maintain FPS
                    frame_duration = time.time() - frame_start
                    sleep_time = max(0, frame_interval - frame_duration)
                    time.sleep(sleep_time)

                except Exception as e:
                    logger.error(f"Error in recording loop: {e}", exc_info=True)
                    time.sleep(1.0)

            # Save remaining frames if any
            if frames_buffer:
                chunk_end_time = datetime.now()
                self._save_chunk(frames_buffer, chunk_start_time, chunk_end_time)

        finally:
            # Clean up mss object
            if self.sct:
                self.sct.close()
                self.sct = None

    def _capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from the screen.

        Returns:
            Numpy array representing the frame (BGR format)
        """
        try:
            # Capture screenshot
            screenshot = self.sct.grab(self.monitor)

            # Convert to numpy array
            frame = np.array(screenshot)

            # Convert BGRA to BGR (remove alpha channel)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            return frame

        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None

    def _save_chunk(
        self,
        frames: list[np.ndarray],
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        """
        Save frames as a video chunk.

        Args:
            frames: List of frame arrays
            start_time: Chunk start timestamp
            end_time: Chunk end timestamp
        """
        if not frames:
            logger.warning("No frames to save")
            return

        try:
            # Create filename with timestamp
            timestamp_str = start_time.strftime("%Y%m%d_%H%M%S")
            filename = f"chunk_{timestamp_str}.mp4"
            output_path = self.output_dir / filename

            # Get frame dimensions
            height, width = frames[0].shape[:2]

            # Create video writer (H.264 codec)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # or 'avc1' for H.264
            writer = cv2.VideoWriter(
                str(output_path),
                fourcc,
                self.fps,
                (width, height),
            )

            if not writer.isOpened():
                logger.error("Failed to open video writer")
                return

            # Write frames
            for frame in frames:
                writer.write(frame)

            writer.release()

            file_size = output_path.stat().st_size
            logger.info(
                f"Saved chunk: {filename} "
                f"({len(frames)} frames, {file_size / 1024:.1f} KB)"
            )

            # Callback notification
            if self.on_chunk_complete:
                self.on_chunk_complete(output_path, start_time, end_time)

        except Exception as e:
            logger.error(f"Error saving chunk: {e}", exc_info=True)

    def get_monitor_info(self) -> dict:
        """Get current monitor information."""
        return {
            "display_id": self.display_id,
            "width": self.monitor["width"],
            "height": self.monitor["height"],
            "top": self.monitor["top"],
            "left": self.monitor["left"],
        }

    @staticmethod
    def get_available_monitors() -> list[dict]:
        """Get list of available monitors."""
        with mss.mss() as sct:
            monitors = []
            for i, monitor in enumerate(sct.monitors[1:], start=1):  # Skip 0 (all monitors)
                monitors.append({
                    "id": i,
                    "width": monitor["width"],
                    "height": monitor["height"],
                    "top": monitor["top"],
                    "left": monitor["left"],
                })
            return monitors

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 'sct') and self.sct:
            try:
                self.sct.close()
            except Exception:
                pass  # Ignore errors during cleanup
