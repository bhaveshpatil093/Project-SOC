import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from app.slm.engine import SLMEngine

logger = logging.getLogger(__name__)

INDEX_NAME = "soc-shift-reports"

@dataclass
class ShiftReport:
    report_id: str
    shift_start: str
    shift_end: str
    generated_at: str

    total_alerts: int
    critical_alerts: int
    high_alerts: int
    new_incidents: int
    alerts_closed: int
    alerts_escalated: int
    feedback_submitted: int

    top_threats: list[dict[str, Any]]
    active_incidents: list[dict[str, Any]]
    watchlisted_entity_activity: list[dict[str, Any]]

    shift_narrative: str
    key_findings: list[str]
    open_items: list[str]
    recommendations: list[str]

async def _fetch_metrics(es, start_time: datetime, end_time: datetime) -> dict:
    # 1. Alerts within window
    query = {
        "query": {
            "range": {
                "timestamp": {
                    "gte": start_time.isoformat() + "Z",
                    "lte": end_time.isoformat() + "Z"
                }
            }
        },
        "aggs": {
            "threat_levels": {"terms": {"field": "threat_level.keyword"}},
            "status": {"terms": {"field": "status.keyword"}},
            "feedback": {"filter": {"exists": {"field": "feedback_status"}}}
        },
        "size": 5,
        "sort": [{"threat_score": {"order": "desc"}}]
    }

    alert_res = await es.search(index="soc-processed-alerts", body=query)

    total_alerts = alert_res["hits"]["total"]["value"] if isinstance(alert_res["hits"]["total"], dict) else alert_res["hits"]["total"]
    top_threats = [hit["_source"] for hit in alert_res["hits"]["hits"]]

    aggs = alert_res.get("aggregations", {})
    levels = {b["key"]: b["doc_count"] for b in aggs.get("threat_levels", {}).get("buckets", [])}
    statuses = {b["key"]: b["doc_count"] for b in aggs.get("status", {}).get("buckets", [])}

    # 2. Incidents within window
    inc_query = {
        "query": {
            "range": {
                "created_at": {
                    "gte": start_time.isoformat() + "Z",
                    "lte": end_time.isoformat() + "Z"
                }
            }
        }
    }
    inc_res = await es.search(index="soc-incidents", body=inc_query)
    new_incidents = inc_res["hits"]["total"]["value"] if isinstance(inc_res["hits"]["total"], dict) else inc_res["hits"]["total"]

    # 3. Active incidents (regardless of creation time, just status=open)
    active_inc_query = {
        "query": {"term": {"status.keyword": "open"}},
        "size": 10,
        "sort": [{"incident_threat_score": {"order": "desc"}}]
    }
    active_inc_res = await es.search(index="soc-incidents", body=active_inc_query)
    active_incidents = [hit["_source"] for hit in active_inc_res["hits"]["hits"]]

    # 4. Watchlisted entity activity
    wl_query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"is_watchlisted": True}},
                    {"range": {"last_updated": {"gte": start_time.isoformat() + "Z", "lte": end_time.isoformat() + "Z"}}}
                ]
            }
        },
        "size": 10
    }
    wl_res = await es.search(index="soc-entity-profiles", body=wl_query)
    watchlisted = [hit["_source"] for hit in wl_res["hits"]["hits"]]

    return {
        "total_alerts": total_alerts,
        "critical_alerts": levels.get("critical", 0),
        "high_alerts": levels.get("high", 0),
        "new_incidents": new_incidents,
        "alerts_closed": statuses.get("closed", 0),
        "alerts_escalated": statuses.get("escalated", 0),
        "feedback_submitted": aggs.get("feedback", {}).get("doc_count", 0),
        "top_threats": top_threats,
        "active_incidents": active_incidents,
        "watchlisted": watchlisted
    }

async def generate_shift_report(es, slm_engine: SLMEngine, shift_hours: int = 8) -> ShiftReport:
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=shift_hours)

    metrics = await _fetch_metrics(es, start_time, end_time)

    # Prepare prompt data
    prompt_data = f"""
Shift metrics: {metrics['total_alerts']} total alerts ({metrics['critical_alerts']} critical, {metrics['high_alerts']} high).
New Incidents: {metrics['new_incidents']}.
Alerts closed: {metrics['alerts_closed']}. Escalated: {metrics['alerts_escalated']}.
Top Threat Entities: {', '.join([a.get('entity_key', 'Unknown') for a in metrics['top_threats']])}.
Active Incidents: {len(metrics['active_incidents'])} still open.
"""

    narrative_prompt = f"Write a professional 2-paragraph summary of this SOC shift for the handover report.\\n{prompt_data}"
    findings_prompt = f"List exactly 3 bullet points highlighting the key security findings from this shift.\\n{prompt_data}"
    open_items_prompt = f"List exactly 2-3 open items needing attention by the next shift analyst.\\n{prompt_data}"
    recommendations_prompt = f"Provide 2 actionable recommendations for the next shift analyst.\\n{prompt_data}"

    try:
        narrative = await slm_engine.generate(narrative_prompt, max_tokens=250)
    except:
        narrative = f"Shift concluded with {metrics['total_alerts']} alerts processed."

    try:
        findings_text = await slm_engine.generate(findings_prompt, max_tokens=150)
        findings = [f.replace("- ", "").replace("* ", "").strip() for f in findings_text.split("\\n") if f.strip() and (f.strip().startswith("-") or f.strip().startswith("*"))]
    except:
        findings = [f"{metrics['critical_alerts']} critical alerts detected."]

    try:
        open_text = await slm_engine.generate(open_items_prompt, max_tokens=150)
        open_items = [f.replace("- ", "").replace("* ", "").strip() for f in open_text.split("\\n") if f.strip() and (f.strip().startswith("-") or f.strip().startswith("*"))]
    except:
        open_items = [f"Review {len(metrics['active_incidents'])} open incidents."]

    try:
        recs_text = await slm_engine.generate(recommendations_prompt, max_tokens=150)
        recommendations = [f.replace("- ", "").replace("* ", "").strip() for f in recs_text.split("\\n") if f.strip() and (f.strip().startswith("-") or f.strip().startswith("*"))]
    except:
        recommendations = ["Monitor watchlisted entities closely."]

    # Build report
    report = ShiftReport(
        report_id=str(uuid.uuid4()),
        shift_start=start_time.isoformat() + "Z",
        shift_end=end_time.isoformat() + "Z",
        generated_at=datetime.utcnow().isoformat() + "Z",
        total_alerts=metrics["total_alerts"],
        critical_alerts=metrics["critical_alerts"],
        high_alerts=metrics["high_alerts"],
        new_incidents=metrics["new_incidents"],
        alerts_closed=metrics["alerts_closed"],
        alerts_escalated=metrics["alerts_escalated"],
        feedback_submitted=metrics["feedback_submitted"],
        top_threats=metrics["top_threats"],
        active_incidents=metrics["active_incidents"],
        watchlisted_entity_activity=metrics["watchlisted"],
        shift_narrative=narrative.strip(),
        key_findings=findings if findings else ["No major findings."],
        open_items=open_items if open_items else ["None."],
        recommendations=recommendations if recommendations else ["None."]
    )

    # Save to ES
    try:
        await es.index(index=INDEX_NAME, document=asdict(report))
        logger.info(f"Generated shift report: {report.report_id}")
    except Exception as e:
        logger.error(f"Failed to save shift report: {e}")

    return report

async def get_latest_shift_report(es, max_hours: int = 8) -> dict:
    query = {
        "query": {"match_all": {}},
        "size": 1,
        "sort": [{"generated_at": {"order": "desc"}}]
    }
    try:
        res = await es.search(index=INDEX_NAME, body=query)
        hits = res["hits"]["hits"]
        if hits:
            return hits[0]["_source"]
        return None
    except Exception as e:
        logger.error(f"Error fetching latest shift report: {e}")
        return None
