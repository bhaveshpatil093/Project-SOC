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
