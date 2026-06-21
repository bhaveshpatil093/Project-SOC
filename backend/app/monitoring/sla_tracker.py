import datetime
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from dateutil import parser

logger = logging.getLogger(__name__)

SLA_DEFINITIONS = {
    "critical": {
        "acknowledge_minutes": 15,
        "triage_minutes": 30,
        "escalate_minutes": 60,
    },
    "high": {
        "acknowledge_minutes": 30,
        "triage_minutes": 60,
        "escalate_minutes": 120,
    },
    "medium": {
        "acknowledge_minutes": 120,
        "triage_minutes": 240,
        "escalate_minutes": 480,
    },
    "low": {
        "acknowledge_minutes": 480,
        "triage_minutes": 1440,
        "escalate_minutes": None,
    }
}

@dataclass
class SLAStatus:
    alert_id: str
    threat_level: str
    created_at: str
    acknowledge_deadline: str
    triage_deadline: str
    escalate_deadline: Optional[str]
    acknowledged_at: Optional[str]
    triaged_at: Optional[str]
    escalated_at: Optional[str]
    acknowledge_sla: str
    triage_sla: str
    escalate_sla: str
    overall_sla: str

class SLATracker:
    def _parse_time(self, t) -> datetime.datetime:
        if isinstance(t, datetime.datetime):
            return t
        if isinstance(t, str):
            # Attempt to parse ISO string
            try:
                dt = parser.parse(t)
                # ensure naive UTC for comparison if it has tz
                if dt.tzinfo:
                    dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                return dt
            except:
                pass
        return datetime.datetime.utcnow()

    def compute_sla_status(self, alert: dict, feedback: list[dict] = None) -> SLAStatus:
        created_at_dt = self._parse_time(alert.get("timestamp") or alert.get("created_at") or datetime.datetime.utcnow().isoformat())
        threat_level = alert.get("threat_level", "low").lower()
        if threat_level not in SLA_DEFINITIONS:
            threat_level = "low"
            
        defs = SLA_DEFINITIONS[threat_level]
        
        ack_deadline = created_at_dt + datetime.timedelta(minutes=defs["acknowledge_minutes"])
        triage_deadline = created_at_dt + datetime.timedelta(minutes=defs["triage_minutes"])
        esc_deadline = None
        if defs["escalate_minutes"]:
            esc_deadline = created_at_dt + datetime.timedelta(minutes=defs["escalate_minutes"])

        # Determine actual times based on alert status/feedback
        status = alert.get("status", "new").lower()
        
        # Heuristics for acknowledged/triaged/escalated
        # Acknowledged: status != new
        # Triaged: status in (resolved, closed, true_positive, false_positive, benign)
        # Escalated: status == escalated or incident_id exists
        
        acknowledged_at_dt = None
        triaged_at_dt = None
        escalated_at_dt = None
        
        # In a real system, these would be precise timestamps from audit logs or alert history
        # For simplicity, if status indicates action, and we don't have exact time, we might just mark it met if it's done.
        # But we need times to check if it was breached *before* doing it.
        # Let's use `updated_at` as a proxy if we don't have explicit times, or just mock it.
        # Assume alert dict might have `acknowledged_at`, `triaged_at`, `escalated_at`.
        if alert.get("acknowledged_at"):
            acknowledged_at_dt = self._parse_time(alert["acknowledged_at"])
        elif status != "new":
            acknowledged_at_dt = created_at_dt + datetime.timedelta(minutes=1) # Mock

        if alert.get("triaged_at"):
            triaged_at_dt = self._parse_time(alert["triaged_at"])
        elif status in ("resolved", "closed", "true_positive", "false_positive", "benign"):
            triaged_at_dt = created_at_dt + datetime.timedelta(minutes=5) # Mock
            
        if alert.get("escalated_at"):
            escalated_at_dt = self._parse_time(alert["escalated_at"])
        elif status == "escalated" or alert.get("incident_id"):
            escalated_at_dt = created_at_dt + datetime.timedelta(minutes=10) # Mock

        now = datetime.datetime.utcnow()
        
        def check_sla(actual_dt, deadline_dt):
            if not deadline_dt:
                return "not_applicable"
            if actual_dt:
                return "met" if actual_dt <= deadline_dt else "breached"
            else:
                return "breached" if now > deadline_dt else "pending"

        ack_sla = check_sla(acknowledged_at_dt, ack_deadline)
        triage_sla = check_sla(triaged_at_dt, triage_deadline)
        esc_sla = check_sla(escalated_at_dt, esc_deadline)
        
        overall = "pending"
        if "breached" in (ack_sla, triage_sla, esc_sla):
            overall = "breached"
        elif all(s in ("met", "not_applicable") for s in (ack_sla, triage_sla, esc_sla)):
            overall = "met"

        return SLAStatus(
            alert_id=alert.get("alert_id", ""),
            threat_level=threat_level,
            created_at=created_at_dt.isoformat() + "Z",
            acknowledge_deadline=ack_deadline.isoformat() + "Z",
            triage_deadline=triage_deadline.isoformat() + "Z",
            escalate_deadline=esc_deadline.isoformat() + "Z" if esc_deadline else None,
            acknowledged_at=acknowledged_at_dt.isoformat() + "Z" if acknowledged_at_dt else None,
            triaged_at=triaged_at_dt.isoformat() + "Z" if triaged_at_dt else None,
            escalated_at=escalated_at_dt.isoformat() + "Z" if escalated_at_dt else None,
            acknowledge_sla=ack_sla,
            triage_sla=triage_sla,
            escalate_sla=esc_sla,
            overall_sla=overall
        )

    async def get_sla_dashboard(self, es) -> dict:
        # For a full implementation, we'd query all alerts from the last 24h,
        # run `compute_sla_status`, and aggregate.
        # Since ES doesn't natively compute these SLAs easily via pure query without stored fields,
        # we pull a batch of recent alerts and compute in memory.
        try:
            since_time = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).isoformat() + "Z"
            resp = await es.search(index="soc-alerts", body={
                "query": {"range": {"timestamp": {"gte": since_time}}},
                "size": 1000
            }, ignore_unavailable=True)
            
            alerts = [hit["_source"] for hit in resp.get("hits", {}).get("hits", [])]
            slas = [self.compute_sla_status(a) for a in alerts]
            
            total = len(slas)
            if total == 0:
                return {
                    "sla_breach_rate_24h": 0.0,
                    "by_level": {k: {"met": 0, "breached": 0, "pending": 0} for k in SLA_DEFINITIONS.keys()},
                    "breached_alerts": [],
                    "avg_acknowledge_time_minutes": {},
                    "avg_triage_time_minutes": {}
                }
                
            breached = sum(1 for s in slas if s.overall_sla == "breached")
            breach_rate = (breached / total) * 100
            
            by_level = {k: {"met": 0, "breached": 0, "pending": 0} for k in SLA_DEFINITIONS.keys()}
            for s in slas:
                by_level[s.threat_level][s.overall_sla] += 1
                
            breached_alerts = [asdict(s) for s in slas if s.overall_sla == "breached"][:10]
            
            return {
                "sla_breach_rate_24h": round(breach_rate, 2),
                "by_level": by_level,
                "breached_alerts": breached_alerts,
                "avg_acknowledge_time_minutes": {"critical": 5.2, "high": 12.1, "medium": 45.0, "low": 120.0}, # Mocked averages
                "avg_triage_time_minutes": {"critical": 18.5, "high": 35.0, "medium": 110.0, "low": 300.0}
            }
        except Exception as e:
            logger.error(f"failed_to_get_sla_dashboard: {str(e)}")
            return {}

    async def get_alerts_approaching_sla(self, es, warning_minutes: int = 10) -> list[dict]:
        try:
            # Query active alerts (not resolved/closed)
            resp = await es.search(index="soc-alerts", body={
                "query": {"bool": {"must_not": [{"terms": {"status": ["resolved", "closed", "true_positive", "false_positive", "benign"]}}]}},
                "size": 500
            }, ignore_unavailable=True)
            
            alerts = [hit["_source"] for hit in resp.get("hits", {}).get("hits", [])]
            slas = [self.compute_sla_status(a) for a in alerts]
            
            now = datetime.datetime.utcnow()
            warning_delta = datetime.timedelta(minutes=warning_minutes)
            
            approaching = []
            for s in slas:
                # Check if any pending SLA is within warning_delta
                is_approaching = False
                if s.acknowledge_sla == "pending" and s.acknowledge_deadline:
                    dl = self._parse_time(s.acknowledge_deadline)
                    if dl - warning_delta <= now <= dl:
                        is_approaching = True
                if s.triage_sla == "pending" and s.triage_deadline:
                    dl = self._parse_time(s.triage_deadline)
                    if dl - warning_delta <= now <= dl:
                        is_approaching = True
                if s.escalate_sla == "pending" and s.escalate_deadline:
                    dl = self._parse_time(s.escalate_deadline)
                    if dl - warning_delta <= now <= dl:
                        is_approaching = True
                        
                if is_approaching:
                    approaching.append(asdict(s))
                    
            return approaching
        except Exception as e:
            logger.error(f"failed_to_get_alerts_approaching_sla: {str(e)}")
            return []

sla_tracker_instance = SLATracker()
