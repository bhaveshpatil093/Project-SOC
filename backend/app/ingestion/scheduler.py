import asyncio
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.ingestion.kibana_client import KibanaProxyClient
from app.logging_config import get_logger

logger = get_logger(__name__)

# In-memory state tracking
scheduler_state = {
    "last_run": None,
    "docs_last_cycle": 0,
    "status": "stopped"
}

_scheduler: AsyncIOScheduler | None = None

def get_window_bucket(ts: datetime, window_minutes: int = 5) -> datetime:
    """Floors a timestamp to the nearest window_minutes."""
    minute = (ts.minute // window_minutes) * window_minutes
    return ts.replace(minute=minute, second=0, microsecond=0)

async def run_ingestion_cycle(kibana_client: KibanaProxyClient):
    """Core cycle: fetches logs via proxy, normalizes, extracts features, runs threat models, and stores to SQLite."""
    try:
        logger.info("ingestion_cycle_started")

        from app.api.routes.websocket import manager
        now_iso = datetime.utcnow().isoformat() + "Z"
        await manager.broadcast({
            "type": "ingestion_started",
            "data": {"timestamp": now_iso}
        })
        
        await manager.broadcast({
            "type": "scoring_started",
            "data": {"timestamp": now_iso}
        })

        from app.scoring.threat_engine import get_threat_engine
        engine = get_threat_engine()
        scoring_stats = await engine.run_scoring_cycle(since_minutes=5)

        # Update in-memory state
        scheduler_state["last_run"] = datetime.utcnow().isoformat() + "Z"
        scheduler_state["docs_last_cycle"] = scoring_stats["scored"]

        # Broadcast completions
        now_iso = datetime.utcnow().isoformat() + "Z"
        await manager.broadcast({
            "type": "scoring_complete",
            "data": {
                "scored": scoring_stats["scored"], "critical": scoring_stats["critical"],
                "high": scoring_stats["high"], "medium": scoring_stats["medium"],
                "low": scoring_stats["low"], "cycle_time_ms": scoring_stats["cycle_time_ms"],
                "timestamp": now_iso
            }
        })
        await manager.broadcast({
            "type": "ingestion_complete",
            "data": {"docs_fetched": scoring_stats["scored"], "docs_indexed": scoring_stats["alerts_above_threshold"], "timestamp": now_iso}
        })

        logger.info("ingestion_cycle_completed",
                    docs_scored=scoring_stats["scored"],
                    alerts_generated=scoring_stats["alerts_above_threshold"],
                    critical=scoring_stats["critical"])

    except Exception as e:
        logger.error("ingestion_cycle_failed", error=str(e))

async def broadcast_stats(kibana_client: KibanaProxyClient):
    try:
        from app.api.routes.websocket import manager
        from app.storage import local_db
        from app.config import settings

        import aiosqlite
        async with aiosqlite.connect(settings.DB_PATH) as db:
            async with db.execute("SELECT threat_level, COUNT(*) FROM soc_alerts WHERE alert_status = 'open' GROUP BY threat_level") as cursor:
                rows = await cursor.fetchall()
                counts = {r[0]: r[1] for r in rows}
                
                stats = {
                    "critical": counts.get("critical", 0),
                    "high": counts.get("high", 0),
                    "medium": counts.get("medium", 0),
                    "low": counts.get("low", 0),
                    "total": sum(counts.values())
                }

        await manager.broadcast({
            "type": "stats_update",
            "data": stats
        })
    except Exception as e:
        logger.error("broadcast_stats_failed", error=str(e))

async def run_drift_detection():
    logger.info("run_drift_detection_started")
    try:
        from app.models.model_manager import get_model_manager
        kibana_client = KibanaProxyClient()
        mm = get_model_manager()
        res = await mm.detect_drift(kibana_client)
        logger.info("drift_detection_completed", **res)
    except Exception as e:
        logger.error("drift_detection_failed", error=str(e))

async def run_platform_alerting():
    logger.info("run_platform_alerting_started")
    try:
        from app.models.model_manager import get_model_manager
        from app.slm.model_loader import get_slm_engine
        from app.monitoring.platform_alerting import PlatformAlerter
        kibana_client = KibanaProxyClient()
        mm = get_model_manager()
        slm = get_slm_engine()
        alerter = PlatformAlerter()
        await alerter.run_alerting_cycle(kibana_client, mm, slm)
        logger.info("run_platform_alerting_completed")
    except Exception as e:
        logger.error("run_platform_alerting_failed", error=str(e))

async def start_scheduler(kibana_client: KibanaProxyClient):
    """Starts the APScheduler background ingestion job."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        run_ingestion_cycle,
        trigger=IntervalTrigger(minutes=5),
        args=[kibana_client],
        id="ingestion_pipeline",
        replace_existing=True
    )

    from app.reports.report_scheduler import report_scheduler
    _scheduler.add_job(
        report_scheduler.run_scheduled_reports,
        trigger=CronTrigger(minute=0),
        args=[kibana_client],
        id="scheduled_reports",
        replace_existing=True
    )

    _scheduler.add_job(
        broadcast_stats,
        trigger=IntervalTrigger(seconds=60),
        args=[kibana_client],
        id="stats_broadcast",
        replace_existing=True
    )

    _scheduler.add_job(
        run_platform_alerting,
        IntervalTrigger(minutes=2),
        id="platform_alerting",
        replace_existing=True,
    )

    from app.models.model_manager import get_model_manager
    from app.models.trainer import run_incremental_retraining

    async def retrain_job():
        mm = get_model_manager()
        from app.config import settings
        await run_incremental_retraining(kibana_client, mm, settings.DB_PATH)

    _scheduler.add_job(
        retrain_job,
        trigger=CronTrigger(day_of_week='sun', hour=2, minute=0),
        id="incremental_retraining",
        replace_existing=True
    )

    from app.slm.conversation_manager import get_conversation_manager

    async def cleanup_conversations_job():
        cm = get_conversation_manager()
        cm.cleanup_expired()

    _scheduler.add_job(
        cleanup_conversations_job,
        trigger=IntervalTrigger(hours=1),
        id="cleanup_conversations",
        replace_existing=True
    )

    from app.models.drift_detector import get_drift_detector

    async def check_drift_job():
        drift_detector = get_drift_detector()
        await drift_detector.run_drift_check(kibana_client)

    _scheduler.add_job(
        check_drift_job,
        trigger=IntervalTrigger(hours=6),
        id="drift_detection",
        replace_existing=True
    )

    _scheduler.start()

    from app.cache.cache_manager import cache

    async def clear_cache_job():
        await cache.clear_expired()

    _scheduler.add_job(
        clear_cache_job,
        trigger=IntervalTrigger(minutes=5),
        id="clear_expired_cache",
        replace_existing=True
    )

    from app.backup.backup_manager import BackupManager

    async def daily_backup_job():
        bm = BackupManager()
        await bm.create_local_backup()

    _scheduler.add_job(
        daily_backup_job,
        trigger=CronTrigger(hour=21, minute=0),
        id="daily_backup",
        replace_existing=True
    )

    try:
        from scripts.cleanup import CleanupManager
        async def weekly_cleanup_job():
            manager = CleanupManager()
            safe_ops = ["audit_logs", "score_history", "chromadb_entries", "conversations", "cache"]
            await manager.run_full_cleanup(dry_run=False, execute_only=safe_ops)
            
        _scheduler.add_job(
            weekly_cleanup_job,
            trigger=CronTrigger(day_of_week='sun', hour=1, minute=0),
            id="weekly_cleanup",
            replace_existing=True
        )
    except ImportError:
        logger.warning("weekly_cleanup_job_skipped", reason="scripts.cleanup module not found")

    from app.monitoring.sla_tracker import sla_tracker_instance
    from app.api.routes.websocket import manager as ws_manager

    async def check_sla_breaches_job():
        try:
            approaching = await sla_tracker_instance.get_alerts_approaching_sla(kibana_client, warning_minutes=10)
            if approaching:
                await ws_manager.broadcast({
                    "type": "sla_warning",
                    "data": approaching
                })
        except Exception as e:
            logger.error(f"Error in check_sla_breaches_job: {e}")

    _scheduler.add_job(
        check_sla_breaches_job,
        trigger=IntervalTrigger(minutes=5),
        id="check_sla_breaches",
        replace_existing=True
    )

    scheduler_state["status"] = "running"
    logger.info("scheduler_started", job="ingestion_pipeline", interval="5_minutes")

async def stop_scheduler():
    """Stops the ingestion scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
        scheduler_state["status"] = "stopped"
        logger.info("scheduler_stopped")
