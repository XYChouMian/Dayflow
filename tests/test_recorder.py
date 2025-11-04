"""Tests for ScreenRecorder."""

import pytest
from pathlib import Path
from datetime import datetime
from dayflow.core.recorder import ScreenRecorder


def test_get_available_monitors():
    """Test monitor detection."""
    monitors = ScreenRecorder.get_available_monitors()
    assert len(monitors) > 0
    assert "width" in monitors[0]
    assert "height" in monitors[0]


def test_recorder_initialization(tmp_path):
    """Test recorder initialization."""
    recorder = ScreenRecorder(
        output_dir=tmp_path,
        chunk_duration=5,
        fps=1,
    )
    assert recorder.output_dir == tmp_path
    assert recorder.chunk_duration == 5
    assert recorder.fps == 1
    assert not recorder.is_recording
