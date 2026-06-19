from fastapi import APIRouter
from app.ingestion.scheduler import scheduler_state, ingest_syslog, ingest_process_logs, ingest_security_events
from app.ingestion.es_client import get_es_client

router = APIRouter()

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
    stats = {}
    try:
        stats["syslog"] = await ingest_syslog(es)
        stats["process"] = await ingest_process_logs(es)
        stats["security"] = await ingest_security_events(es)
        
        # Update scheduler state
        import time
        from datetime import datetime
        total = sum(stats.values())
        scheduler_state["last_run"] = datetime.utcnow().isoformat()
        scheduler_state["docs_last_cycle"] = total
        
        return {"status": "completed", "docs_ingested": total, "details": stats}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
