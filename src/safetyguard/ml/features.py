"""Feature schema, normalization, and assembly for ML models."""

from typing import List, Dict, Any
import numpy as np
import pandas as pd

# Standard features extracted per time window for the classifier
FEATURE_COLUMNS: List[str] = [
    "motion_mean",
    "motion_std",
    "motion_max",
    "motion_min",
    "motion_p90",
    "motion_jerk_mean",
    "spatial_concentration",
    "directional_variance",
    "audio_rms",
    "spectral_centroid",
    "high_freq_ratio",
    "audio_energy_spike",
    "distress_keyword_count",
]


def assemble_multimodal_features(
    video_df: pd.DataFrame,
    audio_df: pd.DataFrame,
    distress_alerts: List[Dict[str, Any]],
) -> pd.DataFrame:
    """
    Merge visual optical flow features with acoustic features and distress keyword alerts
    on 1-second time windows.
    """
    if video_df.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS + ["window_start_seconds", "window_end_seconds"])

    df = video_df.copy()

    # Merge acoustic features if available
    if not audio_df.empty and "window_start_seconds" in audio_df.columns:
        audio_cols = [
            "window_start_seconds", "audio_rms", "spectral_centroid",
            "high_freq_ratio", "energy_ratio_to_baseline"
        ]
        available_cols = [c for c in audio_cols if c in audio_df.columns]
        sub_audio = audio_df[available_cols].copy()

        # Align to nearest second
        sub_audio["window_start_seconds"] = np.floor(sub_audio["window_start_seconds"])
        sub_audio = sub_audio.groupby("window_start_seconds", as_index=False).mean()

        df = pd.merge(df, sub_audio, on="window_start_seconds", how="left")
    else:
        df["audio_rms"] = 0.0
        df["spectral_centroid"] = 0.0
        df["high_freq_ratio"] = 0.0
        df["energy_ratio_to_baseline"] = 1.0

    # Fill defaults for audio
    df["audio_rms"] = df["audio_rms"].fillna(0.0)
    df["spectral_centroid"] = df["spectral_centroid"].fillna(0.0)
    df["high_freq_ratio"] = df["high_freq_ratio"].fillna(0.0)
    df["audio_energy_spike"] = (df.get("energy_ratio_to_baseline", 1.0) > 2.0).astype(float)

    # Distress keyword count per window
    keyword_counts = []
    for _, row in df.iterrows():
        w_start = row["window_start_seconds"]
        w_end = row.get("window_end_seconds", w_start + 1.0)
        kw_hits = 0
        for alert in distress_alerts:
            a_start = alert.get("start_seconds", 0)
            a_end = alert.get("end_seconds", a_start + 5)
            # Check overlap
            if a_start < w_end and a_end > w_start:
                kw_hits += len(alert.get("matched_phrases", []))
        keyword_counts.append(kw_hits)

    df["distress_keyword_count"] = keyword_counts

    # Ensure all expected feature columns exist with numeric values
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    return df
