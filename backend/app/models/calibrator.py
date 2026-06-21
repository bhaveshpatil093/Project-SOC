import logging
import os
import pickle
from datetime import datetime

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

logger = logging.getLogger(__name__)

class ScoreCalibrator:
    def __init__(self):
        self.method = None
        self.calibrator = None
        self.brier_score = None
        self.auc_roc = None
        self.n_samples_used = 0
        self.fitted_at = None

    def fit(self, raw_scores: np.ndarray, labels: np.ndarray) -> dict:
        """
        Fits Platt scaling and Isotonic regression. Chooses the better one based on Brier score.
        labels: 1 = Malicious, 0 = Benign
        """
        if len(raw_scores) < 50:
            logger.warning("Need at least 50 samples to fit calibrator.")
            return {}

        X = raw_scores.reshape(-1, 1)
        y = labels

        # Try Platt Scaling (Logistic Regression)
        lr = LogisticRegression()
        lr.fit(X, y)
        lr_preds = lr.predict_proba(X)[:, 1]
        lr_brier = brier_score_loss(y, lr_preds)

        # Try Isotonic Regression
        iso = IsotonicRegression(out_of_bounds='clip')
        iso.fit(raw_scores, y)
        iso_preds = iso.predict(raw_scores)
        iso_brier = brier_score_loss(y, iso_preds)

        if iso_brier < lr_brier:
            self.method = "isotonic"
            self.calibrator = iso
            self.brier_score = iso_brier
            preds = iso_preds
        else:
            self.method = "platt"
            self.calibrator = lr
            self.brier_score = lr_brier
            preds = lr_preds

        try:
            self.auc_roc = roc_auc_score(y, preds)
        except ValueError:
            self.auc_roc = 0.5  # Handle case with only one class

        self.n_samples_used = len(raw_scores)
        self.fitted_at = datetime.utcnow().isoformat() + "Z"

        return {
            "method": self.method,
            "brier_score": float(self.brier_score),
            "auc_roc": float(self.auc_roc),
            "n_samples_used": self.n_samples_used
        }

    def calibrate(self, raw_score: float) -> float:
        if not self.is_fitted():
            return raw_score

        if self.method == "isotonic":
            return float(self.calibrator.predict([raw_score])[0])
        return float(self.calibrator.predict_proba([[raw_score]])[0, 1])

    def calibrate_batch(self, raw_scores: np.ndarray) -> np.ndarray:
        if not self.is_fitted():
            return raw_scores

        if self.method == "isotonic":
            return self.calibrator.predict(raw_scores)
        return self.calibrator.predict_proba(raw_scores.reshape(-1, 1))[:, 1]

    def is_fitted(self) -> bool:
        return self.calibrator is not None and self.n_samples_used >= 50

    def get_calibration_stats(self) -> dict:
        return {
            "method": self.method,
            "brier_score": self.brier_score,
            "auc_roc": self.auc_roc,
            "n_samples_used": self.n_samples_used,
            "fitted_at": self.fitted_at,
            "is_calibrated": self.is_fitted()
        }

    def save(self, path: str):
        if self.is_fitted():
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                pickle.dump(self, f)
            logger.info(f"Saved calibrator to {path}")

    @classmethod
    def load(cls, path: str) -> "ScoreCalibrator":
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Failed to load calibrator from {path}: {e}")
        return cls()
