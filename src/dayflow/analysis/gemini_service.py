"""Google Gemini AI service implementation."""

import logging
import json
import time
from typing import List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import google.generativeai as genai

from dayflow.analysis.llm_service import LLMService, ActivitySegment

logger = logging.getLogger(__name__)


class GeminiService(LLMService):
    """
    Google Gemini AI service for video and frame analysis.
    Supports direct video upload for efficient analysis.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize Gemini service.

        Args:
            api_key: Google AI API key
            model_name: Gemini model to use (default: gemini-2.5-flash)
                       Available models: gemini-2.5-flash, gemini-2.5-pro,
                                        gemini-2.0-flash-lite
        """
        super().__init__(api_key)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
        logger.info(f"Initialized Gemini service with model: {model_name}")

    def analyze_video(
        self,
        video_path: Path,
        context: Optional[str] = None,
    ) -> List[ActivitySegment]:
        """
        Analyze video using Gemini's native video understanding.

        Args:
            video_path: Path to video file
            context: Optional context from previous activities

        Returns:
            List of ActivitySegment objects
        """
        if not video_path.exists():
            logger.error(f"Video file not found: {video_path}")
            return []

        try:
            logger.info(f"Uploading video to Gemini: {video_path.name}")

            # Upload video file
            video_file = genai.upload_file(str(video_path))

            # Wait for processing
            while video_file.state.name == "PROCESSING":
                logger.debug("Waiting for video processing...")
                time.sleep(2)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                logger.error("Video processing failed")
                return []

            # Build prompt
            prompt = self.get_analysis_prompt(is_video=True)
            if context:
                prompt = f"Previous context: {context}\n\n{prompt}"

            # Generate analysis
            logger.info("Analyzing video with Gemini...")
            response = self.model.generate_content([prompt, video_file])

            # Parse response
            activities = self._parse_video_response(response.text, video_path)

            # Clean up uploaded file
            try:
                genai.delete_file(video_file.name)
            except Exception as e:
                logger.warning(f"Failed to delete uploaded file: {e}")

            logger.info(f"Detected {len(activities)} activities from video")
            return activities

        except Exception as e:
            logger.error(f"Error analyzing video with Gemini: {e}", exc_info=True)
            return []

    def analyze_frames(
        self,
        frame_paths: List[Path],
        timestamps: List[datetime],
        context: Optional[str] = None,
    ) -> List[ActivitySegment]:
        """
        Analyze individual frames using Gemini vision.

        Args:
            frame_paths: List of paths to frame images
            timestamps: Corresponding timestamps for each frame
            context: Optional context from previous activities

        Returns:
            List of ActivitySegment objects
        """
        if not frame_paths or not timestamps:
            logger.error("No frames or timestamps provided")
            return []

        try:
            logger.info(f"Uploading {len(frame_paths)} frames to Gemini...")

            # Upload all frames
            uploaded_files = []
            for frame_path in frame_paths:
                if frame_path.exists():
                    uploaded_file = genai.upload_file(str(frame_path))
                    uploaded_files.append(uploaded_file)

            if not uploaded_files:
                logger.error("No frames could be uploaded")
                return []

            # Build prompt
            prompt = self.get_analysis_prompt(is_video=False)
            if context:
                prompt = f"Previous context: {context}\n\n{prompt}"

            # Add timestamp information
            time_info = "\n\nFrame timestamps:\n"
            for i, ts in enumerate(timestamps[: len(uploaded_files)]):
                time_info += f"Frame {i}: {ts.strftime('%H:%M:%S')}\n"
            prompt += time_info

            # Generate analysis
            content_parts = [prompt] + uploaded_files
            response = self.model.generate_content(content_parts)

            # Parse response
            activities = self._parse_frames_response(
                response.text, timestamps, len(uploaded_files)
            )

            # Clean up uploaded files
            for uploaded_file in uploaded_files:
                try:
                    genai.delete_file(uploaded_file.name)
                except Exception as e:
                    logger.warning(f"Failed to delete uploaded file: {e}")

            logger.info(f"Detected {len(activities)} activities from frames")
            return activities

        except Exception as e:
            logger.error(f"Error analyzing frames with Gemini: {e}", exc_info=True)
            return []

    def _parse_video_response(
        self, response_text: str, video_path: Path
    ) -> List[ActivitySegment]:
        """
        Parse Gemini's response for video analysis.

        Args:
            response_text: Raw response text from Gemini
            video_path: Path to analyzed video

        Returns:
            List of ActivitySegment objects
        """
        try:
            # Extract JSON from response
            json_start = response_text.find("[")
            json_end = response_text.rfind("]") + 1
            if json_start == -1 or json_end == 0:
                logger.error("No JSON array found in response")
                return []

            json_str = response_text[json_start:json_end]
            activities_data = json.loads(json_str)

            # Get video duration to calculate absolute times
            from dayflow.core.video_processor import VideoProcessor

            processor = VideoProcessor()
            video_info = processor.get_video_info(video_path)
            duration = video_info.get("duration", 900)  # Default 15 min

            # Create base timestamp (video start time based on filename)
            # Assuming filename format: chunk_YYYYMMDD_HHMMSS.mp4
            base_time = datetime.now()  # Fallback to now
            try:
                filename = video_path.stem
                if "chunk_" in filename:
                    time_str = filename.split("_", 1)[1]
                    base_time = datetime.strptime(time_str, "%Y%m%d_%H%M%S")
            except Exception:
                pass

            activities = []
            for activity_data in activities_data:
                try:
                    start_min = float(activity_data.get("start_minutes", 0))
                    end_min = float(activity_data.get("end_minutes", duration / 60))

                    start_time = base_time + timedelta(minutes=start_min)
                    end_time = base_time + timedelta(minutes=end_min)

                    activity = ActivitySegment(
                        start_time=start_time,
                        end_time=end_time,
                        title=activity_data.get("title", "Untitled Activity"),
                        summary=activity_data.get("summary", ""),
                        category=self.parse_category(
                            activity_data.get("category", "Other")
                        ),
                    )
                    activities.append(activity)
                except Exception as e:
                    logger.warning(f"Failed to parse activity: {e}")

            return activities

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            return []

    def _parse_frames_response(
        self, response_text: str, timestamps: List[datetime], num_frames: int
    ) -> List[ActivitySegment]:
        """
        Parse Gemini's response for frame analysis.

        Args:
            response_text: Raw response text from Gemini
            timestamps: List of frame timestamps
            num_frames: Number of frames analyzed

        Returns:
            List of ActivitySegment objects
        """
        try:
            # Extract JSON from response
            json_start = response_text.find("[")
            json_end = response_text.rfind("]") + 1
            if json_start == -1 or json_end == 0:
                logger.error("No JSON array found in response")
                return []

            json_str = response_text[json_start:json_end]
            activities_data = json.loads(json_str)

            activities = []
            for activity_data in activities_data:
                try:
                    start_idx = int(activity_data.get("start_index", 0))
                    end_idx = int(activity_data.get("end_index", num_frames - 1))

                    # Clamp indices
                    start_idx = max(0, min(start_idx, len(timestamps) - 1))
                    end_idx = max(start_idx, min(end_idx, len(timestamps) - 1))

                    start_time = timestamps[start_idx]
                    end_time = timestamps[end_idx]

                    activity = ActivitySegment(
                        start_time=start_time,
                        end_time=end_time,
                        title=activity_data.get("title", "Untitled Activity"),
                        summary=activity_data.get("summary", ""),
                        category=self.parse_category(
                            activity_data.get("category", "Other")
                        ),
                    )
                    activities.append(activity)
                except Exception as e:
                    logger.warning(f"Failed to parse activity: {e}")

            return activities

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            return []

    def test_connection(self) -> bool:
        """
        Test if Gemini service is available.

        Returns:
            True if service is available
        """
        try:
            # Try a simple generation
            response = self.model.generate_content("Hello")
            return bool(response.text)
        except Exception as e:
            logger.error(f"Gemini connection test failed: {e}")
            return False
