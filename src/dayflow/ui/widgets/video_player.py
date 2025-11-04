"""Video player widget using PyQt6 multimedia."""

import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

logger = logging.getLogger(__name__)


class VideoPlayer(QWidget):
    """Video player widget with playback controls."""

    def __init__(self, video_path: Path):
        """
        Initialize video player.

        Args:
            video_path: Path to video file
        """
        super().__init__()
        self.video_path = video_path
        self.setup_ui()
        self.setup_player()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(300)
        self.video_widget.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_widget)

        # Controls
        controls_layout = QHBoxLayout()

        # Play/Pause button
        self.play_btn = QPushButton("▶ 播放")
        self.play_btn.clicked.connect(self.toggle_play)
        controls_layout.addWidget(self.play_btn)

        # Position slider
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_position)
        controls_layout.addWidget(self.position_slider)

        # Time label
        self.time_label = QLabel("00:00 / 00:00")
        controls_layout.addWidget(self.time_label)

        layout.addLayout(controls_layout)

    def setup_player(self) -> None:
        """Set up media player."""
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        # Connect signals
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.playbackStateChanged.connect(self.state_changed)

        # Load video
        if self.video_path.exists():
            self.player.setSource(QUrl.fromLocalFile(str(self.video_path)))
            logger.debug(f"Loaded video: {self.video_path.name}")
        else:
            logger.warning(f"Video file not found: {self.video_path}")

    def toggle_play(self) -> None:
        """Toggle play/pause."""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def set_position(self, position: int) -> None:
        """Set playback position."""
        self.player.setPosition(position)

    def position_changed(self, position: int) -> None:
        """Handle position change."""
        self.position_slider.setValue(position)
        self._update_time_label(position, self.player.duration())

    def duration_changed(self, duration: int) -> None:
        """Handle duration change."""
        self.position_slider.setRange(0, duration)
        self._update_time_label(self.player.position(), duration)

    def state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        """Handle playback state change."""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸ 暂停")
        else:
            self.play_btn.setText("▶ 播放")

    def _update_time_label(self, position: int, duration: int) -> None:
        """Update time display."""
        pos_time = self._format_time(position)
        dur_time = self._format_time(duration)
        self.time_label.setText(f"{pos_time} / {dur_time}")

    def _format_time(self, ms: int) -> str:
        """Format milliseconds as MM:SS."""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def cleanup(self) -> None:
        """Clean up player resources."""
        self.player.stop()
