from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.models import User
from app.auth.routes import get_current_user
from app.cache.cache_manager import cache_result
from app.exceptions import AlertNotFoundError
from app.ingestion.es_client import INDEX_NAMES, get_es_client
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

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
    es = await get_es_client()

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
        "query": query
    }

    try:
        resp = await es.search(index=INDEX_NAMES["incidents"], body=body, ignore_unavailable=True)
        hits = resp.get("hits", {}).get("hits", [])
        total = resp.get("hits", {}).get("total", {}).get("value", 0)

        incidents = [h["_source"] for h in hits]
        return {"total": total, "incidents": incidents}
    except Exception as e:
        logger.error("list_incidents_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch incidents")

@router.get("/stats", response_model=IncidentStatsResponse)
@cache_result(ttl_seconds=60, key_fn=lambda *args, **kwargs: "incident_stats")
async def get_incident_stats(current_user: User = Depends(get_current_user)):
    es = await get_es_client()

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
                    "top_hosts": {"terms": {"field": "host_id", "size": 5}}
                }
            }
        }
    }

    try:
        resp = await es.search(index=INDEX_NAMES["incidents"], body=body, ignore_unavailable=True)
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
            top_targeted_hosts=top_hosts
        )
    except Exception as e:
        logger.error("get_incident_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch incident stats")

@router.get("/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident_detail(incident_id: str, current_user: User = Depends(get_current_user)):
    es = await get_es_client()
    try:
        resp = await es.get(index=INDEX_NAMES["incidents"], id=incident_id)
        incident = resp.get("_source")
    except Exception:
        raise AlertNotFoundError(f"Incident {incident_id} not found", "INCIDENT_NOT_FOUND")

    alert_ids = incident.get("alert_ids", [])
    alerts = []
    if alert_ids:
        try:
            alert_resp = await es.mget(index=INDEX_NAMES["alerts_processed"], body={"ids": alert_ids}, ignore_unavailable=True)
            for doc in alert_resp.get("docs", []):
                if doc.get("found"):
                    alert_doc = doc["_source"]
                    alert_doc["id"] = doc["_id"]
                    alerts.append(alert_doc)
        except Exception as e:
            logger.warning("failed_to_fetch_incident_alerts", incident_id=incident_id, error=str(e))

    # Sort alerts by timestamp
    alerts.sort(key=lambda x: x.get("timestamp", ""))

    timeline = []
    attack_chain = []

    start_time = None
    if alerts:
        try:
            start_time = datetime.fromisoformat(alerts[0].get("timestamp").replace("Z", "+00:00"))
        except:
            pass

    for a in alerts:
        ts_str = a.get("timestamp")
        t_delta_str = "T+0m"
        if start_time and ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                delta_min = int((ts - start_time).total_seconds() / 60)
                t_delta_str = f"T+{delta_min}m"
            except:
                pass

        attack_chain.append({
            "time": t_delta_str,
            "log_type": a.get("log_type", "unknown"),
            "tactic": a.get("mitre_tactic", "Unknown"),
            "score": a.get("threat_score", 0.0)
        })

        timeline.append({
            "timestamp": ts_str,
            "event": f"Alert generated for {a.get('log_type')} with score {a.get('threat_score')}",
            "alert_id": a.get("id")
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
    current_user: User = Depends(get_current_user)
):
    if update.status not in ["active", "resolved", "escalated"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    es = await get_es_client()
    body = {"doc": {"status": update.status}}
    try:
        await es.update(index=INDEX_NAMES["incidents"], id=incident_id, body=body)
        logger.info("incident_status_updated", incident_id=incident_id, status=update.status, user=current_user.username)
        return {"success": True, "incident_id": incident_id, "status": update.status}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to update incident")

@router.post("/{incident_id}/escalate")
async def escalate_incident(
    incident_id: str,
    escalation: IncidentEscalation,
    current_user: User = Depends(get_current_user)
):
    es = await get_es_client()
    body = {
        "doc": {
            "status": "escalated",
            "escalated_to": escalation.escalated_to,
            "escalation_reason": escalation.reason,
            "escalated_by": current_user.username,
            "escalated_at": datetime.utcnow().isoformat()
        }
    }
    try:
        await es.update(index=INDEX_NAMES["incidents"], id=incident_id, body=body)
        logger.info("incident_escalated", incident_id=incident_id, to=escalation.escalated_to)
        return {"success": True, "incident_id": incident_id, "status": "escalated"}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to escalate incident")

@router.get("/{incident_id}/investigate")
async def investigate_incident(incident_id: str, current_user: User = Depends(get_current_user)):
    from app.slm.model_loader import _slm_engine

    if _slm_engine.model is None:
        raise HTTPException(status_code=503, detail="SLM engine not loaded")

    es = await get_es_client()
    try:
        resp = await es.get(index=INDEX_NAMES["incidents"], id=incident_id)
        incident = resp.get("_source")
    except:
        raise AlertNotFoundError(f"Incident {incident_id} not found", "INCIDENT_NOT_FOUND")

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


async def run_report_generation(incident_id: str):
    es = await get_es_client()
    try:
        # Fetch incident
        res = await es.get(index="soc-incidents", id=incident_id)
        incident = res["_source"]

        # Fetch alerts
        alerts = []
        if incident.get("alert_ids"):
            alerts_res = await es.search(
                index="soc-processed-alerts",
                body={"query": {"terms": {"_id": incident["alert_ids"]}}, "size": 100}
            )
            alerts = [hit["_source"] for hit in alerts_res.get("hits", {}).get("hits", [])]

        slm_engine = SLMEngine()
        await generate_incident_report(es, slm_engine, incident_id, incident, alerts)
    except Exception as e:
        print(f"Error generating report in background: {e}")


@router.post("/{incident_id}/generate-report", dependencies=[Depends(require_role("admin", "analyst"))])
async def trigger_report_generation(incident_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_report_generation, incident_id)
    return {"job_id": str(uuid.uuid4()), "status": "generating"}

@router.get("/{incident_id}/report", dependencies=[Depends(require_role("admin", "analyst"))])
async def fetch_incident_report(incident_id: str):
    es = await get_es_client()
    report = await get_incident_report(es, incident_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or still generating")
    return {"data": report}
