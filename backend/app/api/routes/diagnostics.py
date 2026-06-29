import os
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.ingestion.kibana_client import KibanaProxyClient
from app.ingestion.log_fetcher import fetch_logs

router = APIRouter()

@router.get("/kibana-health")
async def kibana_health():
    kibana_client = KibanaProxyClient()
    start_time = time.time()
    connected = await kibana_client.check_connection()
    latency_ms = (time.time() - start_time) * 1000.0
    return {
        "connected": connected,
        "kibana_url": kibana_client.base_url,
        "latency_ms": round(latency_ms, 2),
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }

@router.get("/index-stats")
async def index_stats():
    kibana_client = KibanaProxyClient()
    indices = [
        "logs-system.syslog-*",
        "logs-endpoint.events.process-*",
        "logs-windows.powershell_operational-*"
    ]
    results = {}
    for idx in indices:
        query = {
            "size": 0,
            "track_total_hits": True,
            "query": {"match_all": {}}
        }
        try:
            resp = await kibana_client.search(index=idx, body=query)
            doc_count = resp.get("hits", {}).get("total", {}).get("value", 0)
            results[idx] = {"doc_count": doc_count, "reachable": True}
        except Exception:
            results[idx] = {"doc_count": 0, "reachable": False}
    return results

@router.get("/data-freshness")
async def data_freshness():
    kibana_client = KibanaProxyClient()
    indices = {
        "network": "logs-system.syslog-*",
        "process": "logs-endpoint.events.process-*",
        "security_alert": "logs-windows.powershell_operational-*"
    }
    results = {}
    for key, idx in indices.items():
        query = {
            "size": 1,
            "sort": [{"@timestamp": {"order": "desc"}}],
            "query": {"match_all": {}}
        }
        try:
            resp = await kibana_client.search(index=idx, body=query)
            hits = resp.get("hits", {}).get("hits", [])
            if hits:
                results[key] = hits[0]["_source"].get("@timestamp")
            else:
                results[key] = None
        except Exception:
            results[key] = None
    return results

@router.get("/local-db-stats")
async def local_db_stats():
    import aiosqlite
    alerts = 0
    open_alerts = 0
    feedback = 0
    feature_vectors = 0
    
    if os.path.exists(settings.DB_PATH):
        try:
            async with aiosqlite.connect(settings.DB_PATH) as db:
                async with db.execute("SELECT COUNT(*) FROM soc_alerts") as cur:
                    row = await cur.fetchone()
                    alerts = row[0] if row else 0
                async with db.execute("SELECT COUNT(*) FROM soc_alerts WHERE alert_status = 'open'") as cur:
                    row = await cur.fetchone()
                    open_alerts = row[0] if row else 0
                async with db.execute("SELECT COUNT(*) FROM soc_feedback") as cur:
                    row = await cur.fetchone()
                    feedback = row[0] if row else 0
                async with db.execute("SELECT COUNT(*) FROM soc_features") as cur:
                    row = await cur.fetchone()
                    feature_vectors = row[0] if row else 0
        except Exception:
            pass
            
    return {
        "alerts": alerts,
        "open_alerts": open_alerts,
        "feedback": feedback,
        "feature_vectors": feature_vectors,
        "db_path": settings.DB_PATH
    }

class FetchRequest(BaseModel):
    index: str
    since_minutes: int

@router.post("/test-fetch")
async def test_fetch(req: FetchRequest):
    kibana_client = KibanaProxyClient()
    try:
        logs = await fetch_logs(kibana_client, req.index, req.since_minutes)
        return {
            "doc_count": len(logs),
            "sample": logs[0] if logs else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
