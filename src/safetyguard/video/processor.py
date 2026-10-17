"""Video processing pipeline: metadata, chunked frame reading, and spatio-temporal motion analysis."""

import base64
import logging
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Generator
import cv2
import numpy as np
import pandas as pd

from safetyguard.config import (
    DEFAULT_FRAME_SAMPLE_FPS,
    WINDOW_SECONDS,
    SUPPORTED_VIDEO_EXTENSIONS,
    MAX_VIDEO_DURATION_SECONDS,
)

logger = logging.getLogger(__name__)


class VideoProcessingError(Exception):
    """Raised when video reading or processing fails."""
    pass


class VideoValidationError(Exception):
    """Raised when video file format or duration is invalid."""
    pass


def validate_video_file(file_path: Path) -> Dict[str, Any]:
    """
    Validate that file exists, has a supported extension, and can be read by OpenCV.
    
    Returns basic metadata.
    """
    if not file_path.is_file():
        raise VideoValidationError(f"Video file does not exist: {file_path}")

    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_VIDEO_EXTENSIONS:
        raise VideoValidationError(
            f"Unsupported video extension '{ext}'. Supported: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}"
        )

    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        cap.release()
        raise VideoValidationError(f"Could not open video file with OpenCV: {file_path.name}")

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        duration = (total_frames / fps) if fps > 0 and total_frames > 0 else 0.0

        if duration > MAX_VIDEO_DURATION_SECONDS:
            raise VideoValidationError(
                f"Video duration ({duration:.1f}s) exceeds maximum allowed limit ({MAX_VIDEO_DURATION_SECONDS}s)."
            )

        return {
            "fps": round(fps, 2),
            "total_frames": total_frames,
            "width": width,
            "height": height,
            "duration": round(duration, 2),
            "filename": file_path.name,
            "file_size_bytes": file_path.stat().st_size,
        }
    finally:
        cap.release()


def compute_frame_motion_features(
    prev_gray: np.ndarray,
    curr_gray: np.ndarray
) -> Dict[str, float]:
    """
    Compute dense optical flow between two grayscale frames and extract
    motion magnitude, spatial concentration, and directional entropy.
    """
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray,
        curr_gray,
        None,
        pyr_scale=0.5,
        levels=3,
        winsize=15,
        iterations=3,
        poly_n=5,
        poly_sigma=1.2,
        flags=0,
    )

    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1], angleInDegrees=True)

    mag_mean = float(np.mean(magnitude))
    mag_std = float(np.std(magnitude))
    mag_max = float(np.max(magnitude))
    mag_p90 = float(np.percentile(magnitude, 90))

    # Spatial concentration: ratio of top 10% magnitude sum to total magnitude sum
    # High ratio means motion is concentrated in a specific region (e.g., limb movement / struggle)
    # Low ratio means uniform motion across the entire screen (e.g. camera pan)
    sorted_mag = np.sort(magnitude.ravel())
    top_10_percent = int(len(sorted_mag) * 0.1)
    if top_10_percent > 0:
        top_sum = np.sum(sorted_mag[-top_10_percent:])
        total_sum = np.sum(sorted_mag) + 1e-6
        spatial_concentration = float(top_sum / total_sum)
    else:
        spatial_concentration = 0.0

    # Directional variance (in radians)
    angles_rad = np.deg2rad(angle[magnitude > (mag_mean + 0.1)])
    if len(angles_rad) > 10:
        sin_mean = np.mean(np.sin(angles_rad))
        cos_mean = np.mean(np.cos(angles_rad))
        R = math.sqrt(sin_mean**2 + cos_mean**2)
        circular_variance = float(1.0 - R)  # 0: perfectly aligned direction, 1: chaotic directions
    else:
        circular_variance = 0.0

    return {
        "motion_mean": mag_mean,
        "motion_std": mag_std,
        "motion_max": mag_max,
        "motion_p90": mag_p90,
        "spatial_concentration": spatial_concentration,
        "directional_variance": circular_variance,
    }


def detect_scene_cut(
    prev_gray: np.ndarray,
    curr_gray: np.ndarray,
    hist_threshold: float = 0.58,
    diff_threshold: float = 38.0,
) -> Tuple[bool, float, float]:
    """
    Detect whether transition between two frames is a camera/scene cut.
    Uses histogram correlation and mean absolute difference.
    """
    diff = cv2.absdiff(prev_gray, curr_gray)
    mean_diff = float(np.mean(diff))

    hist1 = cv2.calcHist([prev_gray], [0], None, [32], [0, 256])
    hist2 = cv2.calcHist([curr_gray], [0], None, [32], [0, 256])
    cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)
    hist_sim = float(cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL))

    is_cut = (hist_sim < hist_threshold and mean_diff > diff_threshold) or (mean_diff > 65.0)
    return is_cut, hist_sim, mean_diff


def extract_video_features(
    video_path: Path,
    sample_fps: float = DEFAULT_FRAME_SAMPLE_FPS,
    window_seconds: float = WINDOW_SECONDS,
    progress_callback: Optional[Any] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Process video in chunked fashion to compute window-level visual and motion features.
    Extracts keyframe thumbnails for flagged intervals.
    
    Returns:
        Tuple of (features_dataframe, video_metadata)
    """
    metadata = validate_video_file(video_path)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise VideoProcessingError(f"Failed to open video: {video_path}")

    fps = metadata["fps"] or 25.0
    frame_step = max(1, int(round(fps / sample_fps))) if fps > 0 else 5

    frame_records: List[Dict[str, Any]] = []
    prev_gray: Optional[np.ndarray] = None
    prev_mean_motion: float = 0.0
    frame_idx = 0
    sampled_count = 0
    total_frames = metadata["total_frames"]

    # Thumbnail storage for key intervals
    thumbnails: Dict[int, str] = {}

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_step == 0:
                sampled_count += 1
                timestamp = frame_idx / fps if fps > 0 else (sampled_count / sample_fps)

                # Resize to standard analysis resolution (320x180) for efficiency and consistency
                small = cv2.resize(frame, (320, 180))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

                if prev_gray is not None:
                    is_cut, hist_sim, mean_diff = detect_scene_cut(prev_gray, gray)
                    if is_cut:
                        # Scene cut: suppress cross-shot optical flow artifact
                        features = {
                            "motion_mean": 0.0,
                            "motion_std": 0.0,
                            "motion_max": 0.0,
                            "motion_p90": 0.0,
                            "spatial_concentration": 0.0,
                            "directional_variance": 0.0,
                            "motion_jerk": 0.0,
                            "is_cut": 1.0,
                        }
                        prev_mean_motion = None
                    else:
                        features = compute_frame_motion_features(prev_gray, gray)
                        if prev_mean_motion is None:
                            motion_jerk = 0.0
                        else:
                            motion_jerk = abs(features["motion_mean"] - prev_mean_motion)
                        prev_mean_motion = features["motion_mean"]
                        features["motion_jerk"] = motion_jerk
                        features["is_cut"] = 0.0

                    features["timestamp"] = timestamp
                    features["frame_idx"] = frame_idx
                    frame_records.append(features)

                    # Store representative thumbnail every second
                    second_bucket = int(timestamp)
                    if second_bucket not in thumbnails:
                        thumb = cv2.resize(frame, (160, 90))
                        _, buffer = cv2.imencode(".jpg", thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
                        b64_str = base64.b64encode(buffer).decode("utf-8")
                        thumbnails[second_bucket] = f"data:image/jpeg;base64,{b64_str}"

                prev_gray = gray

                if progress_callback and total_frames > 0 and sampled_count % 10 == 0:
                    pct = min(95.0, (frame_idx / total_frames) * 100.0)
                    progress_callback(pct, f"Analyzing video frames ({frame_idx}/{total_frames})")

            frame_idx += 1

    finally:
        cap.release()

    if not frame_records:
        # Return empty window dataframe with proper schema
        columns = [
            "window_start_seconds", "window_end_seconds", "motion_mean", "motion_std",
            "motion_max", "motion_min", "motion_p90", "motion_jerk_mean", "spatial_concentration",
            "directional_variance", "cut_count", "thumbnail"
        ]
        return pd.DataFrame(columns=columns), metadata

    raw_df = pd.DataFrame(frame_records)
    raw_df["window_start_seconds"] = (raw_df["timestamp"] // window_seconds) * window_seconds

    # Group into time windows: filter out cut transition artifacts if normal frames exist
    normal_frames = raw_df[raw_df["is_cut"] == 0]
    agg_df = normal_frames if not normal_frames.empty else raw_df

    window_df = agg_df.groupby("window_start_seconds", as_index=False).agg(
        motion_mean=("motion_mean", "mean"),
        motion_std=("motion_std", "mean"),
        motion_max=("motion_max", "max"),
        motion_min=("motion_mean", "min"),
        motion_p90=("motion_p90", "max"),
        motion_jerk_mean=("motion_jerk", "mean"),
        spatial_concentration=("spatial_concentration", "mean"),
        directional_variance=("directional_variance", "mean"),
    )

    cuts_by_window = raw_df.groupby("window_start_seconds")["is_cut"].sum().reset_index(name="cut_count")
    window_df = pd.merge(window_df, cuts_by_window, on="window_start_seconds", how="left")
    window_df["cut_count"] = window_df["cut_count"].fillna(0.0)

    window_df["window_end_seconds"] = window_df["window_start_seconds"] + window_seconds
    window_df["thumbnail"] = window_df["window_start_seconds"].apply(
        lambda s: thumbnails.get(int(s), "")
    )

    total_cuts = int(raw_df["is_cut"].sum())
    duration_s = max(1.0, metadata.get("duration", 1.0))
    cuts_per_min = round((total_cuts / duration_s) * 60.0, 1)
    metadata["total_cuts"] = total_cuts
    metadata["cuts_per_minute"] = cuts_per_min
    metadata["is_edited_video"] = cuts_per_min > 8.0

    metadata["thumbnails"] = thumbnails
    return window_df, metadata
