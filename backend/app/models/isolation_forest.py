import os
import joblib
import numpy as np
import pandas as pd
import logging
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

NETWORK_FEATURE_COLS = [
    "conn_per_minute",
    "unique_dst_ip_count",
    "unique_dst_port_count",
    "unique_src_port_count",
    "rare_port_flag",
    "rare_protocol_flag",
    "is_internal_to_external",
    "port_scan_score",
    "top_dst_port",
    "has_icmp",
    "has_high_port"
]

class IsolationForestDetector:
    def __init__(self, contamination=0.05, n_estimators=200, random_state=42):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state
        )

    def train(self, X: np.ndarray) -> dict:
        self.model.fit(X)
        return {
            "status": "trained",
            "n_samples": X.shape[0],
            "contamination": self.contamination
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Anomaly scores mapped dynamically to 0-1.
        Sklearn decision_function inherently binds anomaly (-1) to lower continuous values, and normal (+1) to higher values.
        We flip this scalar and normalize so that High (1.0) equates explicitly to Anomaly.
        """
        raw_scores = self.model.decision_function(X)
        # Flip scalar: Higher becomes anomalous
        flipped = -raw_scores
        # Normalization mapping spanning typical [-0.5, 0.5] range up to 0.0 - 1.0 bounding box
        norm_scores = np.clip(flipped + 0.5, 0.0, 1.0)
        return norm_scores

    def score_single(self, feature_vector: np.ndarray) -> float:
        """Predicts against a contiguous isolated 1D shape feature mapping."""
        X = feature_vector.reshape(1, -1)
        scores = self.predict(X)
        return float(scores[0])

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str) -> "IsolationForestDetector":
        return joblib.load(path)


def train_isolation_forest(feature_df: pd.DataFrame) -> IsolationForestDetector | None:
    import mlflow
    from app.features.feature_merger import fit_scaler, save_scaler, scale_features
    from app.config import settings
    
    mlflow.set_experiment("soc-anomaly-detection")
    
    with mlflow.start_run():
        if feature_df.empty:
            logger.warning("Empty dataframe provided to train_isolation_forest. Cannot train.")
            return None
            
        # Ensure mapping consistency backing up missing network dimensions
        for col in NETWORK_FEATURE_COLS:
            if col not in feature_df.columns:
                feature_df[col] = 0.0
                
        X_df = feature_df[NETWORK_FEATURE_COLS].fillna(0)
        X_raw = X_df.values
        
        # Fit independent sub-scaler
        scaler = fit_scaler(X_raw)
        X_scaled = scale_features(X_raw, scaler)
        
        scaler_path = os.path.join(settings.MODEL_DIR, "network_scaler.pkl")
        save_scaler(scaler, scaler_path)
        
        # Train ML construct
        detector = IsolationForestDetector()
        train_stats = detector.train(X_scaled)
        
        mlflow.log_params({
            "contamination": detector.contamination,
            "n_estimators": detector.model.n_estimators,
            "random_state": detector.model.random_state
        })
        mlflow.log_metrics({
            "n_samples": train_stats["n_samples"]
        })
        
        # Save artifacts locally
        model_path = os.path.join(settings.MODEL_DIR, "isolation_forest.pkl")
        detector.save(model_path)
        
        logger.info(f"Isolation Forest trained on {train_stats['n_samples']} samples and saved to {model_path}.")
        return detector

def load_or_train(feature_df: pd.DataFrame, model_path: str) -> IsolationForestDetector:
    if os.path.exists(model_path):
        logger.info(f"Loading existing Isolation Forest model from {model_path}")
        return IsolationForestDetector.load(model_path)
    else:
        logger.info(f"Model not found at {model_path}. Training fresh Isolation Forest.")
        return train_isolation_forest(feature_df)
