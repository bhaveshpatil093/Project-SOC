import datetime
import psutil
import uuid
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

from app.ingestion.es_client_protocol import supports_index_management
from app.logging_config import get_logger
logger = get_logger(__name__)

@dataclass
class PlatformAlert:
    alert_id: str
    severity: str           # "critical" | "warning" | "info"
    component: str          # "elasticsearch" | "ingestion" | "scoring" | "slm" | "models"
    title: str
    description: str
    triggered_at: str       # ISO format string
    resolved_at: Optional[str]
    is_active: bool

class PlatformAlerter:
    INDEX_NAME = "soc-platform-alerts"

    ALERT_RULES = [
        {
            "rule_id": "PA-001",
            "name": "Ingestion Stopped",
            "check": lambda state: (datetime.datetime.utcnow() - state.get("last_ingestion", datetime.datetime.min)).total_seconds() > 600,
            "severity": "critical",
            "component": "ingestion",
            "description": "No ingestion cycle completed in the last 10 minutes"
        },
        {
            "rule_id": "PA-002",
            "name": "High Pipeline Error Rate",
            "check": lambda state: state.get("error_rate_5m", 0.0) > 0.1,
            "severity": "warning",
            "component": "ingestion",
            "description": "Pipeline error rate exceeds 10% in last 5 minutes"
        },
        {
            "rule_id": "PA-003",
            "name": "Elasticsearch Latency High",
            "check": lambda state: state.get("es_p95_latency_ms", 0) > 2000,
            "severity": "warning",
            "component": "elasticsearch",
            "description": "ES p95 query latency exceeds 2 seconds"
        },
        {
            "rule_id": "PA-004",
            "name": "SLM Unavailable",
            "check": lambda state: not state.get("slm_loaded", False),
            "severity": "warning",
            "component": "slm",
            "description": "SLM model is not loaded — investigation assistant unavailable"
        },
        {
            "rule_id": "PA-005",
            "name": "Model Drift Detected",
            "check": lambda state: state.get("max_psi_score", 0.0) > 0.2,
            "severity": "warning",
            "component": "models",
            "description": "Feature drift detected — model retraining recommended"
        },
        {
            "rule_id": "PA-006",
            "name": "Disk Space Low",
            "check": lambda state: state.get("disk_percent", 0.0) > 85,
            "severity": "critical",
            "component": "system",
            "description": "Disk usage exceeds 85% — backup and cleanup needed"
        },
        {
            "rule_id": "PA-007",
            "name": "Memory Pressure",
            "check": lambda state: state.get("memory_percent", 0.0) > 90,
            "severity": "critical",
            "component": "system",
            "description": "Memory usage exceeds 90%"
        },
        {
            "rule_id": "PA-008",
            "name": "No Models Loaded",
            "check": lambda state: state.get("models_loaded", 1) == 0,
            "severity": "critical",
            "component": "models",
            "description": "No ML models are loaded — all scoring disabled"
        },
    ]

    async def _ensure_index(self, es) -> None:
        if not supports_index_management(es):
            logger.debug(
                "platform_alerting_index_skipped",
                index=self.INDEX_NAME,
                reason="KibanaProxyClient does not support index management",
            )
            return
        try:
            if not await es.indices.exists(index=self.INDEX_NAME):
                await es.indices.create(index=self.INDEX_NAME, body={
                    "mappings": {
                        "properties": {
                            "alert_id": {"type": "keyword"},
                            "rule_id": {"type": "keyword"},
                            "severity": {"type": "keyword"},
                            "component": {"type": "keyword"},
                            "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                            "description": {"type": "text"},
                            "triggered_at": {"type": "date"},
                            "resolved_at": {"type": "date"},
                            "is_active": {"type": "boolean"}
                        }
                    }
                })
        except Exception as e:
            logger.error("failed_to_ensure_platform_alerts_index", error=str(e))

    async def collect_platform_state(self, es, model_manager, slm_engine) -> dict:
        """Collects state for all rule checks."""
        # Get ingestion stats from ES
        # This is a bit of a placeholder proxy for actual metrics fetching
        # In a real deployed app, we could query Prometheus via HTTP, but we'll approximate state
        last_ingestion = datetime.datetime.utcnow()
        try:
            res = await es.search(index="soc-ingestion-logs*", body={"size": 1, "sort": [{"@timestamp": "desc"}]})
            hits = res.get("hits", {}).get("hits", [])
            if hits:
                ts = hits[0]["_source"].get("@timestamp")
                if ts:
                    # simplistic parse
                    last_ingestion = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass

        disk_usage = psutil.disk_usage('/')
        mem_info = psutil.virtual_memory()

        state = {
            "last_ingestion": last_ingestion,
            "error_rate_5m": 0.0, # Mocked
            "es_p95_latency_ms": 100, # Mocked
            "slm_loaded": slm_engine is not None and getattr(slm_engine, "pipeline", None) is not None,
            "max_psi_score": 0.1, # Mocked
            "disk_percent": disk_usage.percent,
            "memory_percent": mem_info.percent,
            "models_loaded": len(model_manager.models) if model_manager else 0
        }
        return state

    async def get_active_platform_alerts(self, es) -> List[PlatformAlert]:
        """Fetch all currently active platform alerts."""
        try:
            await self._ensure_index(es)
            resp = await es.search(index=self.INDEX_NAME, body={
                "query": {"term": {"is_active": True}},
                "size": 100
            })
            hits = resp.get("hits", {}).get("hits", [])
            alerts = []
            for h in hits:
                s = h["_source"]
                alerts.append(PlatformAlert(
                    alert_id=s["alert_id"],
                    severity=s["severity"],
                    component=s["component"],
                    title=s["title"],
                    description=s["description"],
                    triggered_at=s["triggered_at"],
                    resolved_at=s.get("resolved_at"),
                    is_active=s["is_active"]
                ))
                # Bind rule_id manually
                alerts[-1].rule_id = s.get("rule_id")
            return alerts
        except Exception as e:
            logger.error("failed_to_fetch_active_platform_alerts", error=str(e))
            return []

    async def _update_alert_in_es(self, es, alert: dict):
        try:
            await self._ensure_index(es)
            await es.index(index=self.INDEX_NAME, id=alert["alert_id"], body=alert)
        except Exception as e:
            logger.error("failed_to_update_platform_alert", error=str(e), alert_id=alert.get("alert_id"))

    async def evaluate_rules(self, state: dict, active_alerts: List[PlatformAlert], es) -> List[dict]:
        active_rules = {getattr(a, "rule_id", None): a for a in active_alerts if getattr(a, "rule_id", None)}
        
        new_or_updated_alerts = []
        for rule in self.ALERT_RULES:
            rule_id = rule["rule_id"]
            try:
                is_triggered = rule["check"](state)
            except Exception as e:
                logger.error("rule_evaluation_failed", rule_id=rule_id, error=str(e))
                continue

            if is_triggered:
                if rule_id not in active_rules:
                    # Create new alert
                    alert = PlatformAlert(
                        alert_id=f"PA-{uuid.uuid4().hex[:8]}",
                        severity=rule["severity"],
                        component=rule["component"],
                        title=rule["name"],
                        description=rule["description"],
                        triggered_at=datetime.datetime.utcnow().isoformat() + "Z",
                        resolved_at=None,
                        is_active=True
                    )
                    alert_dict = asdict(alert)
                    alert_dict["rule_id"] = rule_id
                    new_or_updated_alerts.append(alert_dict)
            else:
                # Resolve if it was active
                if rule_id in active_rules:
                    alert = active_rules[rule_id]
                    alert_dict = asdict(alert)
                    alert_dict["rule_id"] = rule_id
                    alert_dict["is_active"] = False
                    alert_dict["resolved_at"] = datetime.datetime.utcnow().isoformat() + "Z"
                    new_or_updated_alerts.append(alert_dict)

        for alert in new_or_updated_alerts:
            await self._update_alert_in_es(es, alert)

        return new_or_updated_alerts

    async def run_alerting_cycle(self, es, model_manager, slm_engine):
        try:
            state = await self.collect_platform_state(es, model_manager, slm_engine)
            active_alerts = await self.get_active_platform_alerts(es)
            updated_alerts = await self.evaluate_rules(state, active_alerts, es)

            if updated_alerts:
                from app.api.routes.websocket import manager
                # Broadcast new active state
                current_active = await self.get_active_platform_alerts(es)
                await manager.broadcast({
                    "type": "platform_alerts_sync",
                    "data": [asdict(a) for a in current_active]
                })

                # Also broadcast individual events for toasts
                for a in updated_alerts:
                    if a["is_active"]:
                        await manager.broadcast({
                            "type": "platform_alert",
                            "data": a
                        })
        except Exception as e:
            logger.error("run_alerting_cycle_failed", error=str(e))
