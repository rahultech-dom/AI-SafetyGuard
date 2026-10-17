import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
import pandas as pd

from safetyguard.video.processor import extract_video_features
from safetyguard.audio.processor import extract_audio_from_video, compute_acoustic_features, transcribe_and_detect_distress
from safetyguard.ml.features import assemble_multimodal_features
from safetyguard.ml.classifier import ThreatClassifier
from safetyguard.fusion.assessor import assess_multimodal_incidents

vpath = list(Path('data/videos').glob('*2cw_61cXN8g*'))[0]
print(f"Analyzing Video: {vpath.name}")

v_df, meta = extract_video_features(vpath)
print(f"Duration: {meta['duration']}s, Resolution: {meta['width']}x{meta['height']}, FPS: {meta['fps']}")

wav_path = extract_audio_from_video(vpath)
a_df = compute_acoustic_features(wav_path) if wav_path else pd.DataFrame()
trans, alerts = transcribe_and_detect_distress(wav_path) if wav_path else ([], [])

print(f"Speech Transcripts Detected: {len(trans)}")
for t in trans:
    print(f"  [{t['start_seconds']:.1f}s - {t['end_seconds']:.1f}s]: \"{t['transcript']}\" (Matched: {t.get('matched_phrases', [])})")

if alerts:
    print(f"Distress Phrase Alerts: {len(alerts)}")
    for a in alerts:
        print(f"  ALERT: \"{a['phrase']}\" at {a['start_seconds']}s (conf: {a.get('confidence', 1.0):.2f})")
else:
    print("Distress Phrase Alerts: 0")

clf = ThreatClassifier.load()
feat = clf.predict_dataframe(assemble_multimodal_features(v_df, a_df, alerts))

print("\n--- Model Predictions Per Window ---")
for _, r in feat.iterrows():
    print(f"  Window {r['window_start_seconds']:.1f}s-{r['window_end_seconds']:.1f}s: "
          f"prob={r.get('model_threat_probability', 0.0):.2f}, "
          f"motion={r.get('motion_mean', 0.0):.2f}, "
          f"jerk={r.get('motion_jerk_mean', 0.0):.2f}")

res = assess_multimodal_incidents(feat, trans, alerts, min_confidence=0.45)
print("\n=== MULTIMODAL ASSESSMENT SUMMARY ===")
print(f"Total Windows: {res['summary']['total_windows']}")
print(f"Candidate Incidents Count: {res['summary']['incident_count']}")
print(f"High Priority Count: {res['summary']['high_priority_count']}")
print(f"Medium Priority Count: {res['summary']['medium_priority_count']}")

print("\n=== CANDIDATE INCIDENT INTERVALS ===")
if not res['incidents']:
    print("No safety threat or violent incident indicators detected.")
else:
    for inc in res['incidents']:
        print(f"[{inc['severity'].upper()}] {inc['start_seconds']}s - {inc['end_seconds']}s "
              f"(Peak Conf: {inc['peak_confidence']:.0%}): {inc['reasons']}")
