import logging
import asyncio
from typing import Any
from datetime import datetime, timezone

from elasticsearch import AsyncElasticsearch
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

import hashlib
import time

# Constants mapping log types to index patterns
SOURCE_PATTERNS = {
    "network": "logs-system.syslog-*",
    "process": "logs-endpoint.events.process-*",
    "security_alert": "logs-windows.powershell_operational-*"
}

# Simple in-memory cache for empty results (TTL 5 minutes)
_empty_query_cache = {}

def get_query_hash(index_pattern: str, since_minutes: int, additional_filters: list) -> str:
    key = f"{index_pattern}_{since_minutes}_{str(additional_filters)}"
    return hashlib.md5(key.encode()).hexdigest()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def fetch_logs(
    es: AsyncElasticsearch, 
    index_pattern: str, 
    since_minutes: int = 5, 
    size: int = 1000, 
    additional_filters: list[dict[str, Any]] | None = None
) -> list[dict]:
    """
    Query using range filter on @timestamp for last since_minutes minutes.
    Uses the scroll API if size > 1000.
    Returns list of _source dicts with _id and _index added.
    """
    if additional_filters is None:
        additional_filters = []
        
    query_hash = get_query_hash(index_pattern, since_minutes, additional_filters)
    
    # Check empty query cache
    now = time.time()
    if query_hash in _empty_query_cache:
        cache_time, count = _empty_query_cache[query_hash]
        # If we previously fetched 0 docs and it was within the last (since_minutes) window
        if count == 0 and now - cache_time < (since_minutes * 60) * 0.8:
            logger.debug(f"Skipping empty query fetch for {index_pattern}")
            return []

    query = {
        "bool": {
            "filter": [
                {
                    "range": {
                        "@timestamp": {
                            "gte": f"now-{since_minutes}m",
                            "lte": "now"
                        }
                    }
                }
            ] + additional_filters
        }
    }

    results = []
    
    if size <= 1000:
        # Standard search is sufficient
        resp = await es.search(
            index=index_pattern,
            query=query,
            size=size,
            ignore_unavailable=True
        )
        for hit in resp.get("hits", {}).get("hits", []):
            doc = hit["_source"]
            doc["_id"] = hit["_id"]
            doc["_index"] = hit["_index"]
            results.append(doc)
    else:
        # Use scroll API for larger sizes
        scroll_time = "2m"
        scroll_size = 1000
        
        resp = await es.search(
            index=index_pattern,
            query=query,
            scroll=scroll_time,
            size=scroll_size,
            ignore_unavailable=True
        )
        
        scroll_id = resp.get("_scroll_id")
        hits = resp.get("hits", {}).get("hits", [])
        
        while hits and len(results) < size:
            for hit in hits:
                if len(results) >= size:
                    break
                doc = hit["_source"]
                doc["_id"] = hit["_id"]
                doc["_index"] = hit["_index"]
                results.append(doc)
                
            if len(results) >= size:
                break
                
            resp = await es.scroll(scroll_id=scroll_id, scroll=scroll_time)
            scroll_id = resp.get("_scroll_id")
            hits = resp.get("hits", {}).get("hits", [])
            
        # Clean up the scroll context
        if scroll_id:
            try:
                await es.clear_scroll(scroll_id=scroll_id)
            except Exception as e:
                logger.warning(f"Failed to clear scroll context: {e}")
                
    # Update cache
    _empty_query_cache[query_hash] = (time.time(), len(results))
    
    # Cleanup old cache entries (older than 1 hour) to prevent memory leaks
    if len(_empty_query_cache) > 1000:
        cutoff = time.time() - 3600
        for k in list(_empty_query_cache.keys()):
            if _empty_query_cache[k][0] < cutoff:
                del _empty_query_cache[k]
                
    return results

async def fetch_all_sources(es: AsyncElasticsearch, since_minutes: int = 5) -> dict[str, list[dict]]:
    """
    Calls fetch_logs for all three patterns concurrently using asyncio.gather.
    Adds log_type field to each doc based on index pattern.
    Returns dict mapping log_type to list of records.
    """
    tasks = []
    log_types = list(SOURCE_PATTERNS.keys())
    
    for log_type in log_types:
        pattern = SOURCE_PATTERNS[log_type]
        tasks.append(fetch_logs(es, pattern, since_minutes=since_minutes, size=1000))
        
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_results = {log_type: [] for log_type in log_types}
    
    for log_type, result in zip(log_types, results_list):
        if isinstance(result, Exception):
            logger.error(f"Failed to fetch logs for {log_type}: {result}")
            continue
            
        for doc in result:
            # Tag each document with its logical source type
            doc["log_type"] = log_type
            final_results[log_type].append(doc)
            
    return final_results

async def fetch_by_entity(es: AsyncElasticsearch, host_id: str, user_name: str, since_minutes: int = 30) -> dict[str, list[dict]]:
    """
    Fetch logs filtered by host.id == host_id AND user.name == user_name.
    Used by the SLM investigation flow.
    Returns same structure as fetch_all_sources.
    """
    additional_filters = [
        {"term": {"host.id": host_id}},
        {"term": {"user.name": user_name}}
    ]
    
    tasks = []
    log_types = list(SOURCE_PATTERNS.keys())
    
    for log_type in log_types:
        pattern = SOURCE_PATTERNS[log_type]
        tasks.append(
            fetch_logs(
                es, 
                pattern, 
                since_minutes=since_minutes, 
                size=1000, 
                additional_filters=additional_filters
            )
        )
        
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_results = {log_type: [] for log_type in log_types}
    
    for log_type, result in zip(log_types, results_list):
        if isinstance(result, Exception):
            logger.error(f"Failed to fetch entity logs for {log_type}: {result}")
            continue
            
        for doc in result:
            doc["log_type"] = log_type
            final_results[log_type].append(doc)
            
    return final_results
