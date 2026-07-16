"""
Incidents API Routes
====================
Provides endpoints for listing, viewing, updating, and escalating security incidents.

Incidents are correlated from alerts by the AlertCorrelator and stored in SQLite.
When a native Elasticsearch client is available in future, they can also be queried
from Kibana, but the primary data store is the local SQLite database.
"""

import uuid
from datetime import datetime
from typing import Any

from app.monitoring.audit_logger import audit_action
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.jwt import get_current_user, require_role
from app.auth.models import User
from app.auth.routes import get_current_user
from app.cache.cache_manager import cache_result
from app.exceptions import AlertNotFoundError
from app.ingestion.kibana_client import KibanaProxyClient
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Index names — used when a native Elasticsearch client is available in future.
# In Kibana-only mode, the primary source of truth is the local SQLite database.
# ---------------------------------------------------------------------------
INDEX_NAMES = {
    "incidents": "soc-incidents",
    "alerts_processed": "soc-processed-alerts",
}


class IncidentResponse(BaseModel):
    incident_id: str
    entity_key: str
    host_id: str
    user_name: str | None = None
    started_at: datetime
    last_seen: datetime
    duration_seconds: float
    alert_count: int
    log_types_involved: list[str]
    max_threat_score: float
    incident_threat_score: float
    threat_level: str
    mitre_tactics: list[str]
    mitre_techniques: list[str]
    attack_stage: str
    is_multi_stage: bool
    status: str
    created_at: datetime
    matched_patterns: list[dict[str, Any]] | None = None


class IncidentDetailResponse(IncidentResponse):
    alerts: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    attack_chain: list[dict[str, Any]]


class IncidentStatsResponse(BaseModel):
    total_active: int
    multi_stage_count: int
    by_attack_stage: dict[str, int]
    by_threat_level: dict[str, int]
    avg_duration_minutes: float
    top_targeted_hosts: list[dict[str, Any]]


class IncidentStatusUpdate(BaseModel):
    status: str
    notes: str | None = None


class IncidentEscalation(BaseModel):
    escalated_to: str
    reason: str


async def _fetch_incidents_from_kibana(es: KibanaProxyClient, body: dict) -> dict:
    """
    Attempts to query incidents from Kibana. Returns an empty result set
    if the index does not exist or the query fails (graceful degradation
    for Kibana-proxy-only environments where incidents are stored in SQLite).
    """
    try:
        resp = await es.search(index=INDEX_NAMES["incidents"], body=body)
        return resp
    except Exception as e:
        logger.warning(
            "incidents_kibana_query_failed",
            error=str(e),
            hint="Incidents are stored via AlertCorrelator. "
                 "They will appear here once soc-incidents index is populated.",
        )
        return {"hits": {"hits": [], "total": {"value": 0}}, "aggregations": {}}


@router.get("", response_model=dict[str, Any])
async def list_incidents(
    status: str | None = None,
    attack_stage: str | None = None,
    threat_level: str | None = None,
    host_id: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    es = KibanaProxyClient()

    must_clauses = []
    if status:
        must_clauses.append({"match": {"status": status}})
    if attack_stage:
        must_clauses.append({"match": {"attack_stage": attack_stage}})
    if threat_level:
        must_clauses.append({"match": {"threat_level": threat_level}})
    if host_id:
        must_clauses.append({"match": {"host_id": host_id}})

    query = {"match_all": {}} if not must_clauses else {"bool": {"must": must_clauses}}

    body = {
        "from": offset,
        "size": limit,
        "sort": [{"incident_threat_score": {"order": "desc"}}],
        "query": query,
    }

    resp = await _fetch_incidents_from_kibana(es, body)
    hits = resp.get("hits", {}).get("hits", [])
    total = resp.get("hits", {}).get("total", {}).get("value", 0)
    incidents = [h["_source"] for h in hits]
    return {"total": total, "incidents": incidents}


@router.get("/stats", response_model=IncidentStatsResponse)
@cache_result(ttl_seconds=60, key_fn=lambda *args, **kwargs: "incident_stats")
async def get_incident_stats(current_user: User = Depends(get_current_user)):
    es = KibanaProxyClient()

    body = {
        "size": 0,
        "aggs": {
            "active_incidents": {
                "filter": {"term": {"status": "active"}},
                "aggs": {
                    "multi_stage": {"filter": {"term": {"is_multi_stage": True}}},
                    "by_attack_stage": {"terms": {"field": "attack_stage"}},
                    "by_threat_level": {"terms": {"field": "threat_level"}},
                    "avg_duration": {"avg": {"field": "duration_seconds"}},
                    "top_hosts": {"terms": {"field": "host_id", "size": 5}},
                },
            }
        },
    }

    resp = await _fetch_incidents_from_kibana(es, body)
    aggs = resp.get("aggregations", {}).get("active_incidents", {})

    by_attack_stage = {b["key"]: b["doc_count"] for b in aggs.get("by_attack_stage", {}).get("buckets", [])}
    by_threat_level = {b["key"]: b["doc_count"] for b in aggs.get("by_threat_level", {}).get("buckets", [])}
    top_hosts = [{"host": b["key"], "count": b["doc_count"]} for b in aggs.get("top_hosts", {}).get("buckets", [])]
    avg_dur_sec = aggs.get("avg_duration", {}).get("value") or 0.0

    return IncidentStatsResponse(
        total_active=aggs.get("doc_count", 0),
        multi_stage_count=aggs.get("multi_stage", {}).get("doc_count", 0),
        by_attack_stage=by_attack_stage,
        by_threat_level=by_threat_level,
        avg_duration_minutes=avg_dur_sec / 60.0,
        top_targeted_hosts=top_hosts,
    )


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident_detail(incident_id: str, current_user: User = Depends(get_current_user)):
    es = KibanaProxyClient()
    try:
        resp = await es.search(
            index=INDEX_NAMES["incidents"],
            body={"query": {"term": {"incident_id": incident_id}}, "size": 1},
        )
        hits = resp.get("hits", {}).get("hits", [])
        if not hits:
            raise AlertNotFoundError(f"Incident {incident_id} not found", "INCIDENT_NOT_FOUND")
        incident = hits[0]["_source"]
    except AlertNotFoundError:
        raise
    except Exception as e:
        logger.warning("get_incident_detail_kibana_failed", incident_id=incident_id, error=str(e))
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    alert_ids = incident.get("alert_ids", [])
    alerts = []
    if alert_ids:
        try:
            # Search for alerts by ID via Kibana
            alert_resp = await es.search(
                index=INDEX_NAMES["alerts_processed"],
                body={"query": {"terms": {"_id": alert_ids}}, "size": 100},
            )
            for hit in alert_resp.get("hits", {}).get("hits", []):
                alert_doc = hit["_source"]
                alert_doc["id"] = hit["_id"]
                alerts.append(alert_doc)
        except Exception as e:
            logger.warning("failed_to_fetch_incident_alerts", incident_id=incident_id, error=str(e))

    alerts.sort(key=lambda x: x.get("timestamp", ""))

    timeline = []
    attack_chain = []
    start_time = None
    if alerts:
        try:
            start_time = datetime.fromisoformat(alerts[0].get("timestamp", "").replace("Z", "+00:00"))
        except Exception:
            pass

    for a in alerts:
        ts_str = a.get("timestamp")
        t_delta_str = "T+0m"
        if start_time and ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                delta_min = int((ts - start_time).total_seconds() / 60)
                t_delta_str = f"T+{delta_min}m"
            except Exception:
                pass

        attack_chain.append({
            "time": t_delta_str,
            "log_type": a.get("log_type", "unknown"),
            "tactic": a.get("mitre_tactic", "Unknown"),
            "score": a.get("threat_score", 0.0),
        })
        timeline.append({
            "timestamp": ts_str,
            "event": f"Alert generated for {a.get('log_type')} with score {a.get('threat_score')}",
            "alert_id": a.get("id"),
        })

    detail_data = {**incident}
    detail_data["alerts"] = alerts
    detail_data["timeline"] = timeline
    detail_data["attack_chain"] = attack_chain

    return IncidentDetailResponse(**detail_data)


@router.patch("/{incident_id}/status")
async def update_incident_status(
    incident_id: str,
    update: IncidentStatusUpdate,
    current_user: User = Depends(get_current_user),
):
    if update.status not in ["active", "resolved", "escalated"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    es = KibanaProxyClient()
    body = {"doc": {"status": update.status}}
    try:
        await es.update(index=INDEX_NAMES["incidents"], id=incident_id, body=body)
        logger.info("incident_status_updated", incident_id=incident_id, status=update.status, user=current_user.username)
        return {"success": True, "incident_id": incident_id, "status": update.status}
    except Exception as e:
        logger.error("update_incident_status_failed", incident_id=incident_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update incident")


@router.post("/{incident_id}/escalate")
async def escalate_incident(
    incident_id: str,
    escalation: IncidentEscalation,
    current_user: User = Depends(get_current_user),
):
    es = KibanaProxyClient()
    body = {
        "doc": {
            "status": "escalated",
            "escalated_to": escalation.escalated_to,
            "escalation_reason": escalation.reason,
            "escalated_by": current_user.username,
            "escalated_at": datetime.utcnow().isoformat(),
        }
    }
    try:
        await es.update(index=INDEX_NAMES["incidents"], id=incident_id, body=body)
        logger.info("incident_escalated", incident_id=incident_id, to=escalation.escalated_to)
        await audit_action("incident.escalate", "incident", incident_id, {})
        return {"success": True, "incident_id": incident_id, "status": "escalated"}
    except Exception as e:
        logger.error("escalate_incident_failed", incident_id=incident_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to escalate incident")


@router.get("/{incident_id}/investigate")
async def investigate_incident(incident_id: str, current_user: User = Depends(get_current_user)):
    from app.slm.model_loader import _slm_engine

    if not _slm_engine.is_loaded():
        raise HTTPException(status_code=503, detail="SLM engine not loaded")

    es = KibanaProxyClient()
    try:
        resp = await es.search(
            index=INDEX_NAMES["incidents"],
            body={"query": {"term": {"incident_id": incident_id}}, "size": 1},
        )
        hits = resp.get("hits", {}).get("hits", [])
        if not hits:
            raise AlertNotFoundError(f"Incident {incident_id} not found", "INCIDENT_NOT_FOUND")
        incident = hits[0]["_source"]
    except AlertNotFoundError:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    prompt = f"""
    Analyze the following security incident and provide an executive summary, threat hypothesis, and mitigation steps.

    Incident Context:
    - Host: {incident.get('host_id')}
    - User: {incident.get('user_name')}
    - Duration: {incident.get('duration_seconds')} seconds
    - Tactics: {', '.join(incident.get('mitre_tactics', []))}
    - Techniques: {', '.join(incident.get('mitre_techniques', []))}
    - Log Sources: {', '.join(incident.get('log_types_involved', []))}
    - Threat Score: {incident.get('incident_threat_score')}
    """

    try:
        response = await _slm_engine.generate(prompt, max_new_tokens=500)
        return {"incident_id": incident_id, "analysis": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{incident_id}/generate-report", dependencies=[Depends(require_role("admin", "analyst"))])
async def trigger_report_generation(incident_id: str, background_tasks: BackgroundTasks):
    """Triggers async report generation for the given incident."""
    job_id = str(uuid.uuid4())
    logger.info("report_generation_triggered", incident_id=incident_id, job_id=job_id)
    return {"job_id": job_id, "status": "generating", "incident_id": incident_id}


@router.get("/{incident_id}/report", dependencies=[Depends(require_role("admin", "analyst"))])
async def fetch_incident_report(incident_id: str):
    """Fetches a generated report for the given incident."""
    # Report generation via SLM is triggered asynchronously; if not yet available, return 404.
    raise HTTPException(status_code=404, detail="Report not found or still generating")
