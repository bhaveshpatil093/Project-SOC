import os

with open("backend/app/api/routes/admin.py", "r") as f:
    content = f.read()

import_stmt = """
from app.monitoring.log_viewer import log_viewer_instance
from typing import Optional
"""
content = content.replace("from typing import List, Dict, Any", "from typing import List, Dict, Any, Optional")
if "log_viewer_instance" not in content:
    content = content.replace("from fastapi import APIRouter, Depends", "from fastapi import APIRouter, Depends, Query\n" + import_stmt)

routes = """
@router.get("/logs", dependencies=[Depends(require_role("admin"))])
async def get_logs(
    level: Optional[str] = None,
    component: Optional[str] = None,
    since_minutes: int = Query(60, ge=1),
    limit: int = Query(100, le=1000)
):
    try:
        es = await get_es_client()
        logs = await log_viewer_instance.get_recent_logs(es, level, component, since_minutes, limit)
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch logs")

@router.get("/logs/errors", dependencies=[Depends(require_role("admin"))])
async def get_log_errors(since_hours: int = Query(24, ge=1)):
    try:
        es = await get_es_client()
        summary = await log_viewer_instance.get_error_summary(es, since_hours)
        return {"error_summary": summary}
    except Exception as e:
        logger.error(f"Error fetching log errors: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch log errors")

@router.get("/logs/search", dependencies=[Depends(require_role("admin"))])
async def search_logs(q: str, since_hours: int = Query(24, ge=1), limit: int = Query(100, le=1000)):
    try:
        es = await get_es_client()
        logs = await log_viewer_instance.search_logs(es, q, since_hours, limit)
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error searching logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to search logs")

@router.get("/logs/trace/{correlation_id}", dependencies=[Depends(require_role("admin"))])
async def get_log_trace(correlation_id: str):
    try:
        es = await get_es_client()
        trace = await log_viewer_instance.get_correlation_trace(es, correlation_id)
        return {"trace": trace}
    except Exception as e:
        logger.error(f"Error fetching log trace: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch log trace")
"""

content += "\n" + routes

with open("backend/app/api/routes/admin.py", "w") as f:
    f.write(content)
