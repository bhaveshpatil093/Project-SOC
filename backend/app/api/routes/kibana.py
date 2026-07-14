"""
Kibana & ES proxy routes for the frontend.
Provides safe, read-only access to Kibana data and index information.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.jwt import require_role
from app.ingestion.kibana_client import KibanaProxyClient
from app.config import settings

router = APIRouter(tags=["kibana"])


@router.get("/kibana/url", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_kibana_url():
    """Returns the Kibana base URL for deeplink generation in the frontend."""
    return {"url": settings.KIBANA_URL, "available": True}


@router.get("/es/indices", dependencies=[Depends(require_role("admin", "analyst"))])
async def list_es_indices():
    """
    Returns doc counts for each known Kibana data stream by searching with size=0.
    KibanaProxyClient does not support es.cat.indices, so we query each index directly.
    """
    es = KibanaProxyClient()
    known_indices = [
        "logs-system.syslog-*",
        "logs-endpoint.events.process-*",
        "logs-windows.powershell_operational-*",
    ]
    results = []
    for idx in known_indices:
        try:
            resp = await es.search(
                index=idx,
                body={"size": 0, "track_total_hits": True, "query": {"match_all": {}}},
            )
            doc_count = resp.get("hits", {}).get("total", {}).get("value", 0)
            results.append({"name": idx, "health": "green", "doc_count": doc_count, "size_bytes": None})
        except Exception:
            results.append({"name": idx, "health": "red", "doc_count": 0, "size_bytes": None})
    return {"data": results}


def _validate_no_scripts(query_dict: dict):
    """Recursively checks for script injections in query."""
    for k, v in query_dict.items():
        if k in ["script", "script_fields"]:
            raise ValueError("Scripting is forbidden for security reasons.")
        if isinstance(v, dict):
            _validate_no_scripts(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    _validate_no_scripts(item)


class ESQueryRequest(BaseModel):
    index: str
    query: dict
    size: int = Field(10, le=100)
    sort: list = []


# Known safe indices — extended for the current Kibana data streams
_SAFE_INDICES = {
    "logs-system.syslog-*",
    "logs-endpoint.events.process-*",
    "logs-windows.powershell_operational-*",
    "soc-*",
}


@router.post("/es/query", dependencies=[Depends(require_role("admin", "analyst"))])
async def run_es_query(req: ESQueryRequest):
    """Executes a safe, read-only ES query via Kibana proxy."""
    # Validate index is whitelisted
    if not any(req.index == idx or req.index.startswith(idx.rstrip("*")) for idx in _SAFE_INDICES):
        raise HTTPException(status_code=403, detail="Index not whitelisted for direct query.")

    try:
        _validate_no_scripts(req.query)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    es = KibanaProxyClient()
    body: dict = {"query": req.query, "size": req.size}
    if req.sort:
        body["sort"] = req.sort

    try:
        res = await es.search(index=req.index, body=body)
        return {"data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
