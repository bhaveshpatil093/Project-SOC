import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.auth.jwt import get_current_user, require_role, User
from app.ingestion.es_client import get_es_client
from app.monitoring.audit_logger import audit_logger_instance

router = APIRouter(prefix="/api/admin/audit-log", tags=["admin", "audit"])

@router.get("", dependencies=[Depends(require_role("admin"))])
async def get_audit_logs(
    user: str = Query(None),
    action: str = Query(None),
    resource_id: str = Query(None),
    since_hours: int = Query(24)
):
    es = await get_es_client()
    events = await audit_logger_instance.get_audit_trail(
        es=es, user=user, action=action, resource_id=resource_id, since_hours=since_hours
    )
    return {"data": events}

@router.get("/users/{username}", dependencies=[Depends(require_role("admin"))])
async def get_user_activity(username: str, since_days: int = Query(7)):
    es = await get_es_client()
    activity = await audit_logger_instance.get_user_activity(es=es, user=username, since_days=since_days)
    return {"data": activity}

@router.get("/export", dependencies=[Depends(require_role("admin"))])
async def export_audit_logs(
    since_hours: int = Query(24)
):
    es = await get_es_client()
    events = await audit_logger_instance.get_audit_trail(es=es, since_hours=since_hours)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["event_id", "timestamp", "user", "role", "action", "resource_type", "resource_id", "ip_address", "result"])
    
    for e in events:
        writer.writerow([
            e.event_id, e.timestamp, e.user, e.role, e.action, e.resource_type, e.resource_id, e.ip_address, e.result
        ])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=soc_audit_log_{since_hours}h.csv"}
    )
