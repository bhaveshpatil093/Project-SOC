from fastapi import APIRouter
from app.ingestion.scheduler import scheduler_state, run_ingestion_cycle
from app.ingestion.es_client import get_es_client
from app.auth.jwt import require_role
from fastapi import Depends

router = APIRouter(dependencies=[Depends(require_role("admin", "analyst"))])

@router.get("/status")
def get_ingestion_status():
    """Returns the live in-memory state of the ingestion scheduler."""
    return {
        "last_run": scheduler_state["last_run"],
        "docs_last_cycle": scheduler_state["docs_last_cycle"],
        "status": scheduler_state["status"]
    }

@router.post("/run")
async def trigger_ingestion_cycle():
    """Manually triggers the ingestion pipeline synchronously."""
    es = await get_es_client()
    try:
        await run_ingestion_cycle(es)
        return {"status": "completed", "details": "Ingestion cycle executed"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
