"""Dataset management, video-group splitting, and benchmark generation."""

import logging
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from safetyguard.config import DATA_DIR
from safetyguard.ml.features import FEATURE_COLUMNS

logger = logging.getLogger(__name__)

BENCHMARK_DATASET_PATH = DATA_DIR / "safety_benchmark_dataset.csv"


def generate_benchmark_dataset(
    output_path: Optional[Path] = None,
    num_videos: int = 40,
    windows_per_video: int = 25,
    random_seed: int = 42,
) -> pd.DataFrame:
    """
    Generate a realistic, reproducible benchmark dataset of multimodal feature windows
    with distinct video categories and clear provenance.
    
    Categories:
    - Normal Walking/Standing (Low motion, low directional variance, normal audio)
    - Fast Running/Dancing/Sports (High motion, low spatial concentration, rhythmic)
    - Physical Struggle/Aggression (High motion jerk, high directional variance, high spatial concentration, screaming/energy spike)
    - Sudden Fall/Collapse (Sharp jerk peak followed by near zero motion, possible distress phrase)
    
    Target label: 0 for Non-Threat / Normal, 1 for Potential Incident / Threat
    """
    rng = np.random.RandomState(random_seed)
    records = []

    video_types = [
        {"type": "normal_walk", "label": 0, "weight": 0.25},
        {"type": "running_dance_sports", "label": 0, "weight": 0.25},
        {"type": "music_video_dance", "label": 0, "weight": 0.20},
        {"type": "physical_struggle", "label": 1, "weight": 0.18},
        {"type": "sudden_fall", "label": 1, "weight": 0.12},
    ]

    weights = [vt["weight"] for vt in video_types]
    chosen_types = rng.choice(video_types, size=num_videos, p=weights)

    for vid_idx, v_cfg in enumerate(chosen_types):
        vid_name = f"video_{vid_idx:03d}_{v_cfg['type']}"
        v_type = v_cfg["type"]
        v_label = v_cfg["label"]

        for w_idx in range(windows_per_video):
            # Simulate features based on physical characteristics of each category
            if v_type == "normal_walk":
                motion_mean = float(rng.uniform(0.1, 0.6))
                motion_std = float(rng.uniform(0.02, 0.15))
                motion_max = motion_mean + float(rng.uniform(0.1, 0.4))
                motion_min = max(0.0, motion_mean - float(rng.uniform(0.05, 0.2)))
                motion_p90 = motion_mean + float(rng.uniform(0.05, 0.2))
                motion_jerk = float(rng.uniform(0.01, 0.12))
                spatial_conc = float(rng.uniform(0.05, 0.25))
                dir_var = float(rng.uniform(0.05, 0.3))
                audio_rms = float(rng.uniform(100.0, 500.0))
                spectral_centroid = float(rng.uniform(800.0, 1600.0))
                high_freq_ratio = float(rng.uniform(0.05, 0.2))
                audio_energy_spike = 1.0 if rng.rand() > 0.9 else 0.0
                distress_kw = 0.0

            elif v_type == "running_dance_sports":
                # High motion, but uniform and rhythmic, low directional variance
                motion_mean = float(rng.uniform(2.0, 6.0))
                motion_std = float(rng.uniform(0.8, 2.0))
                motion_max = motion_mean + float(rng.uniform(1.5, 4.0))
                motion_min = max(0.2, motion_mean - float(rng.uniform(1.0, 2.0)))
                motion_p90 = motion_mean + float(rng.uniform(0.8, 2.5))
                motion_jerk = float(rng.uniform(0.2, 1.2))
                spatial_conc = float(rng.uniform(0.1, 0.45))
                dir_var = float(rng.uniform(0.15, 0.55))
                audio_rms = float(rng.uniform(300.0, 2000.0))
                spectral_centroid = float(rng.uniform(1000.0, 2100.0))
                high_freq_ratio = float(rng.uniform(0.1, 0.3))
                audio_energy_spike = 1.0 if rng.rand() > 0.8 else 0.0
                distress_kw = 0.0

            elif v_type == "music_video_dance":
                # Fast dance choreography, music videos, social media dance trends
                # High motion, energetic dance beats, solo dancer on static camera or panning
                # Loud music audio (high RMS) but continuous, NO distress keywords, NO scream spike
                motion_mean = float(rng.uniform(2.5, 8.5))
                motion_std = float(rng.uniform(1.0, 3.0))
                motion_max = motion_mean + float(rng.uniform(1.5, 4.5))
                motion_min = max(0.1, motion_mean - float(rng.uniform(1.0, 2.5)))
                motion_p90 = motion_mean + float(rng.uniform(1.0, 3.0))
                motion_jerk = float(rng.uniform(0.4, 2.2))
                spatial_conc = float(rng.uniform(0.20, 0.65))
                dir_var = float(rng.uniform(0.20, 0.75))
                audio_rms = float(rng.uniform(2500.0, 11000.0))
                spectral_centroid = float(rng.uniform(1400.0, 2600.0))
                high_freq_ratio = float(rng.uniform(0.15, 0.40))
                audio_energy_spike = 1.0 if rng.rand() > 0.75 else 0.0
                distress_kw = 0.0

            elif v_type == "physical_struggle":
                # High jerk, violent altercation, chaotic motion, rapid acceleration/impacts
                # Covers both CCTV (static camera) and handheld footage (camera shaking/jerking)
                is_active_window = rng.rand() > 0.25
                if is_active_window:
                    is_cctv_struggle = rng.rand() > 0.6
                    if is_cctv_struggle:
                        # Fixed surveillance camera perspective: subjects occupy small frame region
                        motion_mean = float(rng.uniform(0.55, 1.8))
                        motion_std = float(rng.uniform(0.25, 0.8))
                        motion_max = motion_mean + float(rng.uniform(0.8, 2.0))
                        motion_min = 0.05
                        motion_p90 = motion_mean + float(rng.uniform(0.5, 1.2))
                        motion_jerk = float(rng.uniform(0.25, 0.95))
                        spatial_conc = float(rng.uniform(0.70, 0.98))
                        dir_var = float(rng.uniform(0.30, 0.85))
                    else:
                        # Close-up or handheld struggle
                        motion_mean = float(rng.uniform(3.5, 10.5))
                        motion_std = float(rng.uniform(1.5, 3.8))
                        motion_max = motion_mean + float(rng.uniform(2.5, 6.0))
                        motion_min = 0.1
                        motion_p90 = motion_mean + float(rng.uniform(1.8, 4.5))
                        motion_jerk = float(rng.uniform(1.8, 4.8))
                        spatial_conc = float(rng.uniform(0.15, 0.85))
                        dir_var = float(rng.uniform(0.10, 0.95))

                    audio_rms = float(rng.uniform(1500.0, 6000.0))
                    spectral_centroid = float(rng.uniform(2000.0, 3800.0))
                    high_freq_ratio = float(rng.uniform(0.30, 0.75))
                    audio_energy_spike = 1.0 if rng.rand() > 0.65 else 0.0
                    distress_kw = 1.0 if rng.rand() > 0.75 else 0.0
                else:
                    motion_mean = float(rng.uniform(0.5, 1.8))
                    motion_std = float(rng.uniform(0.2, 0.6))
                    motion_max = motion_mean + 0.8
                    motion_min = 0.1
                    motion_p90 = motion_mean + 0.5
                    motion_jerk = float(rng.uniform(0.1, 0.5))
                    spatial_conc = float(rng.uniform(0.15, 0.45))
                    dir_var = float(rng.uniform(0.15, 0.55))
                    audio_rms = float(rng.uniform(400.0, 1200.0))
                    spectral_centroid = float(rng.uniform(1000.0, 2000.0))
                    high_freq_ratio = float(rng.uniform(0.1, 0.3))
                    audio_energy_spike = 0.0
                    distress_kw = 0.0

            else:  # sudden_fall
                is_fall_moment = (w_idx == 10 or w_idx == 11)
                if is_fall_moment:
                    motion_mean = float(rng.uniform(3.0, 6.5))
                    motion_std = float(rng.uniform(1.5, 3.0))
                    motion_max = motion_mean + 4.0
                    motion_min = 0.05
                    motion_p90 = motion_mean + 2.5
                    motion_jerk = float(rng.uniform(1.8, 4.0))  # Extreme spike in jerk
                    spatial_conc = float(rng.uniform(0.5, 0.9))
                    dir_var = float(rng.uniform(0.4, 0.8))
                    audio_rms = float(rng.uniform(1500.0, 3000.0))
                    spectral_centroid = float(rng.uniform(2000.0, 3200.0))
                    high_freq_ratio = float(rng.uniform(0.35, 0.6))
                    audio_energy_spike = 1.0
                    distress_kw = 1.0 if rng.rand() > 0.5 else 0.0
                elif w_idx > 11:  # Post-fall lying still
                    motion_mean = float(rng.uniform(0.01, 0.15))
                    motion_std = float(rng.uniform(0.005, 0.03))
                    motion_max = motion_mean + 0.1
                    motion_min = 0.0
                    motion_p90 = motion_mean + 0.05
                    motion_jerk = float(rng.uniform(0.005, 0.05))
                    spatial_conc = float(rng.uniform(0.02, 0.1))
                    dir_var = 0.0
                    audio_rms = float(rng.uniform(50.0, 300.0))
                    spectral_centroid = float(rng.uniform(500.0, 1200.0))
                    high_freq_ratio = float(rng.uniform(0.02, 0.1))
                    audio_energy_spike = 0.0
                    distress_kw = 1.0 if rng.rand() > 0.7 else 0.0
                else:
                    motion_mean = float(rng.uniform(0.2, 0.7))
                    motion_std = float(rng.uniform(0.05, 0.2))
                    motion_max = motion_mean + 0.5
                    motion_min = 0.1
                    motion_p90 = motion_mean + 0.3
                    motion_jerk = float(rng.uniform(0.05, 0.2))
                    spatial_conc = float(rng.uniform(0.1, 0.25))
                    dir_var = float(rng.uniform(0.1, 0.3))
                    audio_rms = float(rng.uniform(150.0, 400.0))
                    spectral_centroid = float(rng.uniform(900.0, 1500.0))
                    high_freq_ratio = float(rng.uniform(0.05, 0.2))
                    audio_energy_spike = 0.0
                    distress_kw = 0.0

            records.append({
                "video_id": vid_name,
                "window_start_seconds": float(w_idx),
                "motion_mean": motion_mean,
                "motion_std": motion_std,
                "motion_max": motion_max,
                "motion_min": motion_min,
                "motion_p90": motion_p90,
                "motion_jerk_mean": motion_jerk,
                "spatial_concentration": spatial_conc,
                "directional_variance": dir_var,
                "audio_rms": audio_rms,
                "spectral_centroid": spectral_centroid,
                "high_freq_ratio": high_freq_ratio,
                "audio_energy_spike": audio_energy_spike,
                "distress_keyword_count": distress_kw,
                "label": v_label,
                "video_category": v_type,
            })

    df = pd.DataFrame(records)
    save_path = output_path or BENCHMARK_DATASET_PATH
    save_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(save_path, index=False)
    logger.info("Saved benchmark dataset with %d rows across %d videos to %s", len(df), num_videos, save_path)
    return df


def load_dataset_with_group_split(
    dataset_path: Optional[Path] = None,
    test_size: float = 0.25,
    val_size: float = 0.20,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load dataset and split into train, validation, and test sets strictly grouped by video_id
    to prevent temporal leakage across adjacent frames!
    """
    path = dataset_path or BENCHMARK_DATASET_PATH
    if not path.is_file():
        generate_benchmark_dataset(path)

    df = pd.read_csv(path)
    if "video_id" not in df.columns or "label" not in df.columns:
        raise ValueError("Dataset must contain 'video_id' and 'label' columns.")

    groups = df["video_id"].values

    # First split off test set by video_id
    gss_test = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_val_idx, test_idx = next(gss_test.split(df, df["label"], groups=groups))

    train_val_df = df.iloc[train_val_idx].copy()
    test_df = df.iloc[test_idx].copy()

    # Second split train_val into train and validation by video_id
    adjusted_val_size = val_size / (1.0 - test_size)
    gss_val = GroupShuffleSplit(n_splits=1, test_size=adjusted_val_size, random_state=random_state)
    train_idx, val_idx = next(gss_val.split(train_val_df, train_val_df["label"], groups=train_val_df["video_id"].values))

    train_df = train_val_df.iloc[train_idx].copy()
    val_df = train_val_df.iloc[val_idx].copy()

    return train_df, val_df, test_df
