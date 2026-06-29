import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger
logger = get_logger(__name__)

SCHEDULE_INDEX = "soc-report-schedules"
REPORTS_INDEX = "soc-generated-reports"

FREQ_TO_HOURS = {
    "every_8h": 8,
    "daily": 24,
    "weekly": 168,
    "on_incident": None,
}

DEFAULT_SCHEDULES = [
    {
        "name": "8-Hour Shift Report",
        "report_type": "shift",
        "frequency": "every_8h",
        "format": "markdown",
        "recipients": [],
        "filters": {},
        "is_active": True,
    },
    {
        "name": "Daily Threat Summary",
        "report_type": "daily",
        "frequency": "daily",
        "format": "markdown",
        "recipients": [],
        "filters": {},
        "is_active": True,
    },
    {
        "name": "Weekly Threat Intel Digest",
        "report_type": "weekly",
        "frequency": "weekly",
        "format": "markdown",
        "recipients": [],
        "filters": {},
        "is_active": True,
    },
]


@dataclass
class ReportSchedule:
    schedule_id: str
    name: str
    report_type: str
    frequency: str
    recipients: List[str]
    format: str
    filters: Dict[str, Any]
    is_active: bool
    next_run: str
    last_run: Optional[str] = None


@dataclass
class GeneratedReport:
    report_id: str
    schedule_id: str
    generated_at: str
    report_type: str
    content_markdown: str
    content_json: Dict[str, Any]
    stats: Dict[str, Any]
    period_start: str
    period_end: str
    schedule_name: str = ""


class ReportScheduler:

    async def initialize(self, es):
        for idx in [SCHEDULE_INDEX, REPORTS_INDEX]:
            exists = await es.indices.exists(index=idx)
            if not exists:
                await es.indices.create(index=idx, body={
                    "mappings": {
                        "properties": {
                            "generated_at": {"type": "date"},
                            "period_start": {"type": "date"},
                            "period_end": {"type": "date"},
                            "next_run": {"type": "date"},
                            "last_run": {"type": "date"},
                            "is_active": {"type": "boolean"},
                        }
                    }
                })
                logger.info(f"Created index {idx}")

        # Create default schedules if none exist
        existing = await self.get_schedules(es)
        if not existing:
            now = datetime.utcnow()
            for s in DEFAULT_SCHEDULES:
                hours = FREQ_TO_HOURS.get(s["frequency"], 24) or 24
                schedule = ReportSchedule(
                    schedule_id=uuid.uuid4().hex,
                    next_run=(now + timedelta(hours=hours)).isoformat() + "Z",
                    **s,
                )
                await es.index(index=SCHEDULE_INDEX, id=schedule.schedule_id, body=asdict(schedule))
            logger.info("Created default report schedules")

    async def get_schedules(self, es) -> List[ReportSchedule]:
        try:
            resp = await es.search(
                index=SCHEDULE_INDEX,
                body={"query": {"match_all": {}}, "size": 50, "sort": [{"next_run": {"order": "asc"}}]},
                ignore_unavailable=True,
            )
            return [ReportSchedule(**h["_source"]) for h in resp.get("hits", {}).get("hits", [])]
        except Exception as e:
            logger.error(f"Error fetching schedules: {e}")
            return []

    async def create_schedule(self, es, schedule: ReportSchedule) -> ReportSchedule:
        await es.index(index=SCHEDULE_INDEX, id=schedule.schedule_id, body=asdict(schedule))
        return schedule

    async def update_schedule(self, es, schedule_id: str, updates: dict):
        await es.update(index=SCHEDULE_INDEX, id=schedule_id, body={"doc": updates})

    async def delete_schedule(self, es, schedule_id: str):
        await es.delete(index=SCHEDULE_INDEX, id=schedule_id, ignore=[404])

    async def get_reports(self, es, schedule_id: str = None, limit: int = 20) -> List[GeneratedReport]:
        try:
            query: Dict[str, Any] = {"match_all": {}}
            if schedule_id:
                query = {"term": {"schedule_id": schedule_id}}
            resp = await es.search(
                index=REPORTS_INDEX,
                body={"query": query, "size": limit, "sort": [{"generated_at": {"order": "desc"}}]},
                ignore_unavailable=True,
            )
            return [GeneratedReport(**h["_source"]) for h in resp.get("hits", {}).get("hits", [])]
        except Exception as e:
            logger.error(f"Error fetching reports: {e}")
            return []

    async def get_report(self, es, report_id: str) -> Optional[GeneratedReport]:
        try:
            resp = await es.get(index=REPORTS_INDEX, id=report_id, ignore=[404])
            if resp and resp.get("found"):
                return GeneratedReport(**resp["_source"])
            return None
        except Exception as e:
            logger.error(f"Error fetching report {report_id}: {e}")
            return None

    async def store_report(self, es, report: GeneratedReport):
        await es.index(index=REPORTS_INDEX, id=report.report_id, body=asdict(report))

    async def generate_report(self, es, schedule: ReportSchedule) -> GeneratedReport:
        """Generate report content from live Elasticsearch data."""
        now = datetime.utcnow()
        hours_back = FREQ_TO_HOURS.get(schedule.frequency, 24) or 24
        period_start = now - timedelta(hours=hours_back)

        since_iso = period_start.isoformat() + "Z"
        filters = schedule.filters or {}
        min_level = filters.get("min_threat_level", "")

        # --- Query alert stats ---
        level_agg_query = {
            "query": {
                "bool": {
                    "must": [{"range": {"timestamp": {"gte": since_iso}}}]
                }
            },
            "size": 0,
            "aggs": {
                "by_level": {"terms": {"field": "threat_level", "size": 10}},
                "by_status": {"terms": {"field": "alert_status", "size": 10}},
                "top_entities": {"terms": {"field": "entity_key", "size": 5}},
                "avg_score": {"avg": {"field": "threat_score"}},
            }
        }

        if min_level:
            level_order = {"low": ["low","medium","high","critical"], "medium": ["medium","high","critical"], "high": ["high","critical"], "critical": ["critical"]}
            level_filter = {"terms": {"threat_level": level_order.get(min_level, [])}}
            level_agg_query["query"]["bool"]["must"].append(level_filter)

        try:
            alert_resp = await es.search(index="soc-alerts", body=level_agg_query, ignore_unavailable=True)
        except Exception:
            alert_resp = {"hits": {"total": {"value": 0}}, "aggregations": {}}

        total_alerts = alert_resp.get("hits", {}).get("total", {}).get("value", 0)
        aggs = alert_resp.get("aggregations", {})

        by_level = {b["key"]: b["doc_count"] for b in aggs.get("by_level", {}).get("buckets", [])}
        by_status = {b["key"]: b["doc_count"] for b in aggs.get("by_status", {}).get("buckets", [])}
        top_entities = [{"entity": b["key"], "alert_count": b["doc_count"]} for b in aggs.get("top_entities", {}).get("buckets", [])]
        avg_score = round((aggs.get("avg_score", {}).get("value") or 0) * 100, 1)

        # --- Query incident stats ---
        try:
            inc_resp = await es.search(
                index="soc-incidents",
                body={
                    "query": {"range": {"created_at": {"gte": since_iso}}},
                    "size": 0,
                    "aggs": {
                        "by_stage": {"terms": {"field": "attack_stage", "size": 10}},
                        "multi_stage": {"filter": {"term": {"is_multi_stage": True}}},
                    }
                },
                ignore_unavailable=True
            )
            total_incidents = inc_resp.get("hits", {}).get("total", {}).get("value", 0)
            inc_aggs = inc_resp.get("aggregations", {})
            by_stage = {b["key"]: b["doc_count"] for b in inc_aggs.get("by_stage", {}).get("buckets", [])}
            multi_stage_count = inc_aggs.get("multi_stage", {}).get("doc_count", 0)
        except Exception:
            total_incidents = 0
            by_stage = {}
            multi_stage_count = 0

        # --- Build markdown ---
        period_label = {
            "shift": "Last 8 Hours",
            "daily": "Last 24 Hours",
            "weekly": "Last 7 Days",
        }.get(schedule.report_type, f"Last {hours_back}h")

        level_rows = "\n".join([
            f"| {lvl.capitalize()} | {cnt} |"
            for lvl, cnt in [("critical", by_level.get("critical", 0)), ("high", by_level.get("high", 0)), ("medium", by_level.get("medium", 0)), ("low", by_level.get("low", 0))]
        ])

        status_rows = "\n".join([f"| {st} | {cnt} |" for st, cnt in by_status.items()])
        entity_rows = "\n".join([f"| `{e['entity']}` | {e['alert_count']} |" for e in top_entities[:5]])
        stage_rows = "\n".join([f"| {st} | {cnt} |" for st, cnt in by_stage.items()]) or "| — | — |"

        content_markdown = f"""# {schedule.name}
**Period:** {period_label} ({period_start.strftime('%Y-%m-%d %H:%M')} UTC → {now.strftime('%Y-%m-%d %H:%M')} UTC)
**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S')} UTC

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Alerts | **{total_alerts}** |
| Avg Threat Score | **{avg_score}%** |
| Total Incidents | **{total_incidents}** |
| Multi-Stage Incidents | **{multi_stage_count}** |
| Open Alerts | **{by_status.get('open', 0)}** |
| Closed Alerts | **{by_status.get('closed', 0)}** |

---

## Alert Breakdown by Threat Level

| Level | Count |
|-------|-------|
{level_rows}

---

## Alert Status Distribution

| Status | Count |
|--------|-------|
{status_rows or "| — | — |"}

---

## Top 5 Most Active Entities

| Entity | Alerts |
|--------|--------|
{entity_rows or "| — | — |"}

---

## Incident Summary

| Attack Stage | Count |
|--------------|-------|
{stage_rows}

> **{multi_stage_count}** multi-stage attack chain(s) detected in this period.

---

## Recommendations

{"- ⚠️  **" + str(by_level.get('critical', 0)) + " critical alerts** require immediate analyst attention." if by_level.get('critical', 0) > 0 else "- ✅ No critical alerts in this period."}
{"- 🔁  " + str(multi_stage_count) + " multi-stage incident(s) suggest active threat campaigns — escalate to L2." if multi_stage_count > 0 else "- ✅ No multi-stage incidents detected."}
- 📊 Average threat score: **{avg_score}%** {"— elevated, review entity baselines." if avg_score > 60 else "— within acceptable range."}

---
*Report generated automatically by ISRO ISTRAC SOC Platform*
"""

        content_json = {
            "period": {"start": since_iso, "end": now.isoformat() + "Z"},
            "alerts": {
                "total": total_alerts,
                "by_level": by_level,
                "by_status": by_status,
                "avg_score_pct": avg_score,
                "top_entities": top_entities,
            },
            "incidents": {
                "total": total_incidents,
                "by_stage": by_stage,
                "multi_stage_count": multi_stage_count,
            },
        }

        stats = {
            "total_alerts": total_alerts,
            "critical_alerts": by_level.get("critical", 0),
            "total_incidents": total_incidents,
            "avg_score_pct": avg_score,
        }

        return GeneratedReport(
            report_id=uuid.uuid4().hex,
            schedule_id=schedule.schedule_id,
            schedule_name=schedule.name,
            generated_at=now.isoformat() + "Z",
            report_type=schedule.report_type,
            content_markdown=content_markdown,
            content_json=content_json,
            stats=stats,
            period_start=since_iso,
            period_end=now.isoformat() + "Z",
        )

    async def run_scheduled_reports(self, es):
        """Called hourly by APScheduler to check and run due schedules."""
        now = datetime.utcnow()
        schedules = await self.get_schedules(es)

        for sched in schedules:
            if not sched.is_active:
                continue
            if sched.frequency == "on_incident":
                continue

            try:
                next_run_dt = datetime.fromisoformat(sched.next_run.replace("Z", ""))
            except Exception:
                continue

            if next_run_dt <= now:
                try:
                    report = await self.generate_report(es, sched)
                    await self.store_report(es, report)

                    hours = FREQ_TO_HOURS.get(sched.frequency, 24) or 24
                    new_next = (now + timedelta(hours=hours)).isoformat() + "Z"

                    await self.update_schedule(es, sched.schedule_id, {
                        "last_run": now.isoformat() + "Z",
                        "next_run": new_next,
                    })
                    logger.info(f"Generated scheduled report: {sched.name} → {report.report_id}")
                except Exception as e:
                    logger.error(f"Failed to generate report for schedule {sched.schedule_id}: {e}")


report_scheduler = ReportScheduler()
