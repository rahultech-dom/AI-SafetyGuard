"""Configuration module for AI SafetyGuard."""

import os
from pathlib import Path
from typing import List, Set

# Base directories
PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

DATA_DIR = PROJECT_ROOT / "data"
VIDEOS_DIR = DATA_DIR / "videos"
AUDIO_DIR = DATA_DIR / "audio"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
MODELS_DIR = PROJECT_ROOT / "models"
JOBS_DIR = OUTPUTS_DIR / "jobs"

for directory in [DATA_DIR, VIDEOS_DIR, AUDIO_DIR, OUTPUTS_DIR, MODELS_DIR, JOBS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Processing settings
DEFAULT_FRAME_SAMPLE_FPS = 5.0  # Sample rate for optical flow analysis
WINDOW_SECONDS = 1.0            # Analysis window size
MAX_UPLOAD_SIZE_MB = 250        # Upload limit
MAX_VIDEO_DURATION_SECONDS = 600  # 10 minutes max for reasonable processing
SUPPORTED_VIDEO_EXTENSIONS: Set[str] = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

# Audio processing settings
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_CHUNK_SECONDS = 5.0

# Distress keywords (English, Hindi transliterated, Devanagari Hindi)
DEFAULT_DISTRESS_KEYWORDS: List[str] = [
    # English
    "help",
    "help me",
    "please help",
    "save me",
    "stop it",
    "leave me",
    "call police",
    "someone help",
    "emergency",
    # Hindi Transliteration
    "bachao",
    "bachaao",
    "madad",
    "madad karo",
    "mujhe bachao",
    "chhoro",
    "chodo",
    "mat karo",
    "police bulao",
    # Hindi Devanagari
    "मदद",
    "बचाओ",
    "मुझे बचाओ",
    "मदद करो",
    "छोड़ो",
    "मुझे छोड़ो",
    "मत करो",
    "पुलिस बुलाओ",
    "गुहार",
]

# Multimodal incident assessment thresholds
DEFAULT_MOTION_ANOMALY_THRESHOLD = 1.8   # Standard deviation threshold for optical flow jerk
DEFAULT_MOTION_INTENSITY_HIGH = 2.5       # High optical flow mean magnitude
DEFAULT_AUDIO_ENERGY_SPIKE_RATIO = 2.2   # Audio RMS jump over local baseline
DEFAULT_SCREAM_SPECTRAL_CENTROID_HZ = 2200.0  # High frequency centroid typical of shouts/screams
