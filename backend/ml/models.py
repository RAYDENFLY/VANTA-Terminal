"""
VANTA Terminal — Pre-Registered Model Arena & Wrappers
======================================================
Implements the 3 pre-registered supervised ML candidate model families specified in
docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md (Section 5):
1. MODEL-1-LOGIT: Regularized Logistic Regression (L2, C=0.1, solver='lbfgs')
2. MODEL-2-LGBM:  LightGBM (max_depth=4, num_leaves=15, min_child_samples=50, subsample=0.8, colsample=0.8)
3. MODEL-3-XGB:   XGBoost (max_depth=4, min_child_weight=50, subsample=0.8, colsample=0.8)

Invariants:
- Fixed random seed = 42.
- Balanced class weighting.
- CPU execution with n_jobs=4.
- Deterministic, reproducible training.
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier


class MLModelWrapper:
    """
    Unified wrapper for multiclass classifiers predicting {-1, 0, 1}.
    """

    def __init__(self, model_id: str):
        self.model_id = model_id
        self.classes_ = np.array([-1, 0, 1])

        if model_id == "MODEL-1-LOGIT":
            self.model = LogisticRegression(
                penalty="l2",
                C=0.1,
                solver="lbfgs",
                max_iter=1000,
                random_state=42,
                class_weight="balanced"
            )
            self._is_xgb = False

        elif model_id == "MODEL-2-LGBM":
            self.model = LGBMClassifier(
                max_depth=4,
                num_leaves=15,
                min_child_samples=50,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                learning_rate=0.03,
                n_estimators=300,
                random_state=42,
                class_weight="balanced",
                n_jobs=4,
                verbose=-1
            )
            self._is_xgb = False

        elif model_id == "MODEL-3-XGB":
            self.model = XGBClassifier(
                max_depth=4,
                min_child_weight=50,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                learning_rate=0.03,
                n_estimators=300,
                random_state=42,
                n_jobs=4,
                eval_metric="mlogloss"
            )
            self._is_xgb = True
        else:
            raise ValueError(f"Unknown model_id: {model_id}")

    def fit(self, X_train: np.ndarray, y_train: np.ndarray) -> "MLModelWrapper":
        """
        Fits the underlying classifier on In-Sample training observations.
        """
        if self._is_xgb:
            # Map labels {-1, 0, 1} -> {0, 1, 2} for XGBoost
            y_mapped = y_train + 1
            sample_weights = compute_sample_weight("balanced", y_mapped)
            self.model.fit(X_train, y_mapped, sample_weight=sample_weights)
        else:
            self.model.fit(X_train, y_train)

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predicts discrete target labels in {-1, 0, 1}.
        """
        raw_pred = self.model.predict(X)
        if self._is_xgb:
            # Map back {0, 1, 2} -> {-1, 0, 1}
            return (raw_pred - 1).astype(int)
        return raw_pred.astype(int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predicts class probabilities aligned to classes [-1, 0, 1].
        """
        probs = self.model.predict_proba(X)
        # Ensure ordering corresponds strictly to [-1, 0, 1]
        if hasattr(self.model, "classes_") and not self._is_xgb:
            model_classes = self.model.classes_
            if list(model_classes) != [-1, 0, 1]:
                aligned = np.zeros((len(X), 3), dtype=np.float64)
                for i, c in enumerate([-1, 0, 1]):
                    if c in model_classes:
                        idx = list(model_classes).index(c)
                        aligned[:, i] = probs[:, idx]
                return aligned
        return probs

    def evaluate_diagnostics(self, X: np.ndarray, y_true: np.ndarray) -> Dict[str, Any]:
        """
        Computes classification metrics for informational and diagnostic reporting.
        """
        # Drop NaN targets if any
        valid_mask = ~np.isnan(y_true)
        if not valid_mask.any():
            return {}

        X_val = X[valid_mask]
        y_val = y_true[valid_mask].astype(int)

        y_pred = self.predict(X_val)
        y_prob = self.predict_proba(X_val)

        acc = float(accuracy_score(y_val, y_pred))
        b_acc = float(balanced_accuracy_score(y_val, y_pred))

        # Multiclass Brier score: mean squared probability error across all 3 classes
        y_one_hot = np.zeros((len(y_val), 3), dtype=np.float64)
        for i, c in enumerate([-1, 0, 1]):
            y_one_hot[:, i] = (y_val == c).astype(float)
        brier_score = float(np.mean(np.sum((y_prob - y_one_hot) ** 2, axis=1)))

        cm = confusion_matrix(y_val, y_pred, labels=[-1, 0, 1]).tolist()

        return {
            "accuracy": round(acc, 4),
            "balanced_accuracy": round(b_acc, 4),
            "brier_score": round(brier_score, 4),
            "confusion_matrix": cm,
            "class_distribution_true": {
                "-1": int((y_val == -1).sum()),
                "0": int((y_val == 0).sum()),
                "1": int((y_val == 1).sum()),
            },
            "class_distribution_pred": {
                "-1": int((y_pred == -1).sum()),
                "0": int((y_pred == 0).sum()),
                "1": int((y_pred == 1).sum()),
            }
        }
