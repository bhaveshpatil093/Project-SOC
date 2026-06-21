import logging
import os
import uuid
from datetime import datetime

import mlflow
import pandas as pd

from app.cache.cache_manager import cache_result
from app.config import settings
from app.features.feature_merger import run_feature_pipeline
from app.models.drift_detector import get_drift_detector
from app.models.model_manager import ModelManager

logger = logging.getLogger(__name__)

# In-memory mapping resolving background task execution bounds natively
TRAINING_JOBS = {}

async def run_initial_training(es, model_manager: ModelManager, job_id: str = None) -> dict:
    """Extracts historical telemetry mapping massive analytical bounds bootstrapping isolated models explicitly tracking natively."""
    if not job_id:
        job_id = str(uuid.uuid4())

    TRAINING_JOBS[job_id] = {"status": "started", "start_time": datetime.utcnow().isoformat() + "Z"}
    logger.info(f"Starting ML initial training execution cycle. Job ID: {job_id}")

    try:
        # Fetch exact last 7 days of raw analytical limits mapping heavily (7 days * 24 hours * 60 minutes)
        minutes_7_days = 7 * 24 * 60
        feature_df, normalized_df = await run_feature_pipeline(es, since_minutes=minutes_7_days)

        if feature_df.empty:
            TRAINING_JOBS[job_id]["status"] = "failed - no baseline data available"
            return {"job_id": job_id, "status": "failed", "reason": "No feature data available natively in ES indices."}

        # Forces parallel distributed executions exactly across model structures spanning natively on ModelManager
        await model_manager.train_all_models(feature_df, normalized_df)

        # Set drift detector reference distribution
        import numpy as np
        drift_detector = get_drift_detector()
        numeric_df = feature_df.select_dtypes(include=[np.number]).fillna(0)
        if not numeric_df.empty:
            feature_names = numeric_df.columns.tolist()
            X_train = numeric_df.values
            await drift_detector.set_reference_distribution(X_train, feature_names, es)

        TRAINING_JOBS[job_id]["status"] = "completed"
        TRAINING_JOBS[job_id]["end_time"] = datetime.utcnow().isoformat() + "Z"

        logger.info(f"ML baseline training complete natively successfully. Tracked entities: {len(feature_df)}")
        return {"job_id": job_id, "status": "completed", "entities_scored": len(feature_df)}

    except Exception as e:
        logger.error(f"Error in ML initial training cycle: {e}")
        TRAINING_JOBS[job_id]["status"] = f"failed - {str(e)}"
        return {"job_id": job_id, "status": "failed", "reason": str(e)}

async def run_incremental_retraining(es, model_manager: ModelManager, job_id: str = None) -> dict:
    """Isolates targeted True Positive limits executing Deep Learning fine-tuning seamlessly atop established embedding spaces."""
    if not job_id:
        job_id = str(uuid.uuid4())

    TRAINING_JOBS[job_id] = {"status": "started_retraining", "start_time": datetime.utcnow().isoformat() + "Z"}
    logger.info(f"Starting ML incremental retraining limits natively. Job ID: {job_id}")

    try:
        # Fetch labeled TP contextual inputs natively
        from app.feedback.label_store import get_all_feedback
        tp_feedback = await get_all_feedback(es, label="TP", limit=1000)

        # Load exactly 24 hours mapping baseline arrays incrementally bounding natively
        feature_df, normalized_df = await run_feature_pipeline(es, since_minutes=1440)

        if feature_df.empty:
            TRAINING_JOBS[job_id]["status"] = "failed - no incremental baseline data"
            return {"job_id": job_id, "status": "failed", "reason": "No feature data available natively for fine-tuning."}

        from app.models.autoencoder import PROCESS_FEATURE_COLS
        from app.models.isolation_forest import train_isolation_forest

        # Retrain IsolationForest explicitly parsing massive anomaly shifts natively bounding across boundaries
        logger.info("Executing IF total analytical retraining arrays natively...")
        model_manager.if_detector = train_isolation_forest(feature_df)

        # Fine-tune Process Execution Autoencoder
        logger.info("Executing Deep Learning Autoencoder fine-tuning (20 Epoch constraints)...")
        if model_manager.ae_detector and model_manager.proc_scaler:
            from app.features.feature_merger import scale_features

            X = feature_df[PROCESS_FEATURE_COLS].fillna(0).values
            X_scaled = scale_features(X, model_manager.proc_scaler)

            mlflow.set_experiment("soc-anomaly-detection")
            with mlflow.start_run(run_name="ae_finetune_cycle"):
                # Execute mapped learning rate exactly tracking fine-tuning limit bounds
                model_manager.ae_detector.train(X_scaled, epochs=20, lr=1e-4)
                model_path = os.path.join(settings.MODEL_DIR, "autoencoder.pt")
                model_manager.ae_detector.save(model_path)
                mlflow.log_param("cycle", "finetune")
        else:
            from app.models.autoencoder import train_autoencoder
            model_manager.ae_detector = train_autoencoder(feature_df)

        TRAINING_JOBS[job_id]["status"] = "completed"
        TRAINING_JOBS[job_id]["end_time"] = datetime.utcnow().isoformat() + "Z"

        return {"job_id": job_id, "status": "completed"}

    except Exception as e:
        logger.error(f"Error executing explicit ML incremental fine-tuning constraints: {e}")
        TRAINING_JOBS[job_id]["status"] = f"failed - {str(e)}"
        return {"job_id": job_id, "status": "failed", "reason": str(e)}

@cache_result(ttl_seconds=600)
async def get_model_versions() -> list[dict]:
    """Retrieves standard MLFlow experimental states securely natively directly exposing backend artifacts onto REST mappings."""
    try:
        mlflow.set_experiment("soc-anomaly-detection")
        experiment = mlflow.get_experiment_by_name("soc-anomaly-detection")
        if not experiment:
            return []

        runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
        if runs.empty:
            return []

        versions = []
        for _, row in runs.iterrows():
            # Translate scalar definitions extracting parameters implicitly mapping pandas bounds
            params = {k.replace('params.', ''): v for k, v in row.items() if k.startswith('params.') and pd.notna(v)}
            metrics = {k.replace('metrics.', ''): v for k, v in row.items() if k.startswith('metrics.') and pd.notna(v)}

            versions.append({
                "run_id": row["run_id"],
                "status": row["status"],
                "timestamp": str(row["start_time"]),
                "params": params,
                "metrics": metrics
            })

        return versions
    except Exception as e:
        logger.error(f"Error accessing MLFlow artifact states natively: {e}")
        return []

async def train_calibrator(es, model_manager) -> dict:
    import mlflow
    import numpy as np

    from app.feedback.label_store import get_all_feedback
    from app.models.calibrator import ScoreCalibrator

    logger.info("Starting Score Calibrator training...")
    try:
        feedback = await get_all_feedback(es, limit=10000)

        # In a real system, we would query the historical raw scores.
        # But for this simulation, we'll try to extract them if they are in the feedback notes
        # or we might just use some heuristics if we don't have them explicitly joined in feedback.
        # Actually, let's query the alerts matching the feedback alert_ids.

        alert_ids = [fb["alert_id"] for fb in feedback if fb["alert_id"]]
        if not alert_ids:
            return {"status": "skipped", "reason": "No feedback available."}

        # Fetch the original alerts
        query = {
            "size": len(alert_ids),
            "query": {
                "ids": {
                    "values": alert_ids
                }
            }
        }
        res = await es.search(index="soc-processed-alerts", body=query, ignore_unavailable=True)
        alerts_map = {hit["_id"]: hit["_source"] for hit in res.get("hits", {}).get("hits", [])}

        raw_scores = []
        labels = []

        for fb in feedback:
            aid = fb["alert_id"]
            if aid in alerts_map:
                alert = alerts_map[aid]
                raw_score = alert.get("raw_threat_score", alert.get("threat_score", 0.5))
                label_val = 1 if fb["label"] == "TP" else 0  # FP and Benign are 0

                raw_scores.append(raw_score)
                labels.append(label_val)

        if len(raw_scores) < 50:
            logger.info(f"Skipping calibration. Need 50 labeled samples, found {len(raw_scores)}")
            return {"status": "skipped", "reason": f"Need 50 labeled samples, found {len(raw_scores)}"}

        calibrator = ScoreCalibrator()
        stats = calibrator.fit(np.array(raw_scores), np.array(labels))

        calibrator_path = os.path.join(settings.MODEL_DIR, "calibrator.pkl")
        calibrator.save(calibrator_path)

        # Load it into the model manager
        model_manager.calibrator = calibrator

        mlflow.set_experiment("SOC_Ensemble_Calibration")
        with mlflow.start_run(run_name="Calibrator_Update"):
            mlflow.log_params({"method": stats["method"], "n_samples": stats["n_samples_used"]})
            mlflow.log_metrics({"brier_score": stats["brier_score"], "auc_roc": stats["auc_roc"]})

        return {"status": "success", "stats": stats}

    except Exception as e:
        logger.error(f"Error training calibrator: {e}")
        return {"status": "error", "error": str(e)}
