"""
VANTA Terminal — Partition-Aware Feature Scaling (Phase 5B)
===========================================================
Enforces strict In-Sample fitting isolation for feature scalers.
Guarantees that Out-of-Sample evaluation data is strictly transformed using
pre-fitted In-Sample statistics (median, IQR) and never fitted directly.
"""

from typing import Dict, Any, Optional, List, Union
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler


class PartitionAwareScaler:
    """
    RobustScaler wrapper with explicit partition guard and outlier clipping.
    """

    def __init__(self, clip_min: float = -5.0, clip_max: float = 5.0):
        self.scaler = RobustScaler(with_centering=True, with_scaling=True, unit_variance=False)
        self.clip_min = clip_min
        self.clip_max = clip_max
        self.is_fitted = False
        self.feature_names: List[str] = []

    def fit(self, X_train: Union[pd.DataFrame, np.ndarray], partition: str = "IS") -> "PartitionAwareScaler":
        """
        Fits the scaler strictly on the In-Sample training slice.
        Raises ValueError if partition is not In-Sample ("IS").
        """
        if partition.upper() != "IS":
            raise ValueError(
                f"CRITICAL PROTOCOL VIOLATION: PartitionAwareScaler may only be fitted on In-Sample ('IS') partition. "
                f"Attempted to fit on '{partition}'."
            )

        if isinstance(X_train, pd.DataFrame):
            self.feature_names = list(X_train.columns)
            values = X_train.values
        else:
            values = X_train

        # Drop any NaN rows before fitting
        valid_mask = ~np.isnan(values).any(axis=1)
        valid_values = values[valid_mask]

        if len(valid_values) == 0:
            raise ValueError("Cannot fit scaler on empty or entirely NaN training matrix.")

        self.scaler.fit(valid_values)
        self.is_fitted = True
        return self

    def transform(self, X: Union[pd.DataFrame, np.ndarray], partition: Optional[str] = None) -> np.ndarray:
        """
        Transforms features using pre-fitted training statistics and clips to [-5.0, 5.0].
        Raises RuntimeError if transform is called before fit.
        Raises ValueError if partition is Holdout.
        """
        if partition is not None and partition.upper() in ["HOLDOUT", "HOLD_OUT"]:
            raise ValueError("CRITICAL PROTOCOL VIOLATION: Cannot transform Holdout data during research phase.")

        if not self.is_fitted:
            raise RuntimeError(
                "CRITICAL PROTOCOL VIOLATION: Attempted to transform data using an unfitted scaler. "
                "Scaler must be fitted strictly on In-Sample training partition first."
            )

        if isinstance(X, pd.DataFrame):
            values = X.values
        else:
            values = X

        scaled = self.scaler.transform(values)
        # Apply outlier clipping
        clipped = np.clip(scaled, self.clip_min, self.clip_max)
        return clipped

    def fit_transform(self, X_train: Union[pd.DataFrame, np.ndarray], partition: str = "IS") -> np.ndarray:
        """
        Convenience method permitted ONLY on training partition.
        """
        self.fit(X_train, partition=partition)
        return self.transform(X_train, partition=partition)

    def get_params_dict(self) -> Dict[str, Any]:
        """
        Returns fitted medians and scales for audit verification.
        """
        if not self.is_fitted:
            return {"fitted": False}
        return {
            "fitted": True,
            "center": self.scaler.center_.tolist() if hasattr(self.scaler, "center_") else [],
            "scale": self.scaler.scale_.tolist() if hasattr(self.scaler, "scale_") else [],
            "clip_range": [self.clip_min, self.clip_max],
            "feature_names": self.feature_names
        }
