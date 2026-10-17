"""Comprehensive Evaluation of AI SafetyGuard on CCTV and Real-World Footages.
Measures Accuracy, Precision, Recall, Specificity, F1-Score, and False Positive Rate."""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import time
from pathlib import Path
import pandas as pd
import numpy as np

from safetyguard.video.processor import extract_video_features
from safetyguard.audio.processor import compute_acoustic_features, transcribe_and_detect_distress
from safetyguard.ml.features import assemble_multimodal_features
from safetyguard.ml.classifier import ThreatClassifier
from safetyguard.fusion.assessor import assess_multimodal_incidents

VIDEOS_DIR = Path("data/videos")
AUDIO_DIR = Path("data/audio")
OUTPUTS_DIR = Path("outputs")
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Test dataset specification with ground truth
BENCHMARK_CASES = [
    # 1. CCTV Footages
    {
        "id": "CCTV-01",
        "category": "CCTV Footage",
        "name": "Store Checkout Counter",
        "filename": "cctv_normal_store_counter.mp4",
        "ground_truth_label": 0,
        "description": "Fixed camera overlooking store checkout, peaceful customer transaction",
    },
    {
        "id": "CCTV-02",
        "category": "CCTV Footage",
        "name": "Hallway Corridor Patrol",
        "filename": "cctv_normal_hallway_patrol.mp4",
        "ground_truth_label": 0,
        "description": "Fixed corridor surveillance camera, normal pedestrian walking",
    },
    {
        "id": "CCTV-03",
        "category": "CCTV Footage",
        "name": "Parking Lot Altercation Brawl",
        "filename": "cctv_crime_altercation_brawl.mp4",
        "ground_truth_label": 1,
        "description": "Surveillance camera capturing violent physical grappling and tackle",
    },
    {
        "id": "CCTV-04",
        "category": "CCTV Footage",
        "name": "Stairwell Slip & Fall",
        "filename": "cctv_crime_slip_fall.mp4",
        "ground_truth_label": 1,
        "description": "Surveillance camera capturing sudden slip, collapse and motionless person",
    },

    # 2. Real-World Crime / Threat Altercations
    {
        "id": "REAL-01",
        "category": "Real-World Altercation",
        "name": "Crime Patrol Viral Fight Scene",
        "pattern": "*Crime Patrol*.mp4",
        "ground_truth_label": 1,
        "description": "Handheld recorded fight scene with violent struggle, pushing and grappling",
    },
    {
        "id": "REAL-02",
        "category": "Real-World Altercation",
        "name": "Coffee Shop Criminal Altercation",
        "pattern": "*Lio Vs Five Criminal Fight*.mp4",
        "ground_truth_label": 1,
        "description": "Coffee shop brawl with multiple individuals engaging in physical fighting",
    },
    {
        "id": "REAL-03",
        "category": "Real-World Altercation",
        "name": "Action Fight Sequence",
        "pattern": "*Alia Bhatt*Jigra*.mp4",
        "ground_truth_label": 1,
        "description": "Fast-paced combat and physical struggle action sequence",
    },

    # 3. Real-World Normal Activities / Non-Threat Controls
    {
        "id": "REAL-04",
        "category": "Real-World Normal",
        "name": "Pedestrian Walk Normal",
        "filename": "test_walk.mp4",
        "ground_truth_label": 0,
        "description": "Normal walking movement without physical aggression or distress",
    },
    {
        "id": "REAL-05",
        "category": "Real-World Normal",
        "name": "Car Fueling Monologue Vlog",
        "pattern": "*Brabus*.mp4",
        "ground_truth_label": 0,
        "description": "User speaking about car fuel cost, non-threatening daily activity",
    },
    {
        "id": "REAL-06",
        "category": "Real-World Normal",
        "name": "Guru Randhawa Music Dance Video",
        "pattern": "*GURU RANDHAWA*.mp4",
        "ground_truth_label": 0,
        "description": "Fast-paced dance choreography with frequent camera cuts and loud music",
    },
    {
        "id": "REAL-07",
        "category": "Real-World Normal",
        "name": "Dance Short Choreography",
        "pattern": "*Zero Figure*.mp4",
        "ground_truth_label": 0,
        "description": "High-energy dance short with solo dancer in center frame and electronic music",
    },
    {
        "id": "REAL-08",
        "category": "Real-World Normal",
        "name": "Stand-up Comedy & Dialogue",
        "pattern": "*Nishant Tanwar*.mp4",
        "ground_truth_label": 0,
        "description": "Conversational speech and laughter in comedy show setting",
    },
]

def resolve_video_file(case):
    if "filename" in case:
        p = VIDEOS_DIR / case["filename"]
        if p.is_file():
            return p
    if "pattern" in case:
        matches = list(VIDEOS_DIR.glob(case["pattern"]))
        if matches:
            return matches[0]
    return None

def evaluate_project():
    print("======================================================================")
    print("AI SAFETYGUARD: FULL PIPELINE ACCURACY & CCTV EVALUATION SUITE")
    print("======================================================================")
    
    clf = ThreatClassifier.load()
    print(f"Loaded Trained Model: {clf.classifier_type} (Calibrated Threshold: {clf.threshold})")

    results_table = []
    
    tp = 0
    tn = 0
    fp = 0
    fn = 0

    cctv_tp, cctv_tn, cctv_fp, cctv_fn = 0, 0, 0, 0
    real_tp, real_tn, real_fp, real_fn = 0, 0, 0, 0

    for case in BENCHMARK_CASES:
        cid = case["id"]
        cname = case["name"]
        cat = case["category"]
        gt = case["ground_truth_label"]
        vpath = resolve_video_file(case)

        if not vpath or not vpath.is_file():
            print(f"[-] {cid}: File not found, skipping...")
            continue

        print(f"\nEvaluating [{cid}] {cname} ({vpath.name[:35]}...)")
        t0 = time.time()

        # 1. Video analysis with cut suppression
        v_df, meta = extract_video_features(vpath)

        # 2. Audio analysis
        wav_path = AUDIO_DIR / f"{vpath.stem}.wav"
        a_df = compute_acoustic_features(wav_path) if wav_path.is_file() else pd.DataFrame()
        trans, alerts = transcribe_and_detect_distress(wav_path, allow_cloud_service=False) if wav_path.is_file() else ([], [])

        # 3. Multimodal assembly & ML inference
        feat_df = assemble_multimodal_features(v_df, a_df, alerts)
        inference_df = clf.predict_dataframe(feat_df)

        # 4. Multimodal assessment & temporal consistency
        assessment = assess_multimodal_incidents(
            inference_df,
            transcripts=trans,
            distress_alerts=alerts,
            min_confidence=0.45,
            sensitivity="balanced",
        )

        elapsed = round(time.time() - t0, 2)
        summary = assessment["summary"]
        incidents = assessment["incidents"]
        inc_count = summary["incident_count"]
        high_pri_count = summary["high_priority_count"]
        med_pri_count = summary["medium_priority_count"]

        # Prediction: 1 if any incident flagged, 0 if no incident
        predicted_label = 1 if inc_count > 0 else 0

        # Classification outcome
        if gt == 1 and predicted_label == 1:
            outcome = "TP"  # True Positive (Threat correctly detected)
            tp += 1
            if "CCTV" in cat: cctv_tp += 1
            else: real_tp += 1
        elif gt == 0 and predicted_label == 0:
            outcome = "TN"  # True Negative (Normal video correctly passed)
            tn += 1
            if "CCTV" in cat: cctv_tn += 1
            else: real_tn += 1
        elif gt == 0 and predicted_label == 1:
            outcome = "FP"  # False Positive (False Alarm on normal video)
            fp += 1
            if "CCTV" in cat: cctv_fp += 1
            else: real_fp += 1
        else:
            outcome = "FN"  # False Negative (Threat missed)
            fn += 1
            if "CCTV" in cat: cctv_fn += 1
            else: real_fn += 1

        print(f"  Outcome: {outcome} | GT: {gt} | Pred: {predicted_label} | Incidents: {inc_count} (High: {high_pri_count}, Med: {med_pri_count}) in {elapsed}s")
        for inc in incidents:
            print(f"    - [{inc['severity'].upper()}] {inc['start_seconds']:.1f}s-{inc['end_seconds']:.1f}s: {inc['reasons'][:2]}")

        results_table.append({
            "case_id": cid,
            "case_name": cname,
            "category": cat,
            "filename": vpath.name,
            "duration_seconds": meta.get("duration", 0),
            "ground_truth": gt,
            "predicted": predicted_label,
            "outcome": outcome,
            "incident_count": inc_count,
            "high_priority_count": high_pri_count,
            "medium_priority_count": med_pri_count,
            "processing_seconds": elapsed,
            "incidents_detected": [
                {
                    "severity": inc["severity"],
                    "interval": f"{inc['start_seconds']:.1f}s - {inc['end_seconds']:.1f}s",
                    "reasons": inc["reasons"]
                }
                for inc in incidents
            ]
        })

    # Metrics calculation helper
    def calc_metrics(t_p, t_n, f_p, f_n):
        total = t_p + t_n + f_p + f_n
        if total == 0:
            return {}
        acc = (t_p + t_n) / total
        prec = t_p / (t_p + f_p) if (t_p + f_p) > 0 else 0.0
        rec = t_p / (t_p + f_n) if (t_p + f_n) > 0 else 0.0
        spec = t_n / (t_n + f_p) if (t_n + f_p) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        fpr = f_p / (f_p + t_n) if (f_p + t_n) > 0 else 0.0
        return {
            "total_samples": total,
            "true_positives": t_p,
            "true_negatives": t_n,
            "false_positives": f_p,
            "false_negatives": f_n,
            "accuracy": round(acc * 100, 2),
            "precision": round(prec * 100, 2),
            "recall_sensitivity": round(rec * 100, 2),
            "specificity": round(spec * 100, 2),
            "f1_score": round(f1 * 100, 2),
            "false_alarm_rate": round(fpr * 100, 2),
        }

    overall_metrics = calc_metrics(tp, tn, fp, fn)
    cctv_metrics = calc_metrics(cctv_tp, cctv_tn, cctv_fp, cctv_fn)
    real_metrics = calc_metrics(real_tp, real_tn, real_fp, real_fn)

    final_report = {
        "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model_version": "AI-SafetyGuard v1.2 (Farneback + SceneCut + Multimodal RF)",
        "overall_metrics": overall_metrics,
        "cctv_metrics": cctv_metrics,
        "real_world_metrics": real_metrics,
        "test_results": results_table,
    }

    report_path = OUTPUTS_DIR / "evaluation_accuracy_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    print("\n======================================================================")
    print("FINAL ACCURACY REPORT SUMMARY")
    print("======================================================================")
    print(f"Total Videos Evaluated: {overall_metrics['total_samples']}")
    print(f"Overall Accuracy:       {overall_metrics['accuracy']}%")
    print(f"Precision:              {overall_metrics['precision']}%")
    print(f"Recall (Sensitivity):   {overall_metrics['recall_sensitivity']}%")
    print(f"Specificity:            {overall_metrics['specificity']}%")
    print(f"F1-Score:               {overall_metrics['f1_score']}%")
    print(f"False Alarm Rate (FPR): {overall_metrics['false_alarm_rate']}%")
    print("----------------------------------------------------------------------")
    print(f"CCTV Sub-Score Accuracy: {cctv_metrics.get('accuracy')}% (TP: {cctv_tp}, TN: {cctv_tn}, FP: {cctv_fp}, FN: {cctv_fn})")
    print(f"Real-World Sub-Score:    {real_metrics.get('accuracy')}% (TP: {real_tp}, TN: {real_tn}, FP: {real_fp}, FN: {real_fn})")
    print(f"Saved JSON report to: {report_path}")

if __name__ == "__main__":
    evaluate_project()
