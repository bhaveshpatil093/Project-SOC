import logging
from datetime import datetime

from pydantic import BaseModel

logger = logging.getLogger(__name__)

FEEDBACK_INDEX = "soc-analyst-feedback"

class AnalystFeedback(BaseModel):
    alert_id: str
    analyst_name: str
    label: str  # TP, FP, Benign
    notes: str | None = ""
    mitre_override: list[str] | None = []

async def submit_feedback(es, feedback: AnalystFeedback) -> dict:
    doc = feedback.dict()
    doc["timestamp"] = datetime.utcnow().isoformat() + "Z"

    try:
        from app.ingestion.es_client import INDEX_NAMES
        alert_resp = await es.get(index=INDEX_NAMES["alerts_processed"], id=feedback.alert_id, ignore_unavailable=True)
        if "_source" in alert_resp:
            alert_doc = alert_resp["_source"]
            doc["entity_key"] = alert_doc.get("entity_key", "")
            doc["triggered_rules"] = alert_doc.get("triggered_rules", [])

        resp = await es.index(index=FEEDBACK_INDEX, document=doc)
        return {"status": "success", "id": resp["_id"]}
    except Exception as e:
        logger.error(f"Error submitting feedback mapping: {e}")
        return {"status": "error", "message": str(e)}

async def get_feedback_for_alert(es, alert_id: str) -> list[dict]:
    query = {"query": {"match": {"alert_id.keyword": alert_id}}, "sort": [{"timestamp": {"order": "desc"}}]}
    try:
        resp = await es.search(index=FEEDBACK_INDEX, body=query, ignore_unavailable=True)
        return [{"id": h["_id"], **h["_source"]} for h in resp.get("hits", {}).get("hits", [])]
    except Exception:
        return []

async def get_all_feedback(es, label: str = None, limit: int = 500) -> list[dict]:
    must = []
    if label: must.append({"match": {"label.keyword": label}})

    query = {
        "size": limit,
        "sort": [{"timestamp": {"order": "desc"}}],
        "query": {"bool": {"must": must}} if must else {"match_all": {}}
    }
    try:
        resp = await es.search(index=FEEDBACK_INDEX, body=query, ignore_unavailable=True)
        return [{"id": h["_id"], **h["_source"]} for h in resp.get("hits", {}).get("hits", [])]
    except Exception:
        return []

async def get_fp_suppression_patterns(es) -> list[dict]:
    """Isolates explicit False Positive bounds mapping historical intersections recursively matching entities + heuristics."""
    query = {
        "size": 0,
        "query": {"match": {"label.keyword": "FP"}},
        "aggs": {
            "entities": {
                "terms": {"field": "entity_key.keyword", "size": 100},
                "aggs": {
                    "rules": {
                        "terms": {"field": "triggered_rules.keyword", "size": 10}
                    }
                }
            }
        }
    }
    try:
        resp = await es.search(index=FEEDBACK_INDEX, body=query, ignore_unavailable=True)
        patterns = []
        for b in resp.get("aggregations", {}).get("entities", {}).get("buckets", []):
            entity = b["key"]
            rules = [rb["key"] for rb in b.get("rules", {}).get("buckets", [])]
            patterns.append({"entity_key": entity, "rules": rules, "count": b["doc_count"]})
        return patterns
    except Exception:
        return []
