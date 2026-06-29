import time

import psutil
from fastapi import APIRouter, HTTPException

from app.health.checker import HealthChecker
from app.ingestion.kibana_client import KibanaProxyClient
from app.models.model_manager import get_model_manager

router = APIRouter()
checker = HealthChecker()

# Cache state for deep health
last_deep_health_time = 0
cached_deep_health = None

@router.get("", response_model=dict, summary="Liveness Probe", description="Returns health check status.")
async def liveness():
    import os
    from app.config import settings
    kibana_client = KibanaProxyClient()
    return {
        "status": "ok", 
        "version": "1.0.0",
        "kibana_connected": await kibana_client.check_connection(),
        "sqlite_ready": os.path.exists(settings.DB_PATH)
    }

@router.get("/ready", summary="Readiness Probe")
async def readiness():
    try:
        es = KibanaProxyClient()
        await es.info()
    except Exception:
        raise HTTPException(status_code=503, detail="Elasticsearch not connected.")

    mm = get_model_manager()
    if len(mm.models) == 0:
        raise HTTPException(status_code=503, detail="No ML models loaded.")

    return {"status": "ready"}

@router.get("/deep", summary="Deep Health Check")
async def deep_health():
    global last_deep_health_time, cached_deep_health

    current_time = time.time()
    if cached_deep_health and current_time - last_deep_health_time < 30:
        return cached_deep_health

    report = await checker.run_all_checks()
    cached_deep_health = report
    last_deep_health_time = current_time

    return report

@router.get("/metrics", summary="System Resource Metrics")
async def system_metrics():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Process uptime
    p = psutil.Process()
    uptime = time.time() - p.create_time()

    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": mem.percent,
        "memory_used_mb": mem.used / (1024 * 1024),
        "disk_percent": disk.percent,
        "process_uptime_seconds": uptime
    }
