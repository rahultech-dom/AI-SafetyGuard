"""Model evaluation metrics, confusion matrix, and reporting."""

import logging
import time
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    confusion_matrix,
    roc_auc_score,
    classification_report,
)

from safetyguard.ml.classifier import ThreatClassifier
from safetyguard.ml.dataset import load_dataset_with_group_split

logger = logging.getLogger(__name__)


def evaluate_classifier(
    classifier: ThreatClassifier,
    test_df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Evaluate classifier performance on an independent, video-grouped test dataset.
    Computes precision, recall, F1, confusion matrix, latency, and false positive metrics.
    """
    feature_cols = classifier.feature_columns
    X_test = test_df[feature_cols].values
    y_test = test_df["label"].values.astype(int)

    start_time = time.perf_counter()
    probs = classifier.predict_proba(test_df)[:, 1]
    elapsed = time.perf_counter() - start_time

    latency_per_sample_ms = (elapsed / max(1, len(test_df))) * 1000.0
    preds = (probs >= classifier.threshold).astype(int)

    cm = confusion_matrix(y_test, preds, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    # Total test hours represented
    total_test_seconds = len(test_df)
    total_test_hours = max(0.001, total_test_seconds / 3600.0)
    false_positives_per_hour = round(fp / total_test_hours, 2)

    try:
        auc = float(roc_auc_score(y_test, probs))
    except Exception:
        auc = 0.5

    precision = float(precision_score(y_test, preds, zero_division=0))
    recall = float(recall_score(y_test, preds, zero_division=0))
    f1 = float(f1_score(y_test, preds, zero_division=0))
    accuracy = float(accuracy_score(y_test, preds))

    report = {
        "model_type": classifier.classifier_type,
        "calibrated_threshold": classifier.threshold,
        "test_samples": int(len(test_df)),
        "test_distinct_videos": int(test_df["video_id"].nunique()),
        "label_distribution": {
            "normal_windows": int(np.sum(y_test == 0)),
            "incident_windows": int(np.sum(y_test == 1)),
        },
        "metrics": {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(auc, 4),
        },
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
        "operational_diagnostics": {
            "false_positives_per_hour": false_positives_per_hour,
            "latency_per_window_ms": round(latency_per_sample_ms, 2),
            "total_test_hours": round(total_test_hours, 3),
        },
        "per_category_breakdown": {},
    }

    if "video_category" in test_df.columns:
        for cat in test_df["video_category"].unique():
            cat_mask = test_df["video_category"] == cat
            sub_y = y_test[cat_mask]
            sub_preds = preds[cat_mask]
            report["per_category_breakdown"][cat] = {
                "count": int(np.sum(cat_mask)),
                "flagged_count": int(np.sum(sub_preds == 1)),
                "accuracy": round(float(accuracy_score(sub_y, sub_preds)), 3),
            }

    return report


def run_full_pipeline_evaluation() -> Dict[str, Any]:
    """Train on train set, calibrate on val set, and test on independent video-grouped test set."""
    train_df, val_df, test_df = load_dataset_with_group_split()

    clf = ThreatClassifier(classifier_type="random_forest")
    clf.fit(train_df, val_df)
    results = evaluate_classifier(clf, test_df)
    return results
