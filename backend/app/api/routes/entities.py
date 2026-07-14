from app.monitoring.audit_logger import audit_action
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.jwt import require_role
from app.ingestion.kibana_client import KibanaProxyClient
from app.scoring.entity_risk import EntityRiskScorer
from app.scoring.score_history import get_score_history, get_score_trends, get_system_score_trends

router = APIRouter()
scorer = EntityRiskScorer()

class WatchlistRequest(BaseModel):
    reason: str

@router.get("", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_entities(limit: int = Query(50, ge=1, le=200)):
    es = KibanaProxyClient()
    entities = await scorer.get_top_risk_entities(es, n=limit)
    return {"data": entities}

@router.get("/watchlist", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_watchlist():
    es = KibanaProxyClient()
    entities = await scorer.get_watchlist(es)
    return {"data": entities}

@router.get("/{entity_key}", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_entity_profile(entity_key: str):
    es = KibanaProxyClient()
    profile = await scorer.get_or_create_profile(es, entity_key)
    return {"data": profile}

@router.get("/{entity_key}/alerts", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_entity_alerts(entity_key: str, limit: int = Query(50, ge=1, le=100)):
    es = KibanaProxyClient()
    try:
        query = {
            "size": limit,
            "sort": [{"timestamp": {"order": "desc"}}],
            "query": {"term": {"entity_key.keyword": entity_key}}
        }
        res = await es.search(index="soc-processed-alerts", body=query, ignore_unavailable=True)
        alerts = [hit["_source"] for hit in res.get("hits", {}).get("hits", [])]
        return {"data": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{entity_key}/watchlist", dependencies=[Depends(require_role("admin", "analyst"))])
async def add_entity_watchlist(entity_key: str, req: WatchlistRequest):
    es = KibanaProxyClient()
    await scorer.add_to_watchlist(es, entity_key, req.reason)
    return {"status": "success", "message": f"Added {entity_key} to watchlist"}

@router.delete("/{entity_key}/watchlist", dependencies=[Depends(require_role("admin", "analyst"))])
async def remove_entity_watchlist(entity_key: str):
    es = KibanaProxyClient()
    await scorer.remove_from_watchlist(es, entity_key)
    return {"status": "success", "message": f"Removed {entity_key} from watchlist"}

@router.get("/system/trends", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_system_trends():
    es = KibanaProxyClient()
    trends = await get_system_score_trends(es)
    return {"data": trends}

@router.get("/{entity_key}/score-history", dependencies=[Depends(require_role("admin", "analyst"))])
async def entity_score_history(entity_key: str, since_hours: int = 168):
    es = KibanaProxyClient()
    history = await get_score_history(es, entity_key, since_hours)
    return {"data": history}

@router.get("/{entity_key}/score-trends", dependencies=[Depends(require_role("admin", "analyst"))])
async def entity_score_trends(entity_key: str):
    es = KibanaProxyClient()
    trends = await get_score_trends(es, entity_key)
    return {"data": trends}
