from fastapi import APIRouter
from app.ingestion.scheduler import scheduler_state

router = APIRouter()

@router.get("/api/ingestion/status")
def get_ingestion_status():
    """Returns the live in-memory state of the ingestion scheduler."""
    return {
        "last_run": scheduler_state["last_run"],
        "docs_last_cycle": scheduler_state["docs_last_cycle"],
        "status": scheduler_state["status"]
    }
