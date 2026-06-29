from fastapi import APIRouter, Depends, Query

from app.auth.jwt import require_role
from app.feedback.label_store import (
    AnalystFeedback,
    get_all_feedback,
    get_fp_suppression_patterns,
    submit_feedback,
)
from app.feedback.suppressor import get_suppressor
from app.config import settings

router = APIRouter()

@router.post("", dependencies=[Depends(require_role("admin", "analyst"))])
async def post_feedback(feedback: AnalystFeedback):
    """Submits manual triage labels dropping mapped boundaries sequentially matching SQLite tables."""
    res = await submit_feedback(settings.DB_PATH, feedback)

    # Auto-triggers internal mappings dynamically refreshing memory buffers.
    suppressor = get_suppressor()
    await suppressor.refresh_suppression_list(settings.DB_PATH)

    return res

@router.get("")
async def fetch_feedback(label: str = Query(None), limit: int = Query(500)):
    res = await get_all_feedback(settings.DB_PATH, label=label, limit=limit)
    return {"data": res}

@router.get("/stats", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_stats():
    """Calculates active system efficacy identifying accurate TP vs FP suppression bounds."""
    try:
        all_fb = await get_all_feedback(settings.DB_PATH, limit=10000)
        total = len(all_fb)
        
        counts = {"TP": 0, "FP": 0, "Benign": 0}
        for fb in all_fb:
            l = fb.get("label")
            if l in counts:
                counts[l] += 1
                
        tp = counts["TP"]
        fp = counts["FP"]
        benign = counts["Benign"]
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
    patterns = await get_fp_suppression_patterns(settings.DB_PATH)
    stats = get_suppressor().get_suppression_stats()
    return {"patterns": patterns, "stats": stats}

from app.models.active_learner import ActiveLearner

active_learner = ActiveLearner()

@router.get("/labeling-queue", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_labeling_queue_api(n: int = Query(10, le=50)):
    """Returns prioritized list from get_labeling_queue"""
    queue = await active_learner.get_labeling_queue(settings.DB_PATH, n_samples=n)
    return {"data": queue}

@router.get("/labeling-stats", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_labeling_stats_api():
    """Returns stats from get_labeling_stats"""
    stats = await active_learner.get_labeling_stats(settings.DB_PATH)
    return {"data": stats}
