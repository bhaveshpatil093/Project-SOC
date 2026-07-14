import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.ingestion.kibana_client import KibanaProxyClient
from app.models.model_manager import get_model_manager
from app.slm.model_loader import get_slm_engine
from app.slm.rag_pipeline import get_rag_pipeline


@dataclass
class ComponentHealth:
    name: str
    status: str          # "healthy" | "degraded" | "unhealthy"
    latency_ms: float
    details: dict[str, Any]
    last_checked: datetime = field(default_factory=lambda: datetime.now(UTC))

class HealthChecker:
    async def check_elasticsearch(self) -> ComponentHealth:
        start = time.time()
        status = "healthy"
        details = {}
        try:
            es = KibanaProxyClient()
            connected = await es.check_connection()
            latency = (time.time() - start) * 1000
            if connected:
                details = {"kibana_url": es.base_url, "mode": "kibana_proxy"}
            else:
                status = "unhealthy"
                details = {"error": "Kibana check_connection returned False", "kibana_url": es.base_url}
            if latency > 1000:
                status = "degraded"
        except Exception as e:
            latency = (time.time() - start) * 1000
            status = "unhealthy"
            details = {"error": str(e)}

        return ComponentHealth(name="elasticsearch", status=status, latency_ms=latency, details=details)

    async def check_models(self) -> ComponentHealth:
        start = time.time()
        status = "healthy"
        details = {}
        try:
            mm = get_model_manager()
            loaded = len(mm.models)
            details = {"models_loaded": loaded, "models": list(mm.models.keys())}
            if loaded == 0:
                status = "degraded"
        except Exception as e:
            status = "unhealthy"
            details = {"error": str(e)}
        latency = (time.time() - start) * 1000
        return ComponentHealth(name="ml_models", status=status, latency_ms=latency, details=details)

    async def check_slm(self) -> ComponentHealth:
        start = time.time()
        status = "healthy"
        details = {}
        try:
            slm = get_slm_engine()
            details["is_loaded"] = slm.is_loaded()
            if not slm.is_loaded():
                status = "degraded"
                details["error"] = "SLM Engine is offline"
            else:
                # tiny test
                gen = slm.generate("Hello", max_new_tokens=5)
                details["test_output"] = gen
        except Exception as e:
            status = "unhealthy"
            details["error"] = str(e)

        latency = (time.time() - start) * 1000
        if status == "healthy" and latency > 5000:
            status = "degraded"

        return ComponentHealth(name="slm_engine", status=status, latency_ms=latency, details=details)

    async def check_rag(self) -> ComponentHealth:
        start = time.time()
        status = "healthy"
        details = {}
        try:
            rag = get_rag_pipeline()
            stats = await rag.get_index_stats()
            details = stats
            if stats.get("total_indexed", 0) == 0:
                status = "degraded"
                details["warning"] = "RAG collection is empty"
        except Exception as e:
            status = "unhealthy"
            details = {"error": str(e)}
        latency = (time.time() - start) * 1000
        return ComponentHealth(name="rag_pipeline", status=status, latency_ms=latency, details=details)

    async def check_scheduler(self) -> ComponentHealth:
        start = time.time()
        status = "healthy"
        details = {}
        try:
            from app.ingestion.scheduler import _scheduler, scheduler_state
            is_running = _scheduler is not None and _scheduler.running
            details["is_running"] = is_running

            last_run = scheduler_state.get("last_run")
            details["last_run"] = last_run
            details["status"] = scheduler_state.get("status", "unknown")
            details["docs_last_cycle"] = scheduler_state.get("docs_last_cycle", 0)

            if last_run:
                diff = (datetime.now(UTC) - datetime.fromisoformat(last_run.replace('Z', '+00:00'))).total_seconds()
                if diff > 600:  # 10 minutes
                    status = "degraded"
                    details["warning"] = "Last ingestion cycle was over 10 minutes ago."
            else:
                status = "degraded"
                details["warning"] = "No ingestion cycle has run yet."

            if not is_running:
                status = "degraded"

        except Exception as e:
            status = "unhealthy"
            details = {"error": str(e)}
        latency = (time.time() - start) * 1000
        return ComponentHealth(name="ingestion_scheduler", status=status, latency_ms=latency, details=details)

    async def run_all_checks(self) -> dict[str, Any]:
        results = await asyncio.gather(
            self.check_elasticsearch(),
            self.check_models(),
            self.check_slm(),
            self.check_rag(),
            self.check_scheduler()
        )

        overall = "healthy"
        for r in results:
            if r.status == "unhealthy":
                overall = "unhealthy"
                break
            if r.status == "degraded":
                overall = "degraded"

        return {
            "status": overall,
            "components": [
                {
                    "name": r.name,
                    "status": r.status,
                    "latency_ms": r.latency_ms,
                    "details": r.details,
                    "last_checked": r.last_checked.isoformat()
                }
                for r in results
            ]
        }
