"""Tests for video validation, optical flow, and feature extraction."""

import sys
from pathlib import Path
import numpy as np
import pytest

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from safetyguard.video.processor import (
    validate_video_file,
    compute_frame_motion_features,
    extract_video_features,
    VideoValidationError,
)


def test_compute_frame_motion_features():
    """Verify optical flow calculation between two artificial frames."""
    prev = np.zeros((180, 320), dtype=np.uint8)
    curr = np.zeros((180, 320), dtype=np.uint8)

    # Add a shifted white square to simulate localized motion
    prev[50:100, 50:100] = 255
    curr[55:105, 55:105] = 255

    features = compute_frame_motion_features(prev, curr)

    assert "motion_mean" in features
    assert "motion_max" in features
    assert "spatial_concentration" in features
    assert "directional_variance" in features
    assert features["motion_mean"] > 0.0
    assert features["motion_max"] > 0.0


def test_validate_test_video():
    """Verify validation on the project's existing test_walk.mp4."""
    video_path = Path(__file__).resolve().parent.parent / "data" / "videos" / "test_walk.mp4"
    if not video_path.is_file():
        pytest.skip("test_walk.mp4 not present in data/videos")

    meta = validate_video_file(video_path)
    assert meta["fps"] > 0
    assert meta["total_frames"] > 0
    assert meta["width"] == 640
    assert meta["height"] == 360
    assert meta["duration"] > 0


def test_extract_video_features():
    """Verify chunked video feature extraction and window generation."""
    video_path = Path(__file__).resolve().parent.parent / "data" / "videos" / "test_walk.mp4"
    if not video_path.is_file():
        pytest.skip("test_walk.mp4 not present in data/videos")

    df, meta = extract_video_features(video_path, sample_fps=4.0, window_seconds=1.0)

    assert not df.empty
    assert "window_start_seconds" in df.columns
    assert "motion_mean" in df.columns
    assert "spatial_concentration" in df.columns
    assert "directional_variance" in df.columns
    assert "thumbnail" in df.columns
    assert len(df) >= 3
