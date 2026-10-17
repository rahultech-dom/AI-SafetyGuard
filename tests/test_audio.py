"""Tests for audio extraction, acoustic features, and distress phrase matching."""

import sys
from pathlib import Path
import pytest

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from safetyguard.audio.processor import (
    normalize_text,
    find_distress_keywords,
    compute_acoustic_features,
)


def test_distress_keywords_english():
    """Verify English distress phrase recognition."""
    text1 = "Somebody help me please! I am in danger."
    matches1 = find_distress_keywords(text1)
    assert any("help" in m.lower() for m in matches1)

    text_benign = "Can you help me with the math homework?"
    # It catches "help" as a potential word, but downstream fusion evaluates multimodality
    assert "help" in find_distress_keywords(text_benign)

    text_safe = "Today is a sunny day and we are walking."
    assert len(find_distress_keywords(text_safe)) == 0


def test_distress_keywords_hindi():
    """Verify Hindi transliteration and Devanagari phrase recognition."""
    text_hindi_trans = "Arrey koi bachao mujhe yahan!"
    assert "bachao" in find_distress_keywords(text_hindi_trans)

    text_hindi_madad = "Madad karo please jaldi aao"
    assert "madad karo" in find_distress_keywords(text_hindi_madad)

    text_devanagari = "अरे कोई मुझे बचाओ यहाँ से"
    assert "मुझे बचाओ" in find_distress_keywords(text_devanagari) or "बचाओ" in find_distress_keywords(text_devanagari)


def test_compute_acoustic_features():
    """Verify acoustic features on any existing WAV file."""
    audio_dir = Path(__file__).resolve().parent.parent / "data" / "audio"
    wav_files = list(audio_dir.glob("*.wav"))
    if not wav_files:
        pytest.skip("No WAV file found in data/audio for test.")

    df = compute_acoustic_features(wav_files[0], window_seconds=1.0)
    assert not df.empty
    assert "audio_rms" in df.columns
    assert "spectral_centroid" in df.columns
    assert "high_freq_ratio" in df.columns
    assert len(df) > 0
