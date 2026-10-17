"""Audio analysis pipeline: extraction, acoustic feature analysis, and speech/distress detection."""

import logging
import math
import re
import subprocess
import wave
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import speech_recognition as sr

from safetyguard.config import (
    AUDIO_DIR,
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    AUDIO_CHUNK_SECONDS,
    DEFAULT_DISTRESS_KEYWORDS,
    DEFAULT_AUDIO_ENERGY_SPIKE_RATIO,
    DEFAULT_SCREAM_SPECTRAL_CENTROID_HZ,
)

logger = logging.getLogger(__name__)


class AudioProcessingError(Exception):
    """Raised when audio extraction or analysis fails."""
    pass


def extract_audio_from_video(
    video_path: Path,
    output_wav_path: Optional[Path] = None,
) -> Optional[Path]:
    """
    Extract standardized 16000Hz mono PCM WAV audio from video file using FFmpeg.
    Returns path to WAV file or None if video has no audio stream.
    """
    if not video_path.is_file():
        raise AudioProcessingError(f"Video file not found: {video_path}")

    target_wav = output_wav_path or (AUDIO_DIR / f"{video_path.stem}.wav")
    target_wav.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(video_path),
        "-vn",
        "-ac", str(AUDIO_CHANNELS),
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-c:a", "pcm_s16le",
        str(target_wav),
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.warning("FFmpeg did not extract audio (video may have no audio track): %s", result.stderr)
            return None

        if not target_wav.is_file() or target_wav.stat().st_size < 100:
            return None

        return target_wav
    except FileNotFoundError:
        raise AudioProcessingError("FFmpeg executable not found in PATH.")
    except Exception as err:
        raise AudioProcessingError(f"Audio extraction failed: {err}") from err


def compute_acoustic_features(
    wav_path: Path,
    window_seconds: float = 1.0,
) -> pd.DataFrame:
    """
    Extract window-level acoustic features:
    - RMS Energy (volume / intensity)
    - High-frequency ratio & Spectral centroid (indicative of screams / shouts)
    - Energy jump ratio over moving baseline
    """
    if not wav_path or not wav_path.is_file():
        return pd.DataFrame()

    try:
        with wave.open(str(wav_path), "rb") as wf:
            sample_rate = wf.getframerate()
            n_channels = wf.getnchannels()
            n_frames = wf.getnframes()
            audio_bytes = wf.readframes(n_frames)

        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        if n_channels > 1:
            samples = samples.reshape(-1, n_channels).mean(axis=1)

        total_seconds = len(samples) / sample_rate
        if total_seconds < 0.2:
            return pd.DataFrame()

        window_size = int(sample_rate * window_seconds)
        n_windows = int(math.ceil(len(samples) / window_size))

        window_records = []
        global_rms_values = []

        for w_idx in range(n_windows):
            start_sample = w_idx * window_size
            end_sample = min(len(samples), (w_idx + 1) * window_size)
            chunk = samples[start_sample:end_sample]

            if len(chunk) < 100:
                continue

            start_sec = round(start_sample / sample_rate, 2)
            end_sec = round(end_sample / sample_rate, 2)

            # RMS Energy
            rms = float(np.sqrt(np.mean(chunk**2)))
            global_rms_values.append(rms)

            # FFT for spectral features
            # Screams and high-pitched distress sounds concentrate power in 1.5 kHz - 4.5 kHz
            fft_vals = np.abs(np.fft.rfft(chunk))
            freqs = np.fft.rfftfreq(len(chunk), d=1.0 / sample_rate)

            total_energy = np.sum(fft_vals) + 1e-6
            spectral_centroid = float(np.sum(freqs * fft_vals) / total_energy)

            # High frequency ratio (energy between 1500Hz and 4500Hz)
            scream_band = (freqs >= 1500) & (freqs <= 4500)
            high_freq_ratio = float(np.sum(fft_vals[scream_band]) / total_energy)

            window_records.append({
                "window_start_seconds": start_sec,
                "window_end_seconds": end_sec,
                "audio_rms": rms,
                "spectral_centroid": spectral_centroid,
                "high_freq_ratio": high_freq_ratio,
            })

        df = pd.DataFrame(window_records)
        if not df.empty:
            baseline_rms = df["audio_rms"].median() + 1e-4
            df["energy_ratio_to_baseline"] = df["audio_rms"] / baseline_rms
            df["potential_sound_anomaly"] = (
                (df["energy_ratio_to_baseline"] > DEFAULT_AUDIO_ENERGY_SPIKE_RATIO) &
                (df["spectral_centroid"] > DEFAULT_SCREAM_SPECTRAL_CENTROID_HZ)
            )

        return df

    except Exception as err:
        logger.warning("Error computing acoustic features: %s", err)
        return pd.DataFrame()


def normalize_text(text: str) -> str:
    """Normalize text by converting to lowercase and removing punctuation."""
    return re.sub(r"[^\w\s]", " ", text.lower()).strip()


def find_distress_keywords(
    text: str,
    keywords: Optional[List[str]] = None,
) -> List[str]:
    """Find distress keywords in the transcription using word boundary matching."""
    if not text:
        return []

    target_keywords = keywords or DEFAULT_DISTRESS_KEYWORDS
    norm_text = normalize_text(text)
    matched = []

    for kw in target_keywords:
        norm_kw = normalize_text(kw)
        if not norm_kw:
            continue
        pattern = r"(?<!\w)" + re.escape(norm_kw) + r"(?!\w)"
        if re.search(pattern, norm_text):
            matched.append(kw)

    return list(dict.fromkeys(matched))


def transcribe_and_detect_distress(
    wav_path: Optional[Path],
    chunk_seconds: float = AUDIO_CHUNK_SECONDS,
    keywords: Optional[List[str]] = None,
    allow_cloud_service: bool = True,
    progress_callback: Optional[Any] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Transcribe speech in chunks and flag distress phrases.
    
    Returns:
        Tuple of (all_transcripts, distress_alerts)
    """
    if not wav_path or not wav_path.is_file():
        return [], []

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    transcripts: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []

    try:
        with sr.AudioFile(str(wav_path)) as source:
            total_duration = source.DURATION
            chunk_num = 0

            while True:
                audio_chunk = recognizer.record(source, duration=chunk_seconds)
                if not audio_chunk.get_raw_data():
                    break

                start_sec = round(chunk_num * chunk_seconds, 2)
                end_sec = round(start_sec + chunk_seconds, 2)

                chunk_text = ""
                recognized_lang = "none"
                service_used = "offline-fallback"

                if allow_cloud_service:
                    # Attempt recognition in English (India) and Hindi
                    for lang in ["en-IN", "hi-IN"]:
                        try:
                            text = recognizer.recognize_google(audio_chunk, language=lang)
                            if text and len(text.strip()) > 0:
                                chunk_text = text.strip()
                                recognized_lang = lang
                                service_used = "google-speech"
                                break
                        except (sr.UnknownValueError, sr.RequestError):
                            continue

                if chunk_text:
                    matched = find_distress_keywords(chunk_text, keywords)
                    item = {
                        "start_seconds": start_sec,
                        "end_seconds": end_sec,
                        "language": recognized_lang,
                        "transcript": chunk_text,
                        "matched_phrases": matched,
                        "service": service_used,
                    }
                    transcripts.append(item)

                    if matched:
                        alert = {
                            "start_seconds": start_sec,
                            "end_seconds": end_sec,
                            "language": recognized_lang,
                            "transcript": chunk_text,
                            "matched_phrases": matched,
                            "alert_type": "Audible Distress Keyword",
                            "review_status": "Human review recommended",
                        }
                        alerts.append(alert)

                chunk_num += 1
                if progress_callback and total_duration > 0:
                    pct = min(100.0, (start_sec / total_duration) * 100.0)
                    progress_callback(pct, f"Analyzing audio chunk {chunk_num} ({start_sec:.1f}s)")

    except Exception as err:
        logger.warning("Speech recognition warning/fallback: %s", err)

    return transcripts, alerts
