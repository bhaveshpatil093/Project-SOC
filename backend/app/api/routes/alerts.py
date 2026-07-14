from collections import Counter
from datetime import datetime, timedelta
import uuid
import json
import aiosqlite

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth.jwt import require_role, get_current_user
from app.cache.cache_manager import cache_result
from app.middleware.rate_limiter import limiter
from app.scoring.threat_engine import get_threat_engine
from app.storage import local_db
from app.config import settings
from app.monitoring.audit_logger import audit_action, AuditEvent
from app.monitoring.audit_logger import audit_logger_instance

router = APIRouter()

@router.get("/tags", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_all_tags():
    """Returns all unique tags used across alerts stored in the local DB."""
    try:
        alerts = await local_db.list_alerts(settings.DB_PATH, limit=10000)
        tags = set()
        for a in alerts:
            raw = a.get("raw_context", {})
            for t in raw.get("tags", []):
                tags.add(t)
        return {"tags": sorted(list(tags))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AlertResponse(BaseModel):
    id: str
    entity_key: str
    threat_score: float
    threat_level: str
    top_features: list[str]
    triggered_rules: list[str]
    mitre_tactics: list[str]
    human_explanation: str
    timestamp: str
    status: str
    tags: list[str] = []

class AlertListResponse(BaseModel):
    total: int
    alerts: list[dict] 
    page: int

class AlertStatsResponse(BaseModel):
    total_open: int
    critical: int
    high: int
    medium: int
    low: int
    top_tactics: list[dict]
    top_hosts: list[dict]
    alerts_last_24h: int

class StatusUpdate(BaseModel):
    status: str

@router.get("", response_model=AlertListResponse, dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
@limiter.limit("120/minute")
async def get_alerts_list(
    request: Request,
    status: str | None = Query(None, description="Filter by status (open, closed)"),
    threat_level: str | None = Query(None, description="Filter by level (critical, high, medium, low)"),
    host_id: str | None = Query(None, description="Filter by origin host ID"),
    user_name: str | None = Query(None, description="Filter by active user context"),
    from_time: str | None = Query(None, description="ISO timestamp baseline"),
    to_time: str | None = Query(None, description="ISO timestamp ceiling"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        alerts = await local_db.list_alerts(settings.DB_PATH, status=status, limit=10000, offset=0, host_id=host_id)
        
        filtered = []
        for a in alerts:
            if threat_level and a.get("threat_level") != threat_level:
                continue
            if user_name and a.get("user_name") != user_name:
                continue
                
            created_at = a.get("created_at", "")
            if from_time and created_at < from_time:
                continue
            if to_time and created_at > to_time:
                continue
                
            filtered.append(a)
            
        total = len(filtered)
        paged = filtered[offset:offset+limit]
        
        mapped = []
        for a in paged:
            m = a.get("raw_context", {})
            m["id"] = a.get("alert_id")
            if "timestamp" not in m:
                m["timestamp"] = a.get("created_at")
            if "status" not in m:
                m["status"] = a.get("alert_status")
            mapped.append(m)
            
        return AlertListResponse(total=total, alerts=mapped, page=(offset // limit) + 1)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=AlertStatsResponse, dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
@cache_result(ttl_seconds=60, key_fn=lambda: "alert_stats")
async def get_stats():
    try:
        open_alerts = await local_db.list_alerts(settings.DB_PATH, status="open", limit=10000)
        
        levels = Counter(a.get("threat_level") for a in open_alerts)
        
        tactic_counter = Counter()
        for a in open_alerts:
            t = a.get("mitre_tactic")
            if t:
                tactic_counter[t] += 1
                
        top_tactics = [{"tactic": t, "count": c} for t, c in tactic_counter.most_common(5)]
        top_hosts = [{"host_id": h, "count": c} for h, c in Counter(a.get("host_id") for a in open_alerts if a.get("host_id")).most_common(5)]
        
        last_24h_limit = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
        last_24h_count = sum(1 for a in open_alerts if a.get("created_at", "") > last_24h_limit)
        
        return AlertStatsResponse(
            total_open=len(open_alerts),
            critical=levels.get("critical", 0),
            high=levels.get("high", 0),
            medium=levels.get("medium", 0),
            low=levels.get("low", 0),
            top_tactics=top_tactics,
            top_hosts=top_hosts,
            alerts_last_24h=last_24h_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trigger-scoring", dependencies=[Depends(require_role("admin", "analyst"))])
async def trigger_scoring():
    engine = get_threat_engine()
    try:
        result = await engine.run_scoring_cycle(since_minutes=5)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{alert_id}", response_model=AlertResponse, dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_alert(alert_id: str):
    alert = await local_db.get_alert(settings.DB_PATH, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    m = alert.get("raw_context", {})
    m["id"] = alert_id
    if "timestamp" not in m:
        m["timestamp"] = alert.get("created_at")
    if "status" not in m:
        m["status"] = alert.get("alert_status")
        
    return m

@router.patch("/{alert_id}/status", dependencies=[Depends(require_role("admin", "analyst"))])
async def update_status(alert_id: str, update: StatusUpdate = Body(...)):
    if update.status not in ["open", "closed", "in_progress"]:
        raise HTTPException(status_code=422, detail="Invalid status.")

    alert = await local_db.get_alert(settings.DB_PATH, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await local_db.update_alert_status(settings.DB_PATH, alert_id, update.status)
    await audit_action('alert.status_change', 'alert', alert_id, {'new_status': update.status})
    return {"status": "success", "updated_status": update.status}

@router.get("/{alert_id}/timeline", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_timeline(alert_id: str):
    alert = await local_db.get_alert(settings.DB_PATH, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    entity_key = alert.get("entity_key")
    if not entity_key:
        return {"timeline": []}

    engine = get_threat_engine()
    try:
        timeline = await engine.get_entity_timeline(entity_key)
        return {"timeline": timeline}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TagPayload(BaseModel):
    tags: list[str] = Field(..., max_length=10)

@router.post("/{alert_id}/tags")
async def add_alert_tags(
    alert_id: str,
    payload: TagPayload,
    request: Request,
    user: dict = Depends(get_current_user)
):
    try:
        alert = await local_db.get_alert(settings.DB_PATH, alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
            
        raw_context = alert.get("raw_context", {})
        existing_tags = raw_context.get("tags", [])
        
        new_tags = []
        for tag in payload.tags:
            tag = tag.strip().lower()
            if len(tag) > 30:
                raise HTTPException(status_code=400, detail=f"Tag '{tag}' exceeds 30 characters")
            if tag and tag not in existing_tags and tag not in new_tags:
                new_tags.append(tag)
                
        if not new_tags:
            return {"tags": existing_tags}
            
        merged_tags = existing_tags + new_tags
        if len(merged_tags) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 tags allowed per alert")
            
        raw_context["tags"] = merged_tags
        async with aiosqlite.connect(settings.DB_PATH) as db:
            await db.execute("UPDATE soc_alerts SET raw_context = ? WHERE alert_id = ?", (json.dumps(raw_context), alert_id))
            await db.commit()
        
        await audit_action('alert.add_tags', 'alert', alert_id, {'added_tags': new_tags})
        return {"tags": merged_tags}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to add tags")

@router.delete("/{alert_id}/tags/{tag}")
async def remove_alert_tag(
    alert_id: str,
    tag: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    try:
        alert = await local_db.get_alert(settings.DB_PATH, alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
            
        raw_context = alert.get("raw_context", {})
        existing_tags = raw_context.get("tags", [])
        
        tag = tag.lower()
        if tag not in existing_tags:
            return {"tags": existing_tags}
            
        existing_tags.remove(tag)
        
        raw_context["tags"] = existing_tags
        async with aiosqlite.connect(settings.DB_PATH) as db:
            await db.execute("UPDATE soc_alerts SET raw_context = ? WHERE alert_id = ?", (json.dumps(raw_context), alert_id))
            await db.commit()
            
        await audit_action('alert.remove_tag', 'alert', alert_id, {'removed_tag': tag})
        
        return {"tags": existing_tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to remove tag")
