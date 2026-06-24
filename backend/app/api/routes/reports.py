import uuid
import logging
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.jwt import get_current_user, require_role
from app.ingestion.es_client import get_es_client
from app.reports.report_scheduler import (
    report_scheduler,
    ReportSchedule,
    FREQ_TO_HOURS
)

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateScheduleRequest(BaseModel):
    name: str
    report_type: str
    frequency: str
    format: str = "markdown"
    recipients: List[str] = []
    filters: Dict[str, Any] = {}
    is_active: bool = True

from pydantic import BaseModel

@router.get("/schedules", dependencies=[Depends(require_role("admin"))])
async def list_schedules():
    try:
        es = await get_es_client()
        schedules = await report_scheduler.get_schedules(es)
        return {"schedules": [vars(s) for s in schedules]}
    except Exception as e:
        logger.error(f"Error listing schedules: {e}")
        raise HTTPException(status_code=500, detail="Failed to list schedules")


@router.post("/schedules", dependencies=[Depends(require_role("admin"))])
async def create_schedule(payload: CreateScheduleRequest):
    try:
        es = await get_es_client()
        now = datetime.utcnow()
        hours = FREQ_TO_HOURS.get(payload.frequency, 24) or 24
        
        schedule = ReportSchedule(
            schedule_id=uuid.uuid4().hex,
            name=payload.name,
            report_type=payload.report_type,
            frequency=payload.frequency,
            format=payload.format,
            recipients=payload.recipients,
            filters=payload.filters,
            is_active=payload.is_active,
            next_run=(now + timedelta(hours=hours)).isoformat() + "Z",
        )
        created = await report_scheduler.create_schedule(es, schedule)
        return {"schedule": vars(created)}
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create schedule")


@router.post("/schedules/{schedule_id}/run-now", dependencies=[Depends(require_role("admin"))])
async def run_schedule_now(schedule_id: str):
    try:
        es = await get_es_client()
        schedules = await report_scheduler.get_schedules(es)
        sched = next((s for s in schedules if s.schedule_id == schedule_id), None)
        
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule not found")
            
        report = await report_scheduler.generate_report(es, sched)
        await report_scheduler.store_report(es, report)
        
        # Update last run, but don't advance next_run for manual triggers unless we want to
        now = datetime.utcnow().isoformat() + "Z"
        await report_scheduler.update_schedule(es, schedule_id, {"last_run": now})
        
        return {"status": "success", "report_id": report.report_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to run schedule")


@router.get("/generated", dependencies=[Depends(require_role("admin"))])
async def list_generated_reports():
    try:
        es = await get_es_client()
        reports = await report_scheduler.get_reports(es)
        # Exclude massive content from list view
        return {
            "reports": [
                {k: v for k, v in vars(r).items() if k not in ("content_markdown", "content_json")}
                for r in reports
            ]
        }
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail="Failed to list reports")


@router.get("/generated/{report_id}", dependencies=[Depends(require_role("admin"))])
async def get_generated_report(report_id: str):
    try:
        es = await get_es_client()
        report = await report_scheduler.get_report(es, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return {"report": vars(report)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching report {report_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch report")
