from fastapi import APIRouter, HTTPException, Depends
from typing import Any
from app.ingestion.es_client import get_es_client, INDEX_NAMES
from app.features.feature_merger import run_feature_pipeline, store_feature_vectors
from app.auth.jwt import require_role
from app.cache.cache_manager import cache_result

router = APIRouter(dependencies=[Depends(require_role("admin", "analyst"))])

@router.get("/api/features/run")
async def run_features_manually():
    """Triggers run_feature_pipeline manually."""
    try:
        es = await get_es_client()
        merged_df, _ = await run_feature_pipeline(es, since_minutes=5)
        if merged_df.empty:
            return {"entities_processed": 0, "window": "None", "top_entities": []}
            
        await store_feature_vectors(es, merged_df)
        
        if 'conn_per_minute' in merged_df.columns:
            top_df = merged_df.nlargest(5, 'conn_per_minute')
        else:
            top_df = merged_df.head(5)
            
        top_entities = top_df['entity_key'].tolist() if 'entity_key' in top_df.columns else []
        window = merged_df['window_bucket'].iloc[0] if 'window_bucket' in merged_df.columns else "unknown"
        
        return {
            "entities_processed": len(merged_df),
            "window": window,
            "top_entities": top_entities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/features/latest")
async def get_latest_features():
    """Queries soc-feature-vectors for most recent window_bucket, returns up to 100 records."""
    try:
        es = await get_es_client()
        query = {
            "query": {"match_all": {}},
            "sort": [{"window_bucket": {"order": "desc"}}],
            "size": 100
        }
        resp = await es.search(index=INDEX_NAMES["features"], body=query, ignore_unavailable=True)
        hits = resp.get("hits", {}).get("hits", [])
        return {"records": [hit["_source"] for hit in hits]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/features/{entity_key}")
@cache_result(ttl_seconds=120, key_fn=lambda entity_key: f"features:{entity_key}")
async def get_entity_features(entity_key: str):
    """Returns feature vector history for entity (last 24h)."""
    try:
        es = await get_es_client()
        query = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"entity_key": entity_key}},
                        {"range": {"window_bucket": {"gte": "now-24h"}}}
                    ]
                }
            },
            "sort": [{"window_bucket": {"order": "desc"}}],
            "size": 288
        }
        resp = await es.search(index=INDEX_NAMES["features"], body=query, ignore_unavailable=True)
        hits = resp.get("hits", {}).get("hits", [])
        return {"records": [hit["_source"] for hit in hits]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
