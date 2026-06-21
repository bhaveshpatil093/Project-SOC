import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict, Any

from app.models.trainer import run_initial_training, run_incremental_retraining, get_model_versions, TRAINING_JOBS
from app.models.interpretability import InterpretabilityReporter
from app.ingestion.es_client import get_es_client
from app.models.model_manager import get_model_manager
from app.auth.jwt import require_role
from fastapi import Depends, Request
from app.middleware.rate_limiter import limiter

router = APIRouter()
reporter = InterpretabilityReporter()

@router.post("/initial", dependencies=[Depends(require_role("admin"))])
@limiter.limit("5/minute")
async def trigger_initial_training(request: Request, background_tasks: BackgroundTasks):
    """Triggers complete baseline ML training pipeline executing arrays synchronously asynchronously in background routines."""
    job_id = str(uuid.uuid4())
    es = await get_es_client()
    mm = get_model_manager()
    
    background_tasks.add_task(run_initial_training, es, mm, job_id)
    return {"job_id": job_id, "status": "started"}

@router.post("/incremental", dependencies=[Depends(require_role("admin", "analyst"))])
@limiter.limit("5/minute")
async def trigger_incremental_retraining(request: Request, background_tasks: BackgroundTasks):
    """Executes incremental bounds retraining overlapping existing artifacts mapping new specific explicit feature vectors."""
    job_id = str(uuid.uuid4())
    es = await get_es_client()
    mm = get_model_manager()
    
    background_tasks.add_task(run_incremental_retraining, es, mm, job_id)
    return {"job_id": job_id, "status": "started"}

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Retrieves ephemeral background ML training job contexts safely tracking local execution metrics."""
    if job_id not in TRAINING_JOBS:
        raise HTTPException(status_code=404, detail="Training job explicit artifact not found natively.")
    return {"job_id": job_id, **TRAINING_JOBS[job_id]}

@router.get("/status", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_training_status():
    """Generates complete model versioning mapping cleanly leveraging underlying MLFlow experiment log pipelines."""
    history = await get_model_versions()
    return {"versions": history}

@router.get("/drift", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_drift_status():
    """Returns the latest model drift report."""
    es = await get_es_client()
    query = {
        "query": {"match_all": {}},
        "sort": [{"timestamp": "desc"}],
        "size": 1
    }
    try:
        res = await es.search(index="soc-drift-log", body=query, ignore_unavailable=True)
        hits = res.get("hits", {}).get("hits", [])
        if hits:
            return hits[0]["_source"]
        return {"status": "No Drift", "overall_drift_score": 0, "top_drifted_features": []}
    except Exception as e:
        return {"status": "Unknown", "overall_drift_score": 0, "error": str(e), "top_drifted_features": []}


@router.get("/interpretability", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_interpretability_report():
    es = await get_es_client()
    manager = get_model_manager()
    report = await reporter.generate_full_report(es, manager)
    return {"data": report}

# --- MLflow Endpoints ---

import mlflow
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
    
    # Try to fetch metric history if possible
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
            
            # Fetch history for loss if available
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
    """Returns calibration stats, AUC-ROC, Brier score, n_samples"""
    manager = get_model_manager()
    if manager.calibrator:
        stats = manager.calibrator.get_calibration_stats()
        return {"data": stats}
    return {"data": {"is_calibrated": False}}

@router.post("/calibration", dependencies=[Depends(require_role("admin", "analyst"))])
async def trigger_calibration_training():
    """Manually trigger calibration training"""
    es = await get_es_client()
    manager = get_model_manager()
    from app.models.trainer import train_calibrator
    res = await train_calibrator(es, manager)
    return res
