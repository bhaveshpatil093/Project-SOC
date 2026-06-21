import time
import uuid
from datetime import datetime

import numpy as np

from app.api.routes.websocket import manager
from app.ingestion.es_client import INDEX_NAMES
from app.logging_config import get_logger
from app.models.model_manager import get_model_manager

logger = get_logger(__name__)

class DriftDetector:
    def __init__(self, reference_window_size: int = 1000, drift_threshold: float = 0.1):
        self.reference_window_size = reference_window_size
        self.drift_threshold = drift_threshold
        self.reference_stats = {}
        self.last_retrain_time = None

    async def load_reference_stats(self, es):
        try:
            res = await es.get(index="soc-drift-reference", id="latest", ignore_unavailable=True)
            if res and "_source" in res:
                self.reference_stats = res["_source"].get("stats", {})
                logger.info("drift_reference_loaded", features=len(self.reference_stats))
        except Exception as e:
            logger.warning("drift_reference_load_failed", error=str(e))

    async def save_reference_stats(self, es):
        try:
            doc = {
                "stats": self.reference_stats,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            await es.index(index="soc-drift-reference", id="latest", document=doc)
            logger.info("drift_reference_saved")
        except Exception as e:
            logger.error("drift_reference_save_failed", error=str(e))

    async def set_reference_distribution(self, X_train: np.ndarray, feature_names: list[str], es):
        self.reference_stats = {}
        for i, f_name in enumerate(feature_names):
            col = X_train[:, i]
            try:
                bins = np.percentile(col, np.linspace(0, 100, 11))
                bins = np.unique(bins)
                if len(bins) < 2:
                    bins = np.array([col.min() - 0.01, col.max() + 0.01])

                expected_pct = np.zeros(len(bins) - 1)
                for b in range(len(bins) - 1):
                    if b == 0:
                        count = np.sum(col <= bins[b+1])
                    elif b == len(bins) - 2:
                        count = np.sum(col > bins[b])
                    else:
                        count = np.sum((col > bins[b]) & (col <= bins[b+1]))
                    expected_pct[b] = count

                expected_pct = expected_pct / len(col)
                expected_pct = np.where(expected_pct == 0, 0.0001, expected_pct)

                self.reference_stats[f_name] = {
                    "mean": float(np.mean(col)),
                    "std": float(np.std(col)),
                    "bins": bins.tolist(),
                    "expected_pct": expected_pct.tolist()
                }
            except Exception as e:
                logger.error("drift_binning_failed", feature=f_name, error=str(e))

        await self.save_reference_stats(es)

    def compute_drift_score(self, X_current: np.ndarray, feature_names: list[str]) -> dict:
        if not self.reference_stats:
            return {"overall_drift_score": 0.0, "feature_scores": {}}

        feature_scores = {}
        valid_psi_scores = []

        for i, f_name in enumerate(feature_names):
            if f_name not in self.reference_stats:
                continue

            col = X_current[:, i]
            ref = self.reference_stats[f_name]
            bins = ref["bins"]
            expected_pct = np.array(ref["expected_pct"])

            actual_pct = np.zeros(len(expected_pct))
            for b in range(len(expected_pct)):
                if b == 0:
                    count = np.sum(col <= bins[b+1])
                elif b == len(expected_pct) - 1:
                    count = np.sum(col > bins[b])
                else:
                    count = np.sum((col > bins[b]) & (col <= bins[b+1]))
                actual_pct[b] = count

            actual_pct = actual_pct / len(col)
            actual_pct = np.where(actual_pct == 0, 0.0001, actual_pct)

            psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
            feature_scores[f_name] = float(psi)
            valid_psi_scores.append(psi)

        overall = float(np.mean(valid_psi_scores)) if valid_psi_scores else 0.0

        return {
            "overall_drift_score": overall,
            "feature_scores": feature_scores
        }

    def detect_anomaly_score_drift(self, recent_scores: list[float]) -> dict:
        if not recent_scores:
            return {"mean_shift": 0.0, "is_drifted": False, "recommendation": "Not enough data"}

        recent_mean = float(np.mean(recent_scores))

        if recent_mean > 0.3:
            return {"mean_shift": recent_mean, "is_drifted": True, "recommendation": "High anomaly scores observed. Check if real attack or false positive drift."}

        return {"mean_shift": recent_mean, "is_drifted": False, "recommendation": "Scores normal"}

    async def run_drift_check(self, es) -> dict:
        logger.info("drift_check_started")

        if not self.reference_stats:
            await self.load_reference_stats(es)

        if not self.reference_stats:
            logger.warning("drift_check_skipped_no_reference")
            return {"status": "skipped", "reason": "No reference distribution available"}

        query = {
            "query": {"match_all": {}},
            "sort": [{"timestamp": "desc"}],
            "size": 500
        }

        try:
            res = await es.search(index=INDEX_NAMES["features"], body=query, ignore_unavailable=True)
            hits = res.get("hits", {}).get("hits", [])

            if not hits:
                return {"status": "skipped", "reason": "No recent features found"}

            feature_dicts = [h["_source"]["features"] for h in hits if "features" in h["_source"]]
            if not feature_dicts:
                return {"status": "skipped", "reason": "No feature vectors in recent docs"}

            feature_names = list(feature_dicts[0].keys())
            X_current = np.array([[fd.get(k, 0) for k in feature_names] for fd in feature_dicts])

            drift_res = self.compute_drift_score(X_current, feature_names)
            overall = drift_res["overall_drift_score"]
            feature_scores = drift_res["feature_scores"]

            top_drifted = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            top_features = [{"name": k, "psi": v} for k, v in top_drifted]

            status = "No Drift"
            if overall > 0.2:
                status = "Significant Drift"
            elif overall > 0.1:
                status = "Slight Drift"

            report = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "overall_drift_score": overall,
                "status": status,
                "top_drifted_features": top_features,
                "feature_scores": feature_scores
            }

            await es.index(index="soc-drift-log", document=report)

            await manager.broadcast({
                "type": "drift_update",
                "data": report
            })

            if overall > 0.2:
                logger.warning("significant_drift_detected", psi=overall)

                now = time.time()
                cooldown_hours = 24

                if self.last_retrain_time is None or (now - self.last_retrain_time) > (cooldown_hours * 3600):
                    logger.info(f"Auto-retraining triggered due to feature drift: PSI={overall:.2f}")
                    mm = get_model_manager()

                    import asyncio
                    asyncio.create_task(run_incremental_retraining(es, mm, job_id=str(uuid.uuid4())))
                    self.last_retrain_time = now
                else:
                    logger.info("drift_retraining_cooldown_active")

            return report

        except Exception as e:
            logger.error("drift_check_failed", error=str(e))
            return {"status": "error", "error": str(e)}

_drift_detector = DriftDetector()

def get_drift_detector():
    return _drift_detector
