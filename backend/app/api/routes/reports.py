from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.auth import require_role
from app.db.elasticsearch import get_es_client
from app.slm.engine import SLMEngine
from app.slm.shift_report import generate_shift_report

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/shift", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def fetch_shift_report(hours: int = Query(8, description="Hours for the shift window")):
    es = await get_es_client()
    slm_engine = SLMEngine()
    
    # In a real system, we might query the DB for the latest generated report.
    # Here, we generate it on-the-fly for the exact hour window requested,
    # or return the most recently scheduled one if we implemented caching.
    report = await generate_shift_report(es, slm_engine, shift_hours=hours)
    return {"data": report}

@router.get("/daily", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def fetch_daily_report():
    es = await get_es_client()
    slm_engine = SLMEngine()
    report = await generate_shift_report(es, slm_engine, shift_hours=24)
    return {"data": report}

@router.get("/weekly", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def fetch_weekly_report():
    es = await get_es_client()
    slm_engine = SLMEngine()
    report = await generate_shift_report(es, slm_engine, shift_hours=168)
    return {"data": report}
