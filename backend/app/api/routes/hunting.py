import time
import uuid
import datetime
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from app.auth.jwt import get_current_user, require_role
from app.ingestion.es_client import get_es_client

logger = logging.getLogger(__name__)
router = APIRouter()

HUNT_RESULTS_INDEX = "soc-hunt-results"
HUNT_SAVED_INDEX = "soc-hunt-saved"


class HuntRequest(BaseModel):
    hunt_type: str  # ioc_search | pattern_search | entity_search | custom_query
    parameters: Dict[str, Any]
    time_range_days: int = 30


class SaveHuntRequest(BaseModel):
    name: str
    description: str
    hunt_request: Dict[str, Any]


async def _build_es_query(hunt_request: HuntRequest, user: dict) -> dict:
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=hunt_request.time_range_days)).isoformat() + "Z"
    params = hunt_request.parameters
    hunt_type = hunt_request.hunt_type

    base_time_filter = {"range": {"timestamp": {"gte": since}}}

    if hunt_type == "ioc_search":
        ioc_type = params.get("ioc_type", "ip")
        ioc_value = params.get("ioc_value", "")
        field_map = {
            "ip": ["src_ip", "dst_ip", "host_ip"],
            "process": ["process_name", "process_image"],
            "domain": ["dns_query", "domain", "url"],
        }
        fields = field_map.get(ioc_type, ["message"])
        should_clauses = [{"match": {f: ioc_value}} for f in fields]
        should_clauses.append({"multi_match": {"query": ioc_value, "fields": ["message", "raw_log"]}})
        return {
            "query": {"bool": {"must": [base_time_filter], "should": should_clauses, "minimum_should_match": 1}},
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": 200,
        }

    elif hunt_type == "pattern_search":
        pattern_id = params.get("pattern_id", "")
        pattern_map = {
            "PAT-001": {"mitre_technique_ids": "T1078"},  # Valid Accounts
            "PAT-002": {"mitre_technique_ids": "T1110"},  # Brute Force
            "PAT-003": {"mitre_technique_ids": "T1059"},  # Command & Scripting
            "PAT-004": {"mitre_technique_ids": "T1055"},  # Process Injection
            "PAT-005": {"log_type": "network_anomaly"},
        }
        pattern_filter = pattern_map.get(pattern_id, {})
        must_clauses = [base_time_filter]
        for k, v in pattern_filter.items():
            must_clauses.append({"match": {k: v}})
        return {
            "query": {"bool": {"must": must_clauses}},
            "sort": [{"threat_score": {"order": "desc"}}],
            "size": 200,
        }

    elif hunt_type == "entity_search":
        entity_key = params.get("entity_key", "")
        include_archived = params.get("include_archived", False)
        must_clauses = [base_time_filter, {"match": {"entity_key": entity_key}}]
        if not include_archived:
            must_clauses.append({"terms": {"alert_status": ["open", "in_progress"]}})
        return {
            "query": {"bool": {"must": must_clauses}},
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": 500,
        }

    elif hunt_type == "custom_query":
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Custom ES queries require admin role")
        return params.get("es_query", {"query": {"match_all": {}}, "size": 100})

    else:
        raise HTTPException(status_code=400, detail=f"Unknown hunt_type: {hunt_type}")


@router.post("/search")
async def run_hunt(
    request: Request,
    hunt_request: HuntRequest,
    user: dict = Depends(get_current_user),
):
    start_ms = time.time() * 1000
    hunt_id = uuid.uuid4().hex

    try:
        es = await get_es_client()
        query = await _build_es_query(hunt_request, user)

        # Search across both logs and alerts
        indices = ["soc-alerts"]
        try:
            resp = await es.search(index=",".join(indices), body=query, ignore_unavailable=True)
        except Exception as e:
            logger.error(f"ES hunt query failed: {e}")
            resp = {"hits": {"hits": [], "total": {"value": 0}}}

        hits = resp.get("hits", {}).get("hits", [])
        total = resp.get("hits", {}).get("total", {}).get("value", 0)
        results = [{"_id": h["_id"], **h["_source"]} for h in hits]

        # Compute top_findings (unique entities with highest threat scores)
        entity_scores: dict = {}
        for r in results:
            ek = r.get("entity_key", r.get("host_id", "unknown"))
            ts = r.get("threat_score", 0)
            if ek not in entity_scores or entity_scores[ek] < ts:
                entity_scores[ek] = ts

        top_findings = sorted(
            [{"entity_key": k, "max_threat_score": v} for k, v in entity_scores.items()],
            key=lambda x: x["max_threat_score"],
            reverse=True,
        )[:10]

        query_time_ms = int(time.time() * 1000 - start_ms)

        # Persist hunt results
        hunt_doc = {
            "hunt_id": hunt_id,
            "user": user["username"],
            "hunt_type": hunt_request.hunt_type,
            "parameters": hunt_request.parameters,
            "time_range_days": hunt_request.time_range_days,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "results_count": total,
            "query_time_ms": query_time_ms,
            "top_findings": top_findings,
            "results": results[:500],  # Cap stored results
        }

        await es.index(index=HUNT_RESULTS_INDEX, id=hunt_id, body=hunt_doc, ignore_unavailable=True)

        return {
            "hunt_id": hunt_id,
            "results_count": total,
            "top_findings": top_findings,
            "query_time_ms": query_time_ms,
            "results": results[:50],  # Return first 50 immediately
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hunt failed: {e}")
        raise HTTPException(status_code=500, detail=f"Hunt failed: {str(e)}")


@router.get("/{hunt_id}/results")
async def get_hunt_results(
    hunt_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    user: dict = Depends(get_current_user),
):
    try:
        es = await get_es_client()
        resp = await es.get(index=HUNT_RESULTS_INDEX, id=hunt_id, ignore=[404])
        if not resp or not resp.get("found"):
            raise HTTPException(status_code=404, detail="Hunt not found")

        hunt = resp["_source"]
        results = hunt.get("results", [])
        return {
            "hunt_id": hunt_id,
            "hunt_type": hunt.get("hunt_type"),
            "created_at": hunt.get("created_at"),
            "results_count": hunt.get("results_count"),
            "top_findings": hunt.get("top_findings", []),
            "results": results[offset : offset + limit],
            "total": len(results),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching hunt results: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch hunt results")


@router.get("/saved")
async def get_saved_hunts(user: dict = Depends(get_current_user)):
    try:
        es = await get_es_client()
        resp = await es.search(
            index=HUNT_SAVED_INDEX,
            body={"query": {"match_all": {}}, "sort": [{"created_at": {"order": "desc"}}], "size": 50},
            ignore_unavailable=True,
        )
        hunts = [{"_id": h["_id"], **h["_source"]} for h in resp.get("hits", {}).get("hits", [])]
        return {"saved_hunts": hunts}
    except Exception as e:
        logger.error(f"Error fetching saved hunts: {e}")
        return {"saved_hunts": []}


@router.post("/save")
async def save_hunt(
    payload: SaveHuntRequest,
    user: dict = Depends(get_current_user),
):
    try:
        es = await get_es_client()
        doc = {
            "name": payload.name,
            "description": payload.description,
            "hunt_request": payload.hunt_request,
            "created_by": user["username"],
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "last_run": None,
            "last_match_count": None,
        }
        resp = await es.index(index=HUNT_SAVED_INDEX, body=doc)
        return {"id": resp["_id"], **doc}
    except Exception as e:
        logger.error(f"Error saving hunt: {e}")
        raise HTTPException(status_code=500, detail="Failed to save hunt")


@router.delete("/saved/{hunt_id}")
async def delete_saved_hunt(
    hunt_id: str,
    user: dict = Depends(get_current_user),
):
    try:
        es = await get_es_client()
        await es.delete(index=HUNT_SAVED_INDEX, id=hunt_id, ignore=[404])
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Error deleting saved hunt: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete saved hunt")
