import logging
from datetime import datetime, timezone
from typing import Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from dataclasses import asdict

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

async def bulk_index(es: AsyncElasticsearch, docs: list[dict], index: str) -> dict[str, Any]:
    """Bulk index documents into Elasticsearch."""
    if not docs:
        return {"indexed": 0, "errors": []}
        
    actions = [
        {
            "_index": index,
            "_source": doc
        }
        for doc in docs
    ]
    
    try:
        success, failed = await async_bulk(
            es, actions, stats_only=False, raise_on_error=False, raise_on_exception=False
        )
        
        errors = []
        if failed:
            for item in failed:
                errors.append(item)
                
        return {"indexed": success, "errors": errors}
    except Exception as e:
        logger.error("bulk_indexing_exception", error=str(e))
        return {"indexed": 0, "errors": [str(e)]}

def get_window_bucket(ts: datetime, window_minutes: int = 5) -> datetime:
    """Floors a timestamp to the nearest window_minutes."""
    minute = (ts.minute // window_minutes) * window_minutes
    return ts.replace(minute=minute, second=0, microsecond=0)

async def run_ingestion_cycle(es: AsyncElasticsearch):
    """Core ingestion cycle: fetch -> normalize -> enrich -> index."""
    try:
        logger.info("ingestion_cycle_started")
        
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
        from app.scoring.threat_engine import get_threat_engine
        engine = get_threat_engine()
        scoring_stats = await engine.run_scoring_cycle(since_minutes=5)
        
        # Update in-memory state
        scheduler_state["last_run"] = datetime.utcnow().isoformat() + "Z"
        scheduler_state["docs_last_cycle"] = index_result["indexed"]
        
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
    
    from app.models.trainer import run_incremental_retraining
    from app.models.model_manager import get_model_manager
    
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

    _scheduler.start()
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
