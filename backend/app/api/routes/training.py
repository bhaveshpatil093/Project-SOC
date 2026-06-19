import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict, Any

from app.models.trainer import run_initial_training, run_incremental_retraining, get_model_versions, TRAINING_JOBS
from app.ingestion.es_client import get_es_client
from app.models.model_manager import get_model_manager
from app.auth.jwt import require_role
from fastapi import Depends, Request
from app.middleware.rate_limiter import limiter

router = APIRouter()

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
    history = get_model_versions()
    return {"versions": history}
