from fastapi import APIRouter, Depends, HTTPException
from app.auth.jwt import require_role
from app.ingestion.es_client import get_es_client
from app.monitoring.sla_tracker import sla_tracker_instance
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_sla_dashboard():
    try:
        es = await get_es_client()
        dashboard = await sla_tracker_instance.get_sla_dashboard(es)
        return dashboard
    except Exception as e:
        logger.error(f"Error fetching SLA dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch SLA dashboard")

@router.get("/alerts/{alert_id}", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_sla_for_alert(alert_id: str):
    try:
        es = await get_es_client()
        resp = await es.get(index="soc-alerts", id=alert_id, ignore=[404])
        if not resp or not resp.get("found"):
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert = resp["_source"]
        status = sla_tracker_instance.compute_sla_status(alert)
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching SLA for alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch SLA status")

@router.get("/approaching-breach", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_approaching_breach(warning_minutes: int = 10):
    try:
        es = await get_es_client()
        alerts = await sla_tracker_instance.get_alerts_approaching_sla(es, warning_minutes=warning_minutes)
        return alerts
    except Exception as e:
        logger.error(f"Error fetching alerts approaching breach: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts approaching breach")
