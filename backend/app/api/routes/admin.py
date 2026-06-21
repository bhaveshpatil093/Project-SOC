from fastapi import APIRouter, Depends, HTTPException
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
