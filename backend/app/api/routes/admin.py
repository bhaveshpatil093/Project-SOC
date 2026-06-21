from app.monitoring.audit_logger import audit_action
from fastapi import APIRouter, Depends, Query

from app.monitoring.log_viewer import log_viewer_instance
from typing import Optional
, HTTPException
from typing import Any

from app.auth.jwt import require_role
from app.ingestion.es_client import get_es_client
from app.migrations.migration_runner import MigrationRunner

router = APIRouter()

@router.get("/migrations", dependencies=[Depends(require_role("admin"))])
async def get_migrations_status() -> dict[str, Any]:
    """Returns the current status of all Elasticsearch index migrations."""
    es = await get_es_client()
    runner = MigrationRunner()
    
    try:
        status = await runner.status(es)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch migration status: {e}")

from pydantic import BaseModel
from app.backup.backup_manager import BackupManager

class RestoreRequest(BaseModel):
    target_indices: list[str] | None = None

@router.get("/backups", dependencies=[Depends(require_role("admin"))])
async def list_backups() -> list[dict[str, Any]]:
    es = await get_es_client()
    bm = BackupManager(es)
    return await bm.list_snapshots()

@router.post("/backups", dependencies=[Depends(require_role("admin"))])
async def create_backup() -> dict[str, Any]:
    es = await get_es_client()
    bm = BackupManager(es)
    try:
        return await bm.create_snapshot()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backups/{name}", dependencies=[Depends(require_role("admin"))])
async def get_backup_details(name: str) -> dict[str, Any]:
    es = await get_es_client()
    bm = BackupManager(es)
    snaps = await bm.list_snapshots()
    for s in snaps:
        if s["snapshot_name"] == name:
            size = await bm.get_snapshot_size(name)
            s["size_bytes"] = size
            return s
    raise HTTPException(status_code=404, detail="Snapshot not found")

@router.post("/backups/{name}/restore", dependencies=[Depends(require_role("admin"))])
async def restore_backup(name: str, req: RestoreRequest) -> dict[str, Any]:
    es = await get_es_client()
    bm = BackupManager(es)
    try:
        return await bm.restore_snapshot(name, target_indices=req.target_indices)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/backups/{name}", dependencies=[Depends(require_role("admin"))])
async def delete_backup(name: str) -> dict[str, Any]:
    es = await get_es_client()
    bm = BackupManager(es)
    try:
        await bm.es.snapshot.delete(repository=bm.repo_name, snapshot=name)
        return {"status": "success", "deleted": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs", dependencies=[Depends(require_role("admin"))])
async def get_logs(
    level: Optional[str] = None,
    component: Optional[str] = None,
    since_minutes: int = Query(60, ge=1),
    limit: int = Query(100, le=1000)
):
    try:
        es = await get_es_client()
        logs = await log_viewer_instance.get_recent_logs(es, level, component, since_minutes, limit)
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch logs")

@router.get("/logs/errors", dependencies=[Depends(require_role("admin"))])
async def get_log_errors(since_hours: int = Query(24, ge=1)):
    try:
        es = await get_es_client()
        summary = await log_viewer_instance.get_error_summary(es, since_hours)
        return {"error_summary": summary}
    except Exception as e:
        logger.error(f"Error fetching log errors: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch log errors")

@router.get("/logs/search", dependencies=[Depends(require_role("admin"))])
async def search_logs(q: str, since_hours: int = Query(24, ge=1), limit: int = Query(100, le=1000)):
    try:
        es = await get_es_client()
        logs = await log_viewer_instance.search_logs(es, q, since_hours, limit)
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error searching logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to search logs")

@router.get("/logs/trace/{correlation_id}", dependencies=[Depends(require_role("admin"))])
async def get_log_trace(correlation_id: str):
    try:
        es = await get_es_client()
        trace = await log_viewer_instance.get_correlation_trace(es, correlation_id)
        return {"trace": trace}
    except Exception as e:
        logger.error(f"Error fetching log trace: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch log trace")
