"""Tests for dataset generation, group-splitting, model training, and evaluation."""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from safetyguard.ml.dataset import generate_benchmark_dataset, load_dataset_with_group_split
from safetyguard.ml.classifier import ThreatClassifier
from safetyguard.ml.evaluation import evaluate_classifier


def test_group_split_prevents_leakage(tmp_path):
    """Verify that video_ids in train and test sets do NOT overlap."""
    ds_path = tmp_path / "test_ds.csv"
    generate_benchmark_dataset(output_path=ds_path, num_videos=16, windows_per_video=10)

    train_df, val_df, test_df = load_dataset_with_group_split(
        dataset_path=ds_path,
        test_size=0.25,
        val_size=0.25,
    )

    train_videos = set(train_df["video_id"].unique())
    val_videos = set(val_df["video_id"].unique())
    test_videos = set(test_df["video_id"].unique())

    # Strict disjointness
    assert train_videos.isdisjoint(test_videos), "Data leakage detected: video_id shared between train and test!"
    assert train_videos.isdisjoint(val_videos), "Data leakage detected: video_id shared between train and val!"
    assert val_videos.isdisjoint(test_videos), "Data leakage detected: video_id shared between val and test!"


def test_classifier_fit_predict_save_load(tmp_path):
    """Verify classifier training, calibrated threshold, prediction, and persistence."""
    ds_path = tmp_path / "test_ds.csv"
    generate_benchmark_dataset(output_path=ds_path, num_videos=20, windows_per_video=15)

    train_df, val_df, test_df = load_dataset_with_group_split(dataset_path=ds_path)

    clf = ThreatClassifier(classifier_type="random_forest")
    meta = clf.fit(train_df, val_df)

    assert "calibrated_threshold" in meta
    assert clf.threshold > 0.0

    # Predictions
    pred_df = clf.predict_dataframe(test_df)
    assert "model_threat_probability" in pred_df.columns
    assert "model_flagged" in pred_df.columns
    assert pred_df["model_threat_probability"].min() >= 0.0
    assert pred_df["model_threat_probability"].max() <= 1.0

    # Persistence roundtrip
    model_file = tmp_path / "model.joblib"
    meta_file = tmp_path / "meta.json"
    clf.save(model_file, meta_file)

    loaded = ThreatClassifier.load(model_file, meta_file)
    loaded_preds = loaded.predict_dataframe(test_df)
    np.testing.assert_array_almost_equal(
        pred_df["model_threat_probability"].values,
        loaded_preds["model_threat_probability"].values
    )


def test_evaluation_metrics(tmp_path):
    """Verify comprehensive evaluation metrics computation."""
    ds_path = tmp_path / "test_ds.csv"
    generate_benchmark_dataset(output_path=ds_path, num_videos=20, windows_per_video=15)
    train_df, val_df, test_df = load_dataset_with_group_split(dataset_path=ds_path)

    clf = ThreatClassifier(classifier_type="random_forest")
    clf.fit(train_df, val_df)

    report = evaluate_classifier(clf, test_df)

    assert "metrics" in report
    assert "precision" in report["metrics"]
    assert "recall" in report["metrics"]
    assert "f1_score" in report["metrics"]
    assert "confusion_matrix" in report
    assert "operational_diagnostics" in report
    assert report["operational_diagnostics"]["latency_per_window_ms"] > 0
