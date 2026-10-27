"""
VANTA Terminal — Pre-Registered Meta-Model Wrappers (Phase 5D.1)
================================================================
Implements strictly-typed, reproducible binary meta-classification models:
- META-1-LOGIT: L2 Regularized Logistic Regression
- META-2-LGBM: Shallow LightGBM Classifier (max_depth=3, num_leaves=7, n_est=150)
- META-3-XGB: Shallow XGBoost Classifier (max_depth=3, min_child_weight=50, n_est=150)

Key Invariants:
1. No Initialization Fitting: Models are never fitted upon import or instantiation.
2. Explicit Training Invariant: Fit occurs strictly on caller-supplied (X, y) matrices.
3. Feature Schema Enforcement: Dimension and feature ordering are strictly verified against
   REGISTERED_FEATURE_NAMES (21 features).
4. Deterministic Single-Class Handling: Folds with a single target class raise SingleClassPartitionError.
5. Standardized Probability Interface: predict_proba_positive(X) returns a 1D float array in [0.0, 1.0].
6. Calibration Integrity: Raw model sigmoid/logistic probabilities are provided without claiming
   unfitted post-hoc calibration (e.g. Platt or Isotonic).
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from abc import ABC, abstractmethod
import numpy as np
from sklearn.linear_model import LogisticRegression
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier

from backend.ml.features import REGISTERED_FEATURE_NAMES


class SingleClassPartitionError(ValueError):
    """Raised when a training fold contains only a single class."""
    pass


class ModelNotFittedError(RuntimeError):
    """Raised when prediction is attempted on an unfitted model."""
    pass


class FeatureDimensionMismatchError(ValueError):
    """Raised when input feature dimension differs from registered schema."""
    pass


class BaseMetaModel(ABC):
    """Abstract base class for all pre-registered Phase 5D meta-classifiers."""

    def __init__(self, model_id: str, model_name: str, config: Dict[str, Any]):
        self.model_id = model_id
        self.model_name = model_name
        self.config = config
        self.is_fitted: bool = False
        self.n_features_in_: Optional[int] = None
        self.classes_: Optional[np.ndarray] = None
        self.underlying_model: Any = None

    @abstractmethod
    def _create_underlying_model(self) -> Any:
        """Instantiates the underlying library model with frozen hyperparameters."""
        pass

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None
    ) -> "BaseMetaModel":
        """
        Fits the meta-classifier strictly on caller-provided training data.
        
        Validations:
        - X must be a 2D float array with exactly 21 columns.
        - y must be a 1D binary integer array with both classes {0, 1} present.
        - No NaNs or infinities permitted.
        """
        if not isinstance(X, np.ndarray) or not isinstance(y, np.ndarray):
            raise TypeError("X and y must be numpy ndarrays.")

        if X.ndim != 2:
            raise ValueError(f"X must be 2-dimensional. Got shape {X.shape}.")
        if y.ndim != 1:
            raise ValueError(f"y must be 1-dimensional. Got shape {y.shape}.")
        if len(X) != len(y):
            raise ValueError(f"Length mismatch: X has {len(X)} rows, y has {len(y)} labels.")

        if X.shape[1] != len(REGISTERED_FEATURE_NAMES):
            raise FeatureDimensionMismatchError(
                f"Feature dimension mismatch: Expected {len(REGISTERED_FEATURE_NAMES)} features, "
                f"got {X.shape[1]}."
            )

        if feature_names is not None and feature_names != REGISTERED_FEATURE_NAMES:
            raise FeatureDimensionMismatchError(
                "Supplied feature names do not match frozen REGISTERED_FEATURE_NAMES ordering."
            )

        if np.isnan(X).any() or np.isinf(X).any():
            raise ValueError("X contains NaN or infinite values.")
        if np.isnan(y).any() or np.isinf(y).any():
            raise ValueError("y contains NaN or infinite values.")

        # Single-class validation
        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            raise SingleClassPartitionError(
                f"Training partition has only single class {unique_classes.tolist()}. "
                f"Cannot train binary classifier."
            )

        self.underlying_model = self._create_underlying_model()
        self.underlying_model.fit(X, y)
        self.is_fitted = True
        self.n_features_in_ = X.shape[1]
        self.classes_ = unique_classes
        return self

    def predict_proba_positive(self, X: np.ndarray) -> np.ndarray:
        """
        Returns the predicted probability of the positive class (Class 1) as a 1D array.
        """
        if not self.is_fitted:
            raise ModelNotFittedError(f"Model {self.model_id} must be fitted before predict.")

        if not isinstance(X, np.ndarray) or X.ndim != 2 or X.shape[1] != self.n_features_in_:
            raise FeatureDimensionMismatchError(
                f"Invalid input shape {X.shape}. Expected (*, {self.n_features_in_})."
            )

        if np.isnan(X).any() or np.isinf(X).any():
            raise ValueError("Input feature matrix X contains NaN or infinite values.")

        probas = self.underlying_model.predict_proba(X)
        # Find index of class 1
        pos_idx = np.where(self.underlying_model.classes_ == 1)[0]
        if len(pos_idx) == 0:
            raise RuntimeError("Class 1 not found in fitted model classes.")
        return probas[:, pos_idx[0]].astype(np.float64)

    def predict(self, X: np.ndarray, threshold: float = 0.50) -> np.ndarray:
        """
        Returns discrete binary predictions {0, 1} based on decision threshold tau.
        """
        probs = self.predict_proba_positive(X)
        return (probs >= threshold).astype(int)

    def get_schema(self) -> Dict[str, Any]:
        """Returns reproducible model metadata and schema specification."""
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "config": self.config,
            "is_fitted": self.is_fitted,
            "expected_features_count": len(REGISTERED_FEATURE_NAMES),
            "feature_names": REGISTERED_FEATURE_NAMES,
            "probability_calibration_claimed": False
        }


class Meta1LogitModel(BaseMetaModel):
    """
    META-1-LOGIT: Regularized Logistic Regression meta-classifier.
    Pre-registered configuration: L2 penalty, C=1.0, L-BFGS solver.
    """

    def __init__(self, c_val: float = 1.0, random_state: int = 42):
        config = {
            "penalty": "l2",
            "C": c_val,
            "solver": "lbfgs",
            "max_iter": 1000,
            "random_state": random_state
        }
        super().__init__(
            model_id="META-1-LOGIT",
            model_name="L2 Regularized Logistic Regression",
            config=config
        )

    def _create_underlying_model(self) -> Any:
        return LogisticRegression(**self.config)


class Meta2LGBMModel(BaseMetaModel):
    """
    META-2-LGBM: Shallow LightGBM meta-classifier.
    Pre-registered configuration: max_depth=3, num_leaves=7, n_estimators=150,
    learning_rate=0.05, min_child_samples=50.
    """

    def __init__(
        self,
        max_depth: int = 3,
        num_leaves: int = 7,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        min_child_samples: int = 50,
        random_state: int = 42
    ):
        config = {
            "max_depth": max_depth,
            "num_leaves": num_leaves,
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "min_child_samples": min_child_samples,
            "random_state": random_state,
            "verbose": -1,
            "n_jobs": 1
        }
        super().__init__(
            model_id="META-2-LGBM",
            model_name="Shallow LightGBM Meta-Classifier",
            config=config
        )

    def _create_underlying_model(self) -> Any:
        return LGBMClassifier(**self.config)


class Meta3XGBModel(BaseMetaModel):
    """
    META-3-XGB: Shallow XGBoost meta-classifier.
    Pre-registered configuration: max_depth=3, n_estimators=150, learning_rate=0.05,
    min_child_weight=50.
    """

    def __init__(
        self,
        max_depth: int = 3,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        min_child_weight: float = 50.0,
        random_state: int = 42
    ):
        config = {
            "max_depth": max_depth,
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "min_child_weight": min_child_weight,
            "random_state": random_state,
            "eval_metric": "logloss",
            "n_jobs": 1
        }
        super().__init__(
            model_id="META-3-XGB",
            model_name="Shallow XGBoost Meta-Classifier",
            config=config
        )

    def _create_underlying_model(self) -> Any:
        return XGBClassifier(**self.config)


def create_meta_model(model_id: str) -> BaseMetaModel:
    """Factory creating an unfitted meta-model instance from frozen ID."""
    mid = model_id.upper()
    if mid in ["META-1", "META-1-LOGIT", "LOGIT"]:
        return Meta1LogitModel()
    elif mid in ["META-2", "META-2-LGBM", "LGBM"]:
        return Meta2LGBMModel()
    elif mid in ["META-3", "META-3-XGB", "XGB"]:
        return Meta3XGBModel()
    else:
        raise ValueError(f"Unknown meta-model ID: {model_id}. Expected META-1-LOGIT, META-2-LGBM, or META-3-XGB.")
