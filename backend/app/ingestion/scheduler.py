from dataclasses import asdict
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from app.ingestion.es_client import INDEX_NAMES
from app.ingestion.log_fetcher import fetch_all_sources
from app.ingestion.normalizer import normalize_batch
from app.logging_config import get_logger

logger = get_logger(__name__)

# In-memory state tracking
scheduler_state = {
    "last_run": None,
    "docs_last_cycle": 0,
    "status": "stopped"
}

_scheduler: AsyncIOScheduler | None = None

import asyncio
import time


async def bulk_index(es: AsyncElasticsearch, docs: list[dict], index: str, chunk_size: int = 500) -> dict[str, Any]:
    """Bulk index documents into Elasticsearch with batching and concurrent optimization."""
    if not docs:
        return {"indexed": 0, "errors": []}

    start_time = time.time()
    total_indexed = 0
    all_errors = []

    # Split docs into chunks
    chunks = [docs[i:i + chunk_size] for i in range(0, len(docs), chunk_size)]

    # Process chunks concurrently with max 3 concurrent
    semaphore = asyncio.Semaphore(3)

    async def process_chunk(chunk):
        async with semaphore:
            actions = [
                {
                    "_index": index,
                    "_source": doc
                }
                for doc in chunk
            ]

            try:
                success, failed = await async_bulk(
                    es, actions, stats_only=False, raise_on_error=False, raise_on_exception=False
                )

                chunk_errors = []
                if failed:
                    for item in failed:
                        chunk_errors.append(item)

                # Log warning if errors > 5%
                if len(chunk_errors) > len(chunk) * 0.05:
                    logger.warning("bulk_index_high_error_rate", chunk_size=len(chunk), errors=len(chunk_errors))

                return success, chunk_errors
            except Exception as e:
                logger.error("bulk_indexing_chunk_exception", error=str(e))
                return 0, [str(e)] * len(chunk)

    results = await asyncio.gather(*(process_chunk(chunk) for chunk in chunks))

    for success, errors in results:
        total_indexed += success
        all_errors.extend(errors)

    elapsed = time.time() - start_time
    logger.info("bulk_index_completed", total=len(docs), indexed=total_indexed, errors=len(all_errors), time_seconds=round(elapsed, 2))

    return {"indexed": total_indexed, "errors": all_errors}

def get_window_bucket(ts: datetime, window_minutes: int = 5) -> datetime:
    """Floors a timestamp to the nearest window_minutes."""
    minute = (ts.minute // window_minutes) * window_minutes
    return ts.replace(minute=minute, second=0, microsecond=0)

async def run_ingestion_cycle(es: AsyncElasticsearch):
    """Core ingestion cycle: fetch -> normalize -> enrich -> index."""
    try:
        logger.info("ingestion_cycle_started")

        from app.api.routes.websocket import manager
        now_iso = datetime.utcnow().isoformat() + "Z"
        await manager.broadcast({
            "type": "ingestion_started",
            "data": {"timestamp": now_iso}
        })

        # a. Fetch logs
        raw_results = await fetch_all_sources(es, since_minutes=5)

        all_enriched_docs = []
        total_fetched = 0
        total_normalized = 0

        # b. Normalize
        for log_type, raw_docs in raw_results.items():
            total_fetched += len(raw_docs)
            normalized_logs = normalize_batch(raw_docs, log_type)
            total_normalized += len(normalized_logs)

            now_utc = datetime.utcnow()

            # c. Add derived fields
            for log in normalized_logs:
                doc = asdict(log)
                doc["ingested_at"] = now_utc.isoformat() + "Z"
                doc["window_bucket"] = get_window_bucket(log.timestamp).isoformat() + "Z"

                user = log.user_name or "system"
                doc["entity_key"] = f"{log.host_id}|{user}"

                if isinstance(log.timestamp, datetime):
                    doc["timestamp"] = log.timestamp.isoformat() + "Z"

                all_enriched_docs.append(doc)

        # d. Bulk Index
        target_index = INDEX_NAMES["alerts_processed"]
        index_result = await bulk_index(es, all_enriched_docs, target_index)

        # e. Run Full Threat Scoring Engine (encapsulates feature pipeline inherently)
        now_iso = datetime.utcnow().isoformat() + "Z"
        await manager.broadcast({
            "type": "scoring_started",
            "data": {"timestamp": now_iso}
        })

        from app.scoring.threat_engine import get_threat_engine
        engine = get_threat_engine()
        scoring_stats = await engine.run_scoring_cycle(since_minutes=5)

        # Update in-memory state
        scheduler_state["last_run"] = datetime.utcnow().isoformat() + "Z"
        scheduler_state["docs_last_cycle"] = index_result["indexed"]

        # Broadcast ingestion and scoring completions
        from app.api.routes.websocket import manager
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
            "data": {"docs_fetched": total_fetched, "docs_indexed": index_result["indexed"], "timestamp": now_iso}
        })

        # e. Log results
        logger.info("ingestion_cycle_completed",
                    docs_fetched=total_fetched,
                    docs_normalized=total_normalized,
                    docs_indexed=index_result['indexed'],
                    error_count=len(index_result['errors']))
        if index_result['errors']:
            logger.warning("indexing_errors_sample", errors=index_result['errors'][:3])

    except Exception as e:
        logger.error("ingestion_cycle_failed", error=str(e))

async def broadcast_stats(es: AsyncElasticsearch):
    try:
        from app.api.routes.websocket import manager
        from app.ingestion.es_client import INDEX_NAMES

        query = {
            "size": 0,
            "aggs": {
                "critical": {"filter": {"term": {"threat_level": "critical"}}},
                "high": {"filter": {"term": {"threat_level": "high"}}},
                "medium": {"filter": {"term": {"threat_level": "medium"}}},
                "low": {"filter": {"term": {"threat_level": "low"}}}
            }
        }
        res = await es.search(index=INDEX_NAMES["alerts_processed"], body=query, ignore_unavailable=True)
        aggs = res.get("aggregations", {})

        stats = {
            "critical": aggs.get("critical", {}).get("doc_count", 0),
            "high": aggs.get("high", {}).get("doc_count", 0),
            "medium": aggs.get("medium", {}).get("doc_count", 0),
            "low": aggs.get("low", {}).get("doc_count", 0),
            "total": res.get("hits", {}).get("total", {}).get("value", 0)
        }
        await manager.broadcast({
            "type": "stats_update",
            "data": stats
        })
    except Exception as e:
        logger.error("broadcast_stats_failed", error=str(e))

async def start_scheduler(es: AsyncElasticsearch):
    """Starts the APScheduler background ingestion job."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        run_ingestion_cycle,
        trigger=IntervalTrigger(minutes=5),
        args=[es],
        id="ingestion_pipeline",
        replace_existing=True
    )

    _scheduler.add_job(
        broadcast_stats,
        trigger=IntervalTrigger(seconds=60),
        args=[es],
        id="stats_broadcast",
        replace_existing=True
    )

    from app.models.model_manager import get_model_manager
    from app.models.trainer import run_incremental_retraining

    async def retrain_job():
        mm = get_model_manager()
        await run_incremental_retraining(es, mm)

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
        await drift_detector.run_drift_check(es)

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
        bm = BackupManager(es)
        await bm.create_snapshot()
        await bm.delete_old_snapshots(keep_last_n=7)

    _scheduler.add_job(
        daily_backup_job,
        trigger=CronTrigger(hour=21, minute=0), # 02:30 IST is UTC 21:00
        id="daily_backup",
        replace_existing=True
    )

    async def weekly_full_backup_job():
        bm = BackupManager(es)
        from datetime import datetime
        name = f"soc_full_backup_{datetime.now():%Y%m%d_%H%M%S}"
        await bm.create_snapshot(snapshot_name=name)
        await bm.delete_old_snapshots(keep_last_n=14)

    _scheduler.add_job(
        weekly_full_backup_job,
        trigger=CronTrigger(day_of_week='sun', hour=21, minute=30), # 03:00 IST is UTC 21:30
        id="weekly_full_backup",
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
