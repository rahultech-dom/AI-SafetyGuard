"""Multimodal incident assessment and fusion module."""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Severity / Review Priority Categories
CATEGORY_NO_INDICATOR = "No indicator detected by the available models"
CATEGORY_REVIEW_RECOMMENDED = "Potential incident — review recommended"
CATEGORY_HIGH_PRIORITY = "Higher-priority review based on multiple indicators"
CATEGORY_UNRELIABLE = "Unable to analyse reliably"


def assess_multimodal_incidents(
    feature_df: pd.DataFrame,
    transcripts: List[Dict[str, Any]],
    distress_alerts: List[Dict[str, Any]],
    min_confidence: float = 0.45,
    sensitivity: str = "balanced",
) -> Dict[str, Any]:
    """
    Fuse visual and audio features into timestamped candidate incident intervals
    with transparent reasons, temporal consistency filtering, and review priorities.
    
    Returns:
        Dictionary containing:
            - summary: high-level metrics
            - incidents: list of candidate incident intervals
            - timeline_windows: 1-second window records for timeline visualization
    """
    if feature_df.empty:
        return {
            "summary": {
                "total_windows": 0,
                "incident_count": 0,
                "high_priority_count": 0,
                "medium_priority_count": 0,
                "audio_alerts_count": len(distress_alerts),
                "system_disclaimer": "Analysis indicates no conclusive determination of safety or guilt.",
            },
            "incidents": [],
            "timeline_windows": [],
        }

    df = feature_df.copy()
    n_rows = len(df)

    # Sensitivity thresholds
    if sensitivity == "high_precision":
        jerk_threshold = 2.8
        motion_threshold = 5.5
        effective_min_conf = max(0.50, min_confidence)
    elif sensitivity == "high_recall":
        jerk_threshold = 2.1
        motion_threshold = 4.5
        effective_min_conf = min(0.35, min_confidence)
    else:  # balanced
        jerk_threshold = 2.5
        motion_threshold = 5.0
        effective_min_conf = min_confidence

    raw_window_flags = []

    for idx, row in df.iterrows():
        w_start = float(row["window_start_seconds"])
        w_end = float(row.get("window_end_seconds", w_start + 1.0))
        prob = float(row.get("model_threat_probability", 0.0))
        jerk = float(row.get("motion_jerk_mean", 0.0))
        mag = float(row.get("motion_mean", 0.0))
        dir_var = float(row.get("directional_variance", 0.0))
        cuts = float(row.get("cut_count", 0.0))
        kw_hits = int(row.get("distress_keyword_count", 0))
        sound_anomaly = bool(
            row.get("audio_energy_spike", 0) > 0.5 and
            float(row.get("spectral_centroid", 0.0)) >= 2200.0
        )

        # Check overlapping transcripts and phrases
        window_transcripts = []
        window_keywords = []
        for t in transcripts:
            if t.get("start_seconds", 0) < w_end and t.get("end_seconds", 0) > w_start:
                window_transcripts.append(t.get("transcript", ""))
                window_keywords.extend(t.get("matched_phrases", []))

        spatial_conc = float(row.get("spatial_concentration", 0.0))

        # Violent physical struggle motion profile
        # Genuine altercations exhibit violent sharp jerk combined with high-intensity motion
        # Corroborated by model threat probability >= 0.26 to avoid camera whip pans on static walls
        is_violent_action = (jerk >= jerk_threshold and mag >= motion_threshold and prob >= 0.26)
        
        # CCTV altercation brawl profile:
        # Fixed surveillance camera perspective: localized struggle (spatial_conc >= 0.70)
        # with elevated motion (>= 0.50) and jerk (>= 0.22)
        is_cctv_brawl = (mag >= 0.50 and jerk >= 0.22 and spatial_conc >= 0.70 and prob >= 0.16)

        # Observable motion guard: quiet corridors or stationary counters (mag < 0.25) cannot be physical altercations
        has_active_motion = (mag >= 0.45 or jerk >= 0.22)
        has_ml_threat = (prob >= effective_min_conf and has_active_motion)

        raw_window_flags.append({
            "idx": idx,
            "start": w_start,
            "end": w_end,
            "prob": prob,
            "jerk": jerk,
            "mag": mag,
            "cuts": cuts,
            "is_violent_action": is_violent_action,
            "is_cctv_brawl": is_cctv_brawl,
            "has_ml_threat": has_ml_threat,
            "has_audio_kw": bool(window_keywords or kw_hits > 0),
            "has_acoustic": sound_anomaly,
            "window_keywords": window_keywords,
            "window_transcripts": window_transcripts,
            "thumbnail": str(row.get("thumbnail", "")),
        })

    # Temporal consistency filter:
    # Real altercations and distress events persist across multiple seconds.
    # An isolated 1-second visual blip without audio distress is filtered out as dance or camera motion.
    timeline_windows: List[Dict[str, Any]] = []

    for i, w in enumerate(raw_window_flags):
        has_prev_violent = (
            i > 0 and (
                raw_window_flags[i - 1]["is_violent_action"]
                or raw_window_flags[i - 1]["is_cctv_brawl"]
            )
        )
        has_next_violent = (
            i < n_rows - 1 and (
                raw_window_flags[i + 1]["is_violent_action"]
                or raw_window_flags[i + 1]["is_cctv_brawl"]
            )
        )
        is_sustained = (has_prev_violent or has_next_violent)

        # Sudden fall detection: sharp jerk (>= 0.22 in CCTV, >= 1.2 in handheld) followed by near-motionless stillness (mag <= 0.20)
        is_fall_detected = False
        if i > 0 and raw_window_flags[i - 1]["jerk"] >= 0.22 and w["mag"] <= 0.20 and raw_window_flags[i - 1]["mag"] >= 0.28:
            is_fall_detected = True

        valid_visual = False
        reasons: List[str] = []
        indicators_count = 0

        # Observable violence indicator:
        # A visual incident requires an observable physical signature:
        # 1. Sudden slip/fall impact followed by immobility (is_fall_detected)
        # 2. Localized CCTV altercation brawl (is_cctv_brawl) sustained or with audio
        # 3. Violent struggle motion (is_violent_action) sustained or with audio
        # 4. Elevated ML threat probability corroborated by audio distress keyword or acoustic anomaly
        if is_fall_detected:
            valid_visual = True
            indicators_count += 1
            reasons.append("Sudden fall and collapse detected (person stationary after impact)")
        elif w["is_cctv_brawl"] and (is_sustained or w["has_audio_kw"]):
            valid_visual = True
            indicators_count += 1
            reasons.append(f"CCTV physical brawl/altercation (jerk={w['jerk']:.2f}, motion={w['mag']:.2f})")
        elif w["is_violent_action"] and (is_sustained or w["has_audio_kw"] or w["has_acoustic"]):
            valid_visual = True
            indicators_count += 1
            reasons.append(f"Violent physical struggle motion (jerk={w['jerk']:.2f}, motion={w['mag']:.2f})")
        elif w["has_ml_threat"] and (w["has_audio_kw"] or w["has_acoustic"]):
            valid_visual = True
            indicators_count += 1
            reasons.append(f"Elevated visual action score ({w['prob']:.0%}) corroborated by acoustic evidence")

        # Audio indicators
        if w["has_audio_kw"]:
            indicators_count += 1
            kw_str = ", ".join(sorted(set(w["window_keywords"]))) if w["window_keywords"] else "distress phrase"
            reasons.append(f"Distress keyword detected: '{kw_str}'")

        if w["has_acoustic"]:
            # Corroborate acoustic energy spike with distress keywords OR violent struggle
            if w["has_audio_kw"]:
                indicators_count += 1
                reasons.append("Acoustic energy spike corroborated by distress keyword")
            elif is_violent_action:
                indicators_count += 1
                reasons.append("Acoustic energy spike corroborated by violent physical struggle")

        # Elevation to High Priority:
        # 1. Multimodal confirmation (both visual struggle + audio distress/scream) -> indicators_count >= 2
        # 2. Sustained high-intensity physical struggle across >= 3 windows in the local cluster
        if valid_visual and w["is_violent_action"]:
            cluster = raw_window_flags[max(0, i - 2): min(n_rows, i + 3)]
            violent_count = sum(1 for cw in cluster if cw["is_violent_action"])
            if violent_count >= 3:
                indicators_count = max(indicators_count, 2)
                if "Sustained high-intensity physical altercation" not in reasons:
                    reasons.append("Sustained high-intensity physical altercation")

        # Strict 4-category classification
        if indicators_count >= 2:
            category = CATEGORY_HIGH_PRIORITY
            severity = "high"
        elif indicators_count == 1:
            category = CATEGORY_REVIEW_RECOMMENDED
            severity = "medium"
        else:
            category = CATEGORY_NO_INDICATOR
            severity = "low"

        # Check for unreliability (e.g. video totally black or zero motion)
        if w["mag"] == 0 and w["jerk"] == 0 and not w["window_transcripts"] and df["motion_mean"].sum() == 0:
            category = CATEGORY_UNRELIABLE
            severity = "unknown"
            reasons = ["Zero motion or missing stream data"]

        timeline_windows.append({
            "start_seconds": w["start"],
            "end_seconds": w["end"],
            "category": category,
            "severity": severity,
            "confidence": round(w["prob"], 2),
            "reasons": reasons,
            "motion_intensity": round(w["mag"], 2),
            "motion_jerk": round(w["jerk"], 2),
            "audio_detected": bool(w["window_transcripts"] or w["has_acoustic"]),
            "matched_keywords": list(set(w["window_keywords"])),
            "transcript_snippet": " | ".join(w["window_transcripts"]) if w["window_transcripts"] else "",
            "thumbnail": w["thumbnail"],
        })

    # Group adjacent flagged windows into contiguous incident intervals
    incidents: List[Dict[str, Any]] = []
    current_incident: Optional[Dict[str, Any]] = None

    for w in timeline_windows:
        is_flagged = w["severity"] in ["high", "medium"]

        if is_flagged:
            if current_incident is None:
                current_incident = {
                    "incident_id": f"inc_{int(w['start_seconds']):04d}",
                    "start_seconds": w["start_seconds"],
                    "end_seconds": w["end_seconds"],
                    "category": w["category"],
                    "severity": w["severity"],
                    "peak_confidence": w["confidence"],
                    "reasons": list(w["reasons"]),
                    "keywords": list(w["matched_keywords"]),
                    "transcripts": [w["transcript_snippet"]] if w["transcript_snippet"] else [],
                    "thumbnail": w["thumbnail"],
                    "review_status": "Pending Human Review",
                    "human_notes": "",
                }
            else:
                # Extend existing interval
                current_incident["end_seconds"] = w["end_seconds"]
                current_incident["peak_confidence"] = max(current_incident["peak_confidence"], w["confidence"])
                if w["severity"] == "high":
                    current_incident["severity"] = "high"
                    current_incident["category"] = CATEGORY_HIGH_PRIORITY
                for r in w["reasons"]:
                    if r not in current_incident["reasons"]:
                        current_incident["reasons"].append(r)
                for k in w["matched_keywords"]:
                    if k not in current_incident["keywords"]:
                        current_incident["keywords"].append(k)
                if w["transcript_snippet"] and w["transcript_snippet"] not in current_incident["transcripts"]:
                    current_incident["transcripts"].append(w["transcript_snippet"])
                if not current_incident["thumbnail"] and w["thumbnail"]:
                    current_incident["thumbnail"] = w["thumbnail"]
        else:
            if current_incident is not None:
                incidents.append(current_incident)
                current_incident = None

    if current_incident is not None:
        incidents.append(current_incident)

    # Filter out sub-2s blips unless distress keywords or falls were detected
    filtered_incidents: List[Dict[str, Any]] = []
    for inc in incidents:
        duration = inc["end_seconds"] - inc["start_seconds"]
        has_kw = len(inc["keywords"]) > 0
        is_fall = any("fall" in str(r).lower() for r in inc.get("reasons", []))
        if duration >= 1.9 or has_kw or is_fall:
            filtered_incidents.append(inc)

    high_pri_count = sum(1 for inc in filtered_incidents if inc["severity"] == "high")

    return {
        "summary": {
            "total_windows": len(timeline_windows),
            "incident_count": len(filtered_incidents),
            "high_priority_count": high_pri_count,
            "medium_priority_count": len(filtered_incidents) - high_pri_count,
            "audio_alerts_count": len(distress_alerts),
            "system_disclaimer": (
                "AI SafetyGuard identifies observable visual/acoustic warning signs for human review. "
                "These signals do not prove a crime has occurred, and the absence of alerts does not establish safety."
            ),
        },
        "incidents": filtered_incidents,
        "timeline_windows": timeline_windows,
    }
