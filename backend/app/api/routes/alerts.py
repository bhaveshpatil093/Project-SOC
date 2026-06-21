
from app.monitoring.audit_logger import audit_action
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth.jwt import require_role
from app.cache.cache_manager import cache_result
from app.ingestion.es_client import INDEX_NAMES, get_es_client
from app.middleware.rate_limiter import limiter
from app.scoring.threat_engine import get_threat_engine

router = APIRouter()

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

class AlertListResponse(BaseModel):
    total: int
    alerts: list[AlertResponse]
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
    """Fetches ML processed alerts querying across elastic fields scaling with deep pagination arrays."""
    es = await get_es_client()
    must_clauses = []

    if status: must_clauses.append({"match": {"status.keyword": status}})
    if threat_level: must_clauses.append({"match": {"threat_level.keyword": threat_level}})

    if host_id: must_clauses.append({"wildcard": {"entity_key.keyword": f"{host_id}|*"}})
    if user_name: must_clauses.append({"wildcard": {"entity_key.keyword": f"*|{user_name}"}})

    if from_time or to_time:
        time_range = {}
        if from_time: time_range["gte"] = from_time
        if to_time: time_range["lte"] = to_time
        must_clauses.append({"range": {"timestamp": time_range}})

    query = {
        "from": offset,
        "size": limit,
        "sort": [{"threat_score": {"order": "desc"}}],
        "query": {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}
    }

    try:
        resp = await es.search(index=INDEX_NAMES["alerts_processed"], body=query, ignore_unavailable=True)
        hits = resp.get("hits", {}).get("hits", [])
        total = resp.get("hits", {}).get("total", {}).get("value", 0)

        alerts = [{"id": h["_id"], **h["_source"]} for h in hits]
        return AlertListResponse(total=total, alerts=alerts, page=(offset // limit) + 1)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=AlertStatsResponse, dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
@cache_result(ttl_seconds=60, key_fn=lambda: "alert_stats")
async def get_stats():
    """Generates complex ES aggregations tracking pipeline security throughput explicitly mapping to React UI dashboards."""
    es = await get_es_client()
    query = {
        "size": 0,
        "query": {"match_all": {}},
        "aggs": {
            "status_open": {"filter": {"term": {"status.keyword": "open"}}},
            "levels": {"terms": {"field": "threat_level.keyword"}},
            "top_tactics": {"terms": {"field": "mitre_tactics.keyword", "size": 5}},
            "top_entities": {"terms": {"field": "entity_key.keyword", "size": 5}},
            "last_24h": {"range": {"timestamp": {"gte": "now-24h/h", "lte": "now/h"}}}
        }
    }
    try:
        resp = await es.search(index=INDEX_NAMES["alerts_processed"], body=query, ignore_unavailable=True)
        aggs = resp.get("aggregations", {})

        open_cnt = aggs.get("status_open", {}).get("doc_count", 0)
        levels = {b["key"]: b["doc_count"] for b in aggs.get("levels", {}).get("buckets", [])}
        top_tactics = [{"tactic": b["key"], "count": b["doc_count"]} for b in aggs.get("top_tactics", {}).get("buckets", [])]

        top_hosts = []
        for b in aggs.get("top_entities", {}).get("buckets", []):
            entity_str = b["key"]
            host_id = entity_str.split("|")[0] if "|" in entity_str else entity_str
            top_hosts.append({"host_id": host_id, "count": b["doc_count"]})

        last_24 = aggs.get("last_24h", {}).get("doc_count", 0)

        return AlertStatsResponse(
            total_open=open_cnt,
            critical=levels.get("critical", 0),
            high=levels.get("high", 0),
            medium=levels.get("medium", 0),
            low=levels.get("low", 0),
            top_tactics=top_tactics,
            top_hosts=top_hosts,
            alerts_last_24h=last_24
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-scoring", dependencies=[Depends(require_role("admin", "analyst"))])
async def trigger_scoring():
    """Manually forces Threat Engine execution spanning the whole extraction pipeline synchronously."""
    engine = get_threat_engine()
    try:
        result = await engine.run_scoring_cycle(since_minutes=5)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alert_id}", response_model=AlertResponse, dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_alert(alert_id: str):
    """Resolves singular specific alerts returning precise SHAP features and translation mappings."""
    engine = get_threat_engine()
    alert = await engine.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"id": alert_id, **alert}


@router.patch("/{alert_id}/status", dependencies=[Depends(require_role("admin", "analyst"))])
async def update_status(alert_id: str, update: StatusUpdate = Body(...)):
    """Allows UI triage handlers mapping interactive state flows directly natively over ES document fields."""
    if update.status not in ["open", "closed", "in_progress"]:
        raise HTTPException(status_code=422, detail="Invalid status. Must be 'open', 'closed', or 'in_progress'.")

    engine = get_threat_engine()
    alert = await engine.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await engine.update_alert_status(alert_id, update.status)
    await audit_action('alert.status_change', 'alert', alert_id, {'new_status': update.status})
    await audit_action('alert.status_change', 'alert', alert_id, {'new_status': update.status})
    return {"status": "success", "updated_status": update.status}


@router.get("/{alert_id}/timeline", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_timeline(alert_id: str):
    """Constructs localized chronological execution limits tracking identically mapped anomalies spanning exact same entities."""
    engine = get_threat_engine()
    alert = await engine.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    entity_key = alert.get("entity_key")
    if not entity_key:
        return {"timeline": []}

    es = await get_es_client()
    query = {
        "size": 100,
        "sort": [{"timestamp": {"order": "asc"}}],
        "query": {
            "term": {"entity_key.keyword": entity_key}
        }
    }
    try:
        resp = await es.search(index=INDEX_NAMES["alerts_processed"], body=query, ignore_unavailable=True)
        hits = resp.get("hits", {}).get("hits", [])
        return {"timeline": [{"id": h["_id"], **h["_source"]} for h in hits]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
