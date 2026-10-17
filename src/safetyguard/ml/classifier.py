"""ML model definition, training, persistence, and inference."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from safetyguard.config import MODELS_DIR
from safetyguard.ml.features import FEATURE_COLUMNS

logger = logging.getLogger(__name__)

DEFAULT_MODEL_FILE = MODELS_DIR / "safetyguard_rf_v1.joblib"
DEFAULT_METADATA_FILE = MODELS_DIR / "safetyguard_rf_v1_meta.json"


class ThreatClassifier:
    """Scikit-Learn classifier for window-level potential threat identification."""

    def __init__(
        self,
        classifier_type: str = "random_forest",
        threshold: float = 0.5,
        random_state: int = 42,
    ):
        self.classifier_type = classifier_type
        self.threshold = threshold
        self.random_state = random_state
        self.feature_columns = list(FEATURE_COLUMNS)
        self.model: Optional[Pipeline] = None
        self.metadata: Dict[str, Any] = {}

    def _build_pipeline(self) -> Pipeline:
        if self.classifier_type == "logistic_regression":
            clf = LogisticRegression(
                class_weight="balanced",
                max_iter=1000,
                random_state=self.random_state,
            )
        else:
            clf = RandomForestClassifier(
                n_estimators=100,
                max_depth=8,
                min_samples_split=4,
                class_weight="balanced",
                random_state=self.random_state,
            )

        return Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", clf),
        ])

    def fit(self, train_df: pd.DataFrame, val_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Fit model on training dataframe and calibrate threshold on validation data."""
        X_train = train_df[self.feature_columns].values
        y_train = train_df["label"].values.astype(int)

        self.model = self._build_pipeline()
        self.model.fit(X_train, y_train)

        # Tune threshold if validation set provided
        best_threshold = self.threshold
        best_f1 = 0.0

        if val_df is not None and not val_df.empty:
            X_val = val_df[self.feature_columns].values
            y_val = val_df["label"].values.astype(int)
            val_probs = self.model.predict_proba(X_val)[:, 1]

            # Find threshold optimizing F1 on validation set
            for th in np.arange(0.3, 0.75, 0.05):
                preds = (val_probs >= th).astype(int)
                tp = np.sum((preds == 1) & (y_val == 1))
                fp = np.sum((preds == 1) & (y_val == 0))
                fn = np.sum((preds == 0) & (y_val == 1))
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

                if f1 > best_f1:
                    best_f1 = f1
                    best_threshold = float(th)

        self.threshold = best_threshold

        self.metadata = {
            "version": "1.0.0",
            "classifier_type": self.classifier_type,
            "trained_at": datetime.now().isoformat(),
            "n_samples": len(train_df),
            "n_features": len(self.feature_columns),
            "feature_columns": self.feature_columns,
            "calibrated_threshold": round(self.threshold, 3),
            "validation_f1_calibrated": round(best_f1, 4) if val_df is not None else None,
        }

        return self.metadata

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return probability of potential incident [P(normal), P(potential_incident)]."""
        if self.model is None:
            raise RuntimeError("Model has not been trained or loaded yet.")
        features = X[self.feature_columns].values
        return self.model.predict_proba(features)

    def predict_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add prediction probabilities and binary decisions to a features DataFrame."""
        if self.model is None:
            # Fallback heuristic if model not available
            result = df.copy()
            result["model_threat_probability"] = 0.0
            result["model_flagged"] = False
            return result

        result = df.copy()
        probs = self.predict_proba(result)[:, 1]
        result["model_threat_probability"] = np.round(probs, 3)
        result["model_flagged"] = (probs >= self.threshold)
        return result

    def save(
        self,
        model_path: Optional[Path] = None,
        meta_path: Optional[Path] = None,
    ) -> Tuple[Path, Path]:
        """Save model and metadata to disk."""
        target_model = model_path or DEFAULT_MODEL_FILE
        target_meta = meta_path or DEFAULT_METADATA_FILE

        target_model.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, target_model)

        with open(target_meta, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        logger.info("Saved model to %s and metadata to %s", target_model, target_meta)
        return target_model, target_meta

    @classmethod
    def load(
        cls,
        model_path: Optional[Path] = None,
        meta_path: Optional[Path] = None,
    ) -> "ThreatClassifier":
        """Load saved model and metadata from disk."""
        target_model = model_path or DEFAULT_MODEL_FILE
        target_meta = meta_path or DEFAULT_METADATA_FILE

        if not target_model.is_file():
            raise FileNotFoundError(f"Model file not found: {target_model}")

        meta = {}
        if target_meta.is_file():
            with open(target_meta, "r", encoding="utf-8") as f:
                meta = json.load(f)

        classifier_type = meta.get("classifier_type", "random_forest")
        threshold = meta.get("calibrated_threshold", 0.5)

        instance = cls(classifier_type=classifier_type, threshold=threshold)
        instance.model = joblib.load(target_model)
        instance.metadata = meta
        return instance


_global_classifier: Optional[ThreatClassifier] = None


def get_default_classifier() -> ThreatClassifier:
    """Get singleton or lazily trained default classifier."""
    global _global_classifier
    if _global_classifier is not None:
        return _global_classifier

    if DEFAULT_MODEL_FILE.is_file():
        try:
            _global_classifier = ThreatClassifier.load()
            return _global_classifier
        except Exception as err:
            logger.warning("Could not load saved model, retraining: %s", err)

    # Train default model on benchmark dataset
    from safetyguard.ml.dataset import load_dataset_with_group_split

    train_df, val_df, _ = load_dataset_with_group_split()
    clf = ThreatClassifier(classifier_type="random_forest")
    clf.fit(train_df, val_df)
    clf.save()
    _global_classifier = clf
    return _global_classifier
