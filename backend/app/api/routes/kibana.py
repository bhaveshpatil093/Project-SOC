from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
import json
import os

from app.api.auth import require_role
from app.db.elasticsearch import get_es_client, INDEX_NAMES

router = APIRouter(tags=["kibana", "es"])

class ESQueryRequest(BaseModel):
    index: str
    query: dict
    size: int = Field(10, le=100)
    sort: list = []

@router.get("/kibana/url", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_kibana_url():
    url = os.environ.get("KIBANA_URL", "http://localhost:5601")
    return {"url": url, "available": True}

@router.get("/es/indices", dependencies=[Depends(require_role("admin", "analyst"))])
async def list_es_indices():
    es = await get_es_client()
    try:
        # Fetch stats for all soc- prefixed indices
        stats = await es.cat.indices(index="soc-*", format="json")
        indices = []
        for s in stats:
            indices.append({
                "name": s.get("index"),
                "health": s.get("health"),
                "doc_count": s.get("docs.count"),
                "size_bytes": s.get("store.size")
            })
        return {"data": indices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _validate_no_scripts(query_dict: dict):
    # Recursively check for script or script_fields to prevent injection
    for k, v in query_dict.items():
        if k in ["script", "script_fields"]:
            raise ValueError("Scripting is forbidden in explicit ES queries for security reasons.")
        if isinstance(v, dict):
            _validate_no_scripts(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    _validate_no_scripts(item)

@router.post("/es/query", dependencies=[Depends(require_role("admin", "analyst"))])
async def run_es_query(req: ESQueryRequest):
    # 1. Validate Index Whitelist
    if req.index not in INDEX_NAMES.values() and req.index != "soc-*":
        raise HTTPException(status_code=403, detail="Index not whitelisted for direct query.")
        
    # 2. Validate No Scripts
    try:
        _validate_no_scripts(req.query)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
        
    # 3. Execute
    es = await get_es_client()
    body = {
        "query": req.query,
        "size": req.size
    }
    if req.sort:
        body["sort"] = req.sort
        
    try:
        res = await es.search(index=req.index, body=body)
        return {"data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
