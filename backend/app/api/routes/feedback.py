from fastapi import APIRouter, HTTPException, Query
from app.feedback.label_store import AnalystFeedback, submit_feedback, get_all_feedback, get_fp_suppression_patterns, FEEDBACK_INDEX
from app.feedback.suppressor import get_suppressor
from app.ingestion.es_client import get_es_client, INDEX_NAMES

router = APIRouter()

@router.post("")
async def post_feedback(feedback: AnalystFeedback):
    """Submits manual triage labels dropping mapped boundaries sequentially matching ES indices."""
    es = await get_es_client()
    res = await submit_feedback(es, feedback)
    
    # Auto-triggers internal mappings dynamically refreshing memory buffers.
    suppressor = get_suppressor()
    await suppressor.refresh_suppression_list(es)
    
    return res

@router.get("")
async def fetch_feedback(label: str = Query(None), limit: int = Query(500)):
    es = await get_es_client()
    res = await get_all_feedback(es, label=label, limit=limit)
    return {"data": res}

@router.get("/stats")
async def get_stats():
    """Calculates active system efficacy identifying accurate TP vs FP suppression bounds."""
    es = await get_es_client()
    query = {
        "size": 0,
        "aggs": {
            "labels": {
                "terms": {"field": "label.keyword"}
            }
        }
    }
    try:
        resp = await es.search(index=FEEDBACK_INDEX, body=query, ignore_unavailable=True)
        buckets = resp.get("aggregations", {}).get("labels", {}).get("buckets", [])
        counts = {b["key"]: b["doc_count"] for b in buckets}
        total = sum(counts.values())
        
        tp = counts.get("TP", 0)
        fp = counts.get("FP", 0)
        benign = counts.get("Benign", 0)
        fp_rate = fp / total if total > 0 else 0.0
        
        return {
            "TP": tp,
            "FP": fp,
            "Benign": benign,
            "total": total,
            "fp_rate": round(fp_rate, 3)
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/suppression-rules")
async def fetch_suppression_rules():
    """Generates transparency exposing tracking metrics identifying blocked mapping entities."""
    es = await get_es_client()
    patterns = await get_fp_suppression_patterns(es)
    stats = get_suppressor().get_suppression_stats()
    return {"patterns": patterns, "stats": stats}
