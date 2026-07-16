"""
Health Checker
==============
Provides structured health checks for all SOC platform components.
Reports HEALTHY, DEGRADED, or UNHEALTHY for each subsystem.

The pipeline is only reported as HEALTHY when:
  ✓ Kibana is reachable
  ✓ Storage (SQLite) is working
  ✓ Ingestion scheduler is running and has completed at least one cycle
  ✓ At least one ML model is loaded (or rule engine is active)

Otherwise reports DEGRADED with informative details.
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.ingestion.kibana_client import KibanaProxyClient
from app.models.model_manager import get_model_manager


@dataclass
class ComponentHealth:
    name: str
    status: str          # "healthy" | "degraded" | "unhealthy"
    latency_ms: float
    details: dict[str, Any]
    last_checked: datetime = field(default_factory=lambda: datetime.now(UTC))


class HealthChecker:

    async def check_elasticsearch(self) -> ComponentHealth:
        """Checks Kibana proxy connectivity."""
        start = time.time()
        status = "healthy"
        details = {}
        try:
            es = KibanaProxyClient()
            connected = await es.check_connection()
            latency = (time.time() - start) * 1000
            if connected:
                details = {"kibana_url": settings_url(), "mode": "kibana_proxy", "connected": True}
            else:
                status = "unhealthy"
                details = {
                    "error": "Kibana check_connection returned False",
                    "kibana_url": settings_url(),
                    "hint": "Ensure KIBANA_URL uses http:// not https://",
                }
            if latency > 1000:
                status = "degraded"
                details["warning"] = "Kibana response latency is high (>1s)"
        except Exception as e:
            latency = (time.time() - start) * 1000
            status = "unhealthy"
            details = {"error": str(e)}

        return ComponentHealth(name="kibana_proxy", status=status, latency_ms=latency, details=details)

    async def check_models(self) -> ComponentHealth:
        """Checks which ML models are loaded in ModelManager."""
        start = time.time()
        status = "healthy"
        details = {}
        try:
            mm = get_model_manager()

            # ModelManager uses individual attributes, not a dict.
            loaded_models = []
            if mm.if_detector is not None:
                loaded_models.append("isolation_forest")
            if mm.ae_detector is not None:
                loaded_models.append("autoencoder")
            if mm.lstm_detector is not None:
                loaded_models.append("lstm")

            # Rule engine is always active (deterministic, no model file needed)
            loaded_models.append("rule_engine")

            details = {
                "models_loaded": len(loaded_models),
                "models": loaded_models,
                "ml_models_available": len(loaded_models) - 1,  # exclude rule_engine
                "rule_engine_active": True,
            }

            if len(loaded_models) == 1:
                # Only rule engine, no ML models — degraded but functional
                status = "degraded"
                details["warning"] = "No ML models loaded. Operating on rule engine only."
        except Exception as e:
            status = "unhealthy"
            details = {"error": str(e)}

        latency = (time.time() - start) * 1000
        return ComponentHealth(name="ml_models", status=status, latency_ms=latency, details=details)

    async def check_slm(self) -> ComponentHealth:
        """Checks if the SLM (Small Language Model) engine is loaded."""
        start = time.time()
        status = "healthy"
        details = {}
        try:
            from app.slm.model_loader import get_slm_engine
            slm = get_slm_engine()
            details["is_loaded"] = slm.is_loaded()
            if not slm.is_loaded():
                status = "degraded"
                details["warning"] = "SLM Engine is offline — chat features unavailable"
        except Exception as e:
            status = "degraded"  # SLM failure is non-critical
            details["error"] = str(e)
            details["warning"] = "SLM Engine failed to load — chat features unavailable"

        latency = (time.time() - start) * 1000
        return ComponentHealth(name="slm_engine", status=status, latency_ms=latency, details=details)

    async def check_rag(self) -> ComponentHealth:
        """Checks the RAG pipeline index status."""
        start = time.time()
        status = "healthy"
        details = {}
        try:
            from app.slm.rag_pipeline import get_rag_pipeline
            rag = get_rag_pipeline()
            stats = await rag.get_index_stats()
            details = stats
            if stats.get("total_indexed", 0) == 0:
                status = "degraded"
                details["warning"] = "RAG collection is empty — investigation context unavailable"
        except Exception as e:
            status = "degraded"  # RAG failure is non-critical
            details = {"error": str(e), "warning": "RAG pipeline unavailable"}

        latency = (time.time() - start) * 1000
        return ComponentHealth(name="rag_pipeline", status=status, latency_ms=latency, details=details)

    async def check_scheduler(self) -> ComponentHealth:
        """Checks the ingestion scheduler status and last run time."""
        start = time.time()
        status = "healthy"
        details = {}
        try:
            from app.ingestion.scheduler import _scheduler, scheduler_state
            is_running = _scheduler is not None and _scheduler.running
            details["is_running"] = is_running
            details["scheduler_status"] = scheduler_state.get("status", "unknown")
            details["docs_last_cycle"] = scheduler_state.get("docs_last_cycle", 0)

            last_run = scheduler_state.get("last_run")
            details["last_run"] = last_run

            if last_run:
                diff = (datetime.now(UTC) - datetime.fromisoformat(last_run.replace("Z", "+00:00"))).total_seconds()
                details["seconds_since_last_run"] = int(diff)
                if diff > 600:  # 10 minutes
                    status = "degraded"
                    details["warning"] = f"Last ingestion cycle was {int(diff/60)} minutes ago (expected every 5 min)."
            else:
                status = "degraded"
                details["warning"] = "No ingestion cycle has run yet — waiting for first cycle."

            if not is_running:
                status = "degraded"
                details["warning"] = details.get("warning", "") + " Scheduler is not running."

        except Exception as e:
            status = "unhealthy"
            details = {"error": str(e)}

        latency = (time.time() - start) * 1000
        return ComponentHealth(name="ingestion_scheduler", status=status, latency_ms=latency, details=details)

    async def check_storage(self) -> ComponentHealth:
        """Checks that SQLite storage is accessible and contains the expected tables."""
        start = time.time()
        status = "healthy"
        details = {}
        try:
            from app.config import settings
            import aiosqlite

            db_exists = os.path.exists(settings.DB_PATH)
            details["db_path"] = settings.DB_PATH
            details["db_exists"] = db_exists

            if not db_exists:
                status = "unhealthy"
                details["error"] = f"SQLite database file not found at {settings.DB_PATH}"
            else:
                async with aiosqlite.connect(settings.DB_PATH) as db:
                    async with db.execute("SELECT COUNT(*) FROM soc_alerts") as cursor:
                        row = await cursor.fetchone()
                        details["total_alerts_stored"] = row[0] if row else 0

                    async with db.execute("SELECT COUNT(*) FROM soc_feedback") as cursor:
                        row = await cursor.fetchone()
                        details["total_feedback_stored"] = row[0] if row else 0

        except Exception as e:
            status = "unhealthy"
            details["error"] = str(e)

        latency = (time.time() - start) * 1000
        return ComponentHealth(name="sqlite_storage", status=status, latency_ms=latency, details=details)

    async def run_all_checks(self) -> dict[str, Any]:
        results = await asyncio.gather(
            self.check_elasticsearch(),
            self.check_models(),
            self.check_slm(),
            self.check_rag(),
            self.check_scheduler(),
            self.check_storage(),
            return_exceptions=False,
        )

        overall = "healthy"
        for r in results:
            if isinstance(r, Exception):
                overall = "unhealthy"
                break
            if r.status == "unhealthy":
                overall = "unhealthy"
                break
            if r.status == "degraded":
                overall = "degraded"

        return {
            "status": overall,
            "timestamp": datetime.now(UTC).isoformat(),
            "components": [
                {
                    "name": r.name,
                    "status": r.status,
                    "latency_ms": round(r.latency_ms, 2),
                    "details": r.details,
                    "last_checked": r.last_checked.isoformat(),
                }
                for r in results
                if not isinstance(r, Exception)
            ],
        }


def settings_url() -> str:
    """Helper to avoid circular import."""
    try:
        from app.config import settings
        return settings.KIBANA_URL
    except Exception:
        return "unknown"
