from fastapi import APIRouter, Depends, Query

from app.auth.jwt import require_role
from app.feedback.label_store import (
    FEEDBACK_INDEX,
    AnalystFeedback,
    get_all_feedback,
    get_fp_suppression_patterns,
    submit_feedback,
)
from app.feedback.suppressor import get_suppressor
from app.ingestion.es_client import get_es_client

router = APIRouter()

@router.post("", dependencies=[Depends(require_role("admin", "analyst"))])
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

@router.get("/stats", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
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

@router.get("/suppressed", dependencies=[Depends(require_role("admin", "analyst"))])
async def fetch_suppression_rules():
    """Generates transparency exposing tracking metrics identifying blocked mapping entities."""
    es = await get_es_client()
    patterns = await get_fp_suppression_patterns(es)
    stats = get_suppressor().get_suppression_stats()
    return {"patterns": patterns, "stats": stats}

from app.models.active_learner import ActiveLearner

active_learner = ActiveLearner()

@router.get("/labeling-queue", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_labeling_queue_api(n: int = Query(10, le=50)):
    """Returns prioritized list from get_labeling_queue"""
    es = await get_es_client()
    queue = await active_learner.get_labeling_queue(es, n_samples=n)
    return {"data": queue}

@router.get("/labeling-stats", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_labeling_stats_api():
    """Returns stats from get_labeling_stats"""
    es = await get_es_client()
    stats = await active_learner.get_labeling_stats(es)
    return {"data": stats}
