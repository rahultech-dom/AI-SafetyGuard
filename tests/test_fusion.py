"""Tests for multimodal fusion and incident assessment."""

import sys
from pathlib import Path
import pytest
import pandas as pd

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from safetyguard.fusion.assessor import (
    assess_multimodal_incidents,
    CATEGORY_NO_INDICATOR,
    CATEGORY_REVIEW_RECOMMENDED,
    CATEGORY_HIGH_PRIORITY,
)


def test_multimodal_assessment_priorities():
    """Verify that multiple coinciding indicators trigger higher priority review."""
    windows = [
        # Window 0: Normal walk
        {
            "window_start_seconds": 0.0,
            "window_end_seconds": 1.0,
            "motion_mean": 0.3,
            "motion_jerk_mean": 0.05,
            "directional_variance": 0.1,
            "spatial_concentration": 0.1,
            "model_threat_probability": 0.1,
            "audio_energy_spike": 0.0,
            "distress_keyword_count": 0,
        },
        # Window 1: Isolated distress word with low motion -> medium priority review
        {
            "window_start_seconds": 1.0,
            "window_end_seconds": 2.0,
            "motion_mean": 0.4,
            "motion_jerk_mean": 0.1,
            "directional_variance": 0.2,
            "spatial_concentration": 0.15,
            "model_threat_probability": 0.2,
            "audio_energy_spike": 0.0,
            "distress_keyword_count": 1,
        },
        # Window 2: Visual motion anomaly + distress word + acoustic scream -> high priority review!
        {
            "window_start_seconds": 2.0,
            "window_end_seconds": 3.0,
            "motion_mean": 4.5,
            "motion_jerk_mean": 2.2,
            "directional_variance": 0.8,
            "spatial_concentration": 0.7,
            "model_threat_probability": 0.85,
            "audio_energy_spike": 1.0,
            "distress_keyword_count": 1,
        },
    ]

    feature_df = pd.DataFrame(windows)
    transcripts = [
        {"start_seconds": 1.0, "end_seconds": 3.0, "transcript": "help please", "matched_phrases": ["help"]}
    ]
    alerts = [
        {"start_seconds": 1.0, "end_seconds": 3.0, "matched_phrases": ["help"]}
    ]

    res = assess_multimodal_incidents(feature_df, transcripts, alerts)

    t_windows = res["timeline_windows"]
    assert len(t_windows) == 3

    # Window 0: No indicator
    assert t_windows[0]["category"] == CATEGORY_NO_INDICATOR
    assert t_windows[0]["severity"] == "low"

    # Window 1: Isolated distress word -> Medium priority
    assert t_windows[1]["category"] == CATEGORY_REVIEW_RECOMMENDED
    assert t_windows[1]["severity"] == "medium"

    # Window 2: Multimodal coincidence -> High priority
    assert t_windows[2]["category"] == CATEGORY_HIGH_PRIORITY
    assert t_windows[2]["severity"] == "high"

    # Verify incident intervals aggregation
    incidents = res["incidents"]
    assert len(incidents) >= 1
    # Check that peak confidence and category reflect highest severity
    highest_inc = max(incidents, key=lambda i: i["peak_confidence"])
    assert highest_inc["severity"] == "high"
    assert "Distress keyword detected" in " ".join(highest_inc["reasons"])
