import os
import uuid
import json
from datetime import datetime

import mlflow
import pandas as pd
import numpy as np

from app.cache.cache_manager import cache_result
from app.config import settings
from app.features.feature_merger import run_feature_pipeline
from app.models.drift_detector import get_drift_detector
from app.models.model_manager import ModelManager
from app.storage import local_db
from app.ingestion.kibana_client import KibanaProxyClient

from app.logging_config import get_logger
logger = get_logger(__name__)

async def run_initial_training(kibana_client: KibanaProxyClient, model_manager: ModelManager, db_path: str, job_id: str = None) -> dict:
    if not job_id:
        job_id = str(uuid.uuid4())

    job_record = {
        "job_id": job_id,
        "job_type": "initial",
        "status": "started",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "finished_at": None,
        "summary": {}
    }
    await local_db.upsert_training_job(db_path, job_record)
    logger.info(f"Starting ML initial training execution cycle. Job ID: {job_id}")

    try:
        minutes_7_days = 7 * 24 * 60
        feature_df, normalized_df = await run_feature_pipeline(kibana_client, since_minutes=minutes_7_days)

        if feature_df.empty:
            job_record["status"] = "failed - no baseline data available"
            job_record["finished_at"] = datetime.utcnow().isoformat() + "Z"
            job_record["summary"] = {"reason": "No feature data available natively in Kibana."}
            await local_db.upsert_training_job(db_path, job_record)
            return {"job_id": job_id, "status": "failed", "reason": job_record["summary"]["reason"]}

        await model_manager.train_all_models(feature_df, normalized_df)

        drift_detector = get_drift_detector()
        numeric_df = feature_df.select_dtypes(include=[np.number]).fillna(0)
        if not numeric_df.empty:
            feature_names = numeric_df.columns.tolist()
            X_train = numeric_df.values
            await drift_detector.set_reference_distribution(X_train, feature_names, kibana_client)

        job_record["status"] = "completed"
        job_record["finished_at"] = datetime.utcnow().isoformat() + "Z"
        job_record["summary"] = {"entities_scored": len(feature_df)}
        await local_db.upsert_training_job(db_path, job_record)

        logger.info(f"ML baseline training complete. Tracked entities: {len(feature_df)}")
        return {"job_id": job_id, "status": "completed", "entities_scored": len(feature_df)}

    except Exception as e:
        logger.error(f"Error in ML initial training cycle: {e}")
        job_record["status"] = f"failed - {str(e)}"
        job_record["finished_at"] = datetime.utcnow().isoformat() + "Z"
        job_record["summary"] = {"reason": str(e)}
        await local_db.upsert_training_job(db_path, job_record)
        return {"job_id": job_id, "status": "failed", "reason": str(e)}

async def run_incremental_retraining(kibana_client: KibanaProxyClient, model_manager: ModelManager, db_path: str, job_id: str = None) -> dict:
    if not job_id:
        job_id = str(uuid.uuid4())

    job_record = {
        "job_id": job_id,
        "job_type": "incremental",
        "status": "started_retraining",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "finished_at": None,
        "summary": {}
    }
    await local_db.upsert_training_job(db_path, job_record)
    logger.info(f"Starting ML incremental retraining natively. Job ID: {job_id}")

    try:
        from app.feedback.label_store import get_all_feedback
        tp_feedback = await local_db.list_feedback(db_path, label="TP", limit=1000)

        feature_df, normalized_df = await run_feature_pipeline(kibana_client, since_minutes=1440)

        tp_feature_rows = []
        for fb in tp_feedback:
            alert = await local_db.get_alert(db_path, fb.get("alert_id"))
            if alert and "raw_context" in alert:
                ctx = alert["raw_context"]
                if "shap_features" in ctx and ctx["shap_features"]:
                    row = ctx["shap_features"]
                    if isinstance(row, dict):
                        tp_feature_rows.append(row)

        if tp_feature_rows:
            tp_df = pd.DataFrame(tp_feature_rows)
            if not feature_df.empty:
                for col in feature_df.columns:
                    if col not in tp_df.columns:
                        tp_df[col] = 0
                tp_df = tp_df[feature_df.columns]
                feature_df = pd.concat([feature_df, tp_df], ignore_index=True)
            else:
                feature_df = tp_df

        if feature_df.empty:
            job_record["status"] = "failed - no incremental baseline data"
            job_record["finished_at"] = datetime.utcnow().isoformat() + "Z"
            job_record["summary"] = {"reason": "No feature data available natively for fine-tuning."}
            await local_db.upsert_training_job(db_path, job_record)
            return {"job_id": job_id, "status": "failed", "reason": job_record["summary"]["reason"]}

        from app.models.autoencoder import PROCESS_FEATURE_COLS
        from app.models.isolation_forest import train_isolation_forest

        logger.info("Executing IF total analytical retraining arrays natively...")
        model_manager.if_detector = train_isolation_forest(feature_df)

        logger.info("Executing Deep Learning Autoencoder fine-tuning (20 Epoch constraints)...")
        if model_manager.ae_detector and model_manager.proc_scaler:
            from app.features.feature_merger import scale_features

            for col in PROCESS_FEATURE_COLS:
                if col not in feature_df.columns:
                    feature_df[col] = 0

            X = feature_df[PROCESS_FEATURE_COLS].fillna(0).values
            X_scaled = scale_features(X, model_manager.proc_scaler)

            mlflow.set_experiment("soc-anomaly-detection")
            with mlflow.start_run(run_name="ae_finetune_cycle"):
                model_manager.ae_detector.train(X_scaled, epochs=20, lr=1e-4)
                model_path = os.path.join(settings.MODEL_DIR, "autoencoder.pt")
                model_manager.ae_detector.save(model_path)
                mlflow.log_param("cycle", "finetune")
        else:
            from app.models.autoencoder import train_autoencoder
            for col in PROCESS_FEATURE_COLS:
                if col not in feature_df.columns:
                    feature_df[col] = 0
            model_manager.ae_detector = train_autoencoder(feature_df)

        job_record["status"] = "completed"
        job_record["finished_at"] = datetime.utcnow().isoformat() + "Z"
        await local_db.upsert_training_job(db_path, job_record)

        return {"job_id": job_id, "status": "completed"}

    except Exception as e:
        logger.error(f"Error executing explicit ML incremental fine-tuning constraints: {e}")
        job_record["status"] = f"failed - {str(e)}"
        job_record["finished_at"] = datetime.utcnow().isoformat() + "Z"
        job_record["summary"] = {"reason": str(e)}
        await local_db.upsert_training_job(db_path, job_record)
        return {"job_id": job_id, "status": "failed", "reason": str(e)}


@cache_result(ttl_seconds=600)
async def get_model_versions() -> list[dict]:
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

async def train_calibrator(kibana_client: KibanaProxyClient, model_manager: ModelManager, db_path: str) -> dict:
    logger.info("Starting Score Calibrator training...")
    try:
        feedback = await local_db.list_feedback(db_path, limit=10000)

        alert_ids = [fb["alert_id"] for fb in feedback if fb["alert_id"]]
        if not alert_ids:
            return {"status": "skipped", "reason": "No feedback available."}

        raw_scores = []
        labels = []

        for fb in feedback:
            aid = fb["alert_id"]
            alert = await local_db.get_alert(db_path, aid)
            if alert:
                ctx = alert.get("raw_context", {})
                raw_score = ctx.get("raw_threat_score", ctx.get("threat_score", 0.5))
                label_val = 1 if fb["label"] == "TP" else 0

                raw_scores.append(raw_score)
                labels.append(label_val)

        if len(raw_scores) < 50:
            logger.info(f"Skipping calibration. Need 50 labeled samples, found {len(raw_scores)}")
            return {"status": "skipped", "reason": f"Need 50 labeled samples, found {len(raw_scores)}"}
            
        from app.models.calibrator import ScoreCalibrator
        calibrator = ScoreCalibrator()
        stats = calibrator.fit(np.array(raw_scores), np.array(labels))

        calibrator_path = os.path.join(settings.MODEL_DIR, "calibrator.pkl")
        calibrator.save(calibrator_path)

        model_manager.calibrator = calibrator

        mlflow.set_experiment("SOC_Ensemble_Calibration")
        with mlflow.start_run(run_name="Calibrator_Update"):
            mlflow.log_params({"method": stats["method"], "n_samples": stats["n_samples_used"]})
            mlflow.log_metrics({"brier_score": stats["brier_score"], "auc_roc": stats["auc_roc"]})

        return {"status": "success", "stats": stats}

    except Exception as e:
        logger.error(f"Error training calibrator: {e}")
        return {"status": "error", "error": str(e)}
