"""Video processing - merge chunks and create timelapse videos."""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional
import cv2
import ffmpeg
import tempfile

logger = logging.getLogger(__name__)


class VideoProcessor:
    """
    Handles video processing operations:
    - Merging 15-second chunks into longer videos
    - Creating timelapse (sped-up) videos
    - Extracting frames for analysis
    """

    def __init__(self):
        """Initialize video processor."""
        self._check_ffmpeg()

    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info("FFmpeg found and available")
                return True
        except Exception as e:
            logger.warning(f"FFmpeg not found or not working: {e}")
            logger.warning("Video merging and timelapse features will be limited")
        return False

    def merge_chunks(
        self,
        chunk_paths: List[Path],
        output_path: Path,
        delete_chunks: bool = False,
    ) -> bool:
        """
        Merge multiple video chunks into one video.

        Args:
            chunk_paths: List of paths to video chunks (in order)
            output_path: Path for output merged video
            delete_chunks: Whether to delete source chunks after merging

        Returns:
            True if successful
        """
        if not chunk_paths:
            logger.error("No chunks to merge")
            return False

        try:
            # Create a temporary file list for ffmpeg concat
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                temp_list = Path(f.name)
                for chunk_path in chunk_paths:
                    # Escape special characters and write in ffmpeg concat format
                    escaped_path = str(chunk_path).replace("\\", "/")
                    f.write(f"file '{escaped_path}'\n")

            # Use ffmpeg to concatenate videos
            try:
                (
                    ffmpeg.input(str(temp_list), format="concat", safe=0)
                    .output(
                        str(output_path),
                        c="copy",  # Copy codec (no re-encoding)
                        loglevel="error",
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )

                logger.info(
                    f"Merged {len(chunk_paths)} chunks into {output_path.name}"
                )

                # Delete source chunks if requested
                if delete_chunks:
                    for chunk_path in chunk_paths:
                        try:
                            chunk_path.unlink()
                        except Exception as e:
                            logger.warning(f"Failed to delete {chunk_path}: {e}")

                return True

            finally:
                # Clean up temp file
                temp_list.unlink(missing_ok=True)

        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error merging chunks: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"Error merging chunks: {e}", exc_info=True)
            return False

    def create_timelapse(
        self,
        input_path: Path,
        output_path: Path,
        speedup: int = 20,
    ) -> bool:
        """
        Create a timelapse (sped-up) video from input video.

        Args:
            input_path: Input video file
            output_path: Output timelapse video file
            speedup: Speed multiplier (default: 20x)

        Returns:
            True if successful
        """
        if not input_path.exists():
            logger.error(f"Input video not found: {input_path}")
            return False

        try:
            # Use setpts filter to speed up video
            # setpts=PTS/20 means 20x speed
            (
                ffmpeg.input(str(input_path))
                .filter("setpts", f"PTS/{speedup}")
                .output(
                    str(output_path),
                    vcodec="libx264",
                    crf=23,  # Quality (lower = better, 23 is good)
                    preset="medium",
                    loglevel="error",
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            logger.info(f"Created timelapse: {output_path.name} ({speedup}x speed)")
            return True

        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error creating timelapse: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"Error creating timelapse: {e}", exc_info=True)
            return False

    def extract_frames(
        self,
        video_path: Path,
        num_frames: int = 10,
        output_dir: Optional[Path] = None,
    ) -> List[Path]:
        """
        Extract evenly-spaced frames from video for analysis.

        Args:
            video_path: Input video file
            num_frames: Number of frames to extract
            output_dir: Optional output directory (uses temp if None)

        Returns:
            List of paths to extracted frame images
        """
        if not video_path.exists():
            logger.error(f"Video not found: {video_path}")
            return []

        try:
            # Open video
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.error(f"Failed to open video: {video_path}")
                return []

            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames == 0:
                logger.error("Video has no frames")
                return []

            # Calculate frame indices to extract
            frame_indices = [
                int(i * total_frames / num_frames) for i in range(num_frames)
            ]

            # Create output directory
            if output_dir is None:
                output_dir = Path(tempfile.mkdtemp())
            else:
                output_dir.mkdir(parents=True, exist_ok=True)

            extracted_frames = []

            for idx, frame_num in enumerate(frame_indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()

                if ret:
                    frame_path = output_dir / f"frame_{idx:03d}.jpg"
                    cv2.imwrite(str(frame_path), frame)
                    extracted_frames.append(frame_path)

            cap.release()

            logger.info(f"Extracted {len(extracted_frames)} frames from {video_path.name}")
            return extracted_frames

        except Exception as e:
            logger.error(f"Error extracting frames: {e}", exc_info=True)
            return []

    def get_video_info(self, video_path: Path) -> dict:
        """
        Get video metadata.

        Args:
            video_path: Path to video file

        Returns:
            Dict with video information
        """
        try:
            probe = ffmpeg.probe(str(video_path))
            video_info = next(
                (s for s in probe["streams"] if s["codec_type"] == "video"), None
            )

            if video_info:
                return {
                    "width": int(video_info.get("width", 0)),
                    "height": int(video_info.get("height", 0)),
                    "duration": float(probe["format"].get("duration", 0)),
                    "fps": eval(video_info.get("r_frame_rate", "0/1")),
                    "codec": video_info.get("codec_name", "unknown"),
                    "size_mb": float(probe["format"].get("size", 0)) / (1024 * 1024),
                }

            return {}

        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {}

    def trim_video(
        self,
        input_path: Path,
        output_path: Path,
        start_time: float,
        duration: float,
    ) -> bool:
        """
        Trim video to specific time range.

        Args:
            input_path: Input video file
            output_path: Output video file
            start_time: Start time in seconds
            duration: Duration in seconds

        Returns:
            True if successful
        """
        try:
            (
                ffmpeg.input(str(input_path), ss=start_time, t=duration)
                .output(
                    str(output_path),
                    c="copy",
                    loglevel="error",
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            logger.info(f"Trimmed video: {output_path.name}")
            return True

        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error trimming video: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"Error trimming video: {e}", exc_info=True)
            return False
