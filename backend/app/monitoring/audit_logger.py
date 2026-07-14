import uuid
import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from contextvars import ContextVar

from app.ingestion.es_client_protocol import supports_index_management
from app.logging_config import get_logger
logger = get_logger(__name__)

@dataclass
class AuditEvent:
    event_id: str               # UUID
    timestamp: str              # ISO format string
    user: str                   # analyst username
    role: str
    action: str                 # see ACTION_TYPES below
    resource_type: str          # "alert" | "incident" | "feedback" | "model" | "system"
    resource_id: Optional[str]
    details: Dict[str, Any]     # Action-specific details
    ip_address: str
    user_agent: str
    correlation_id: str         # From request middleware
    result: str                 # "success" | "failure" | "unauthorized"

ACTION_TYPES = {
    "alert.view", "alert.status_change", "alert.export",
    "feedback.submit", "feedback.view",
    "slm.chat", "slm.explain_alert",
    "incident.view", "incident.escalate", "incident.report_generate",
    "training.start", "training.retrain",
    "admin.backup_create", "admin.backup_restore",
    "admin.model_reload", "admin.rag_reindex",
    "auth.login", "auth.logout", "auth.login_failed",
    "entity.watchlist_add", "entity.watchlist_remove",
}

class AuditLogger:
    INDEX_NAME = "soc-audit-log"

    async def _ensure_index(self, es) -> None:
        if not supports_index_management(es):
            logger.debug(
                "audit_logger_index_skipped",
                index=self.INDEX_NAME,
                reason="KibanaProxyClient does not support index management",
            )
            return
        try:
            if not await es.indices.exists(index=self.INDEX_NAME):
                await es.indices.create(index=self.INDEX_NAME, body={
                    "mappings": {
                        "properties": {
                            "event_id": {"type": "keyword"},
                            "timestamp": {"type": "date"},
                            "user": {"type": "keyword"},
                            "role": {"type": "keyword"},
                            "action": {"type": "keyword"},
                            "resource_type": {"type": "keyword"},
                            "resource_id": {"type": "keyword"},
                            "details": {"type": "object"},
                            "ip_address": {"type": "ip"},
                            "user_agent": {"type": "text"},
                            "correlation_id": {"type": "keyword"},
                            "result": {"type": "keyword"}
                        }
                    }
                })
        except Exception as e:
            logger.error("failed_to_ensure_audit_index", error=str(e))

    async def log(self, es, event: AuditEvent):
        try:
            await self._ensure_index(es)
            doc = asdict(event)
            # if IP is missing or not a valid IP string, elasticsearch mapping might fail
            if not doc["ip_address"] or doc["ip_address"] == "unknown":
                doc["ip_address"] = "0.0.0.0"
            await es.index(index=self.INDEX_NAME, body=doc)
        except Exception as e:
            logger.error("failed_to_log_audit_event", error=str(e))

    async def get_audit_trail(self, es, user: str = None, action: str = None, resource_id: str = None, since_hours: int = 24) -> List[AuditEvent]:
        try:
            await self._ensure_index(es)
            must_clauses = []
            if user:
                must_clauses.append({"term": {"user": user}})
            if action:
                must_clauses.append({"term": {"action": action}})
            if resource_id:
                must_clauses.append({"term": {"resource_id": resource_id}})
            
            since_time = (datetime.datetime.utcnow() - datetime.timedelta(hours=since_hours)).isoformat() + "Z"
            must_clauses.append({"range": {"timestamp": {"gte": since_time}}})

            query = {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}

            resp = await es.search(index=self.INDEX_NAME, body={
                "query": query,
                "sort": [{"timestamp": "desc"}],
                "size": 1000
            })
            
            events = []
            for hit in resp.get("hits", {}).get("hits", []):
                s = hit["_source"]
                events.append(AuditEvent(**s))
            return events
        except Exception as e:
            logger.error("failed_to_get_audit_trail", error=str(e))
            return []

    async def get_user_activity(self, es, user: str, since_days: int = 7) -> dict:
        try:
            await self._ensure_index(es)
            since_time = (datetime.datetime.utcnow() - datetime.timedelta(days=since_days)).isoformat() + "Z"
            resp = await es.search(index=self.INDEX_NAME, body={
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"user": user}},
                            {"range": {"timestamp": {"gte": since_time}}}
                        ]
                    }
                },
                "aggs": {
                    "actions_by_type": {
                        "terms": {"field": "action", "size": 100}
                    }
                },
                "size": 0
            })
            
            total_actions = resp.get("hits", {}).get("total", {}).get("value", 0)
            buckets = resp.get("aggregations", {}).get("actions_by_type", {}).get("buckets", [])
            action_counts = {b["key"]: b["doc_count"] for b in buckets}
            
            return {
                "total_actions": total_actions,
                "alerts_triaged": action_counts.get("alert.status_change", 0),
                "feedback_submitted": action_counts.get("feedback.submit", 0),
                "slm_queries": action_counts.get("slm.chat", 0),
                "active_hours": 0 # Would require more complex date_histogram agg
            }
        except Exception as e:
            logger.error("failed_to_get_user_activity", error=str(e))
            return {}

# Context variables to hold request-scoped info
audit_context_user = ContextVar("audit_context_user", default="system")
audit_context_role = ContextVar("audit_context_role", default="system")
audit_context_ip = ContextVar("audit_context_ip", default="127.0.0.1")
audit_context_ua = ContextVar("audit_context_ua", default="unknown")
audit_context_corr = ContextVar("audit_context_corr", default="N/A")

audit_logger_instance = AuditLogger()

async def audit_action(action: str, resource_type: str, resource_id: str = None, details: dict = None, result: str = "success"):
    """
    Helper to be called from any route to log an action automatically using context variables.
    """
    from app.ingestion.kibana_client import KibanaProxyClient
    try:
        es = KibanaProxyClient()
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            user=audit_context_user.get(),
            role=audit_context_role.get(),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=audit_context_ip.get(),
            user_agent=audit_context_ua.get(),
            correlation_id=audit_context_corr.get(),
            result=result
        )
        await audit_logger_instance.log(es, event)
    except Exception as e:
        logger.error("audit_action_error", error=str(e))
