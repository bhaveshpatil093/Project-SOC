import uuid
import json
import aiosqlite

from app.monitoring.audit_logger import audit_action
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.auth.jwt import require_role
from app.ingestion.kibana_client import KibanaProxyClient
from app.middleware.rate_limiter import limiter
from app.models.interpretability import InterpretabilityReporter
from app.models.model_manager import get_model_manager
from app.models.trainer import (
    get_model_versions,
    run_incremental_retraining,
    run_initial_training,
)
from app.storage import local_db
from app.config import settings

router = APIRouter()
reporter = InterpretabilityReporter()

@router.post("/initial", dependencies=[Depends(require_role("admin"))])
@limiter.limit("5/minute")
async def trigger_initial_training(request: Request, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    kibana_client = KibanaProxyClient()
    mm = get_model_manager()

    background_tasks.add_task(run_initial_training, kibana_client, mm, settings.DB_PATH, job_id)
    return {"job_id": job_id, "status": "started"}

@router.post("/incremental", dependencies=[Depends(require_role("admin", "analyst"))])
@limiter.limit("5/minute")
async def trigger_incremental_retraining(request: Request, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    kibana_client = KibanaProxyClient()
    mm = get_model_manager()

    background_tasks.add_task(run_incremental_retraining, kibana_client, mm, settings.DB_PATH, job_id)
    return {"job_id": job_id, "status": "started"}

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    job = await local_db.get_training_job(settings.DB_PATH, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found in SQLite.")
    return {"job_id": job_id, **job}

@router.get("/status", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_training_status():
    history = await get_model_versions()
    return {"versions": history}

@router.get("/history", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_training_history():
    mlflow_runs = await get_model_versions()
    
    sqlite_jobs = []
    try:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM soc_training_jobs ORDER BY started_at DESC LIMIT 50")
            rows = await cursor.fetchall()
            for r in rows:
                d = dict(r)
                if d.get("summary"):
                    try:
                        d["summary"] = json.loads(d["summary"])
                    except:
                        pass
                sqlite_jobs.append(d)
    except Exception:
        pass
        
    return {"mlflow": mlflow_runs, "sqlite_jobs": sqlite_jobs}

@router.get("/drift", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_drift_status():
    kibana_client = KibanaProxyClient()
    query = {
        "query": {"match_all": {}},
        "sort": [{"timestamp": "desc"}],
        "size": 1
    }
    try:
        res = await kibana_client.search(index="soc-drift-log", body=query)
        hits = res.get("hits", {}).get("hits", [])
        if hits:
            return hits[0]["_source"]
        return {"status": "No Drift", "overall_drift_score": 0, "top_drifted_features": []}
    except Exception as e:
        return {"status": "Unknown", "overall_drift_score": 0, "error": str(e), "top_drifted_features": []}


@router.get("/interpretability", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_interpretability_report():
    kibana_client = KibanaProxyClient()
    manager = get_model_manager()
    report = await reporter.generate_full_report(kibana_client, manager)
    return {"data": report}

from app.models.accuracy_evaluator import AccuracyEvaluator
from cachetools import TTLCache

accuracy_cache = TTLCache(maxsize=10, ttl=3600)

@router.get("/accuracy", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_accuracy_report():
    cache_key = "latest_accuracy_report"
    if cache_key in accuracy_cache:
        return {"data": accuracy_cache[cache_key]}
        
    try:
        kibana_client = KibanaProxyClient()
        manager = get_model_manager()
        evaluator = AccuracyEvaluator()
        report = await evaluator.evaluate_against_feedback(kibana_client, manager)
        
        import dataclasses
        report_dict = dataclasses.asdict(report)
        accuracy_cache[cache_key] = report_dict
        return {"data": report_dict}
    except ValueError as e:
        if "Insufficient data" in str(e):
            return {"error": "insufficient data", "message": str(e)}
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel

class ThresholdUpdate(BaseModel):
    threshold: float

@router.post("/threshold", dependencies=[Depends(require_role("admin"))])
async def update_threshold(payload: ThresholdUpdate):
    return {"status": "success", "threshold": payload.threshold}

# --- MLflow Endpoints ---

from mlflow.tracking import MlflowClient

@router.get("/mlflow/experiments", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def list_experiments():
    client = MlflowClient()
    experiments = client.search_experiments()
    return [
        {
            "experiment_id": exp.experiment_id,
            "name": exp.name,
            "artifact_location": exp.artifact_location,
            "lifecycle_stage": exp.lifecycle_stage
        }
        for exp in experiments
    ]

@router.get("/mlflow/runs/{experiment_id}", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def list_runs(experiment_id: str):
    client = MlflowClient()
    runs = client.search_runs(experiment_ids=[experiment_id])
    return [
        {
            "run_id": run.info.run_id,
            "status": run.info.status,
            "start_time": run.info.start_time,
            "end_time": run.info.end_time,
            "metrics": run.data.metrics,
            "params": run.data.params,
            "tags": run.data.tags
        }
        for run in runs
    ]

@router.get("/mlflow/runs/detail/{run_id}", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_run_details(run_id: str):
    client = MlflowClient()
    run = client.get_run(run_id)

    metric_history = {}
    for key in run.data.metrics.keys():
        try:
            history = client.get_metric_history(run_id, key)
            metric_history[key] = [{"step": h.step, "value": h.value, "timestamp": h.timestamp} for h in history]
        except:
            pass

    return {
        "run_id": run.info.run_id,
        "status": run.info.status,
        "start_time": run.info.start_time,
        "end_time": run.info.end_time,
        "metrics": run.data.metrics,
        "params": run.data.params,
        "tags": run.data.tags,
        "metric_history": metric_history
    }

@router.get("/mlflow/compare", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def compare_runs(run_ids: str):
    ids = [i.strip() for i in run_ids.split(",") if i.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="No run IDs provided")

    client = MlflowClient()
    runs = []
    for rid in ids:
        try:
            run = client.get_run(rid)

            loss_history = []
            try:
                hist = client.get_metric_history(rid, "loss")
                loss_history = [{"step": h.step, "value": h.value} for h in hist]
            except:
                pass

            runs.append({
                "run_id": run.info.run_id,
                "name": run.data.tags.get("mlflow.runName", run.info.run_id[:8]),
                "status": run.info.status,
                "metrics": run.data.metrics,
                "params": run.data.params,
                "loss_history": loss_history
            })
        except:
            continue

    return {"runs": runs}

@router.get("/calibration", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_calibration_stats():
    manager = get_model_manager()
    if manager.calibrator:
        stats = manager.calibrator.get_calibration_stats()
        return {"data": stats}
    return {"data": {"is_calibrated": False}}

@router.post("/calibration", dependencies=[Depends(require_role("admin", "analyst"))])
async def trigger_calibration_training():
    kibana_client = KibanaProxyClient()
    manager = get_model_manager()
    from app.models.trainer import train_calibrator
    res = await train_calibrator(kibana_client, manager, settings.DB_PATH)
    return res
