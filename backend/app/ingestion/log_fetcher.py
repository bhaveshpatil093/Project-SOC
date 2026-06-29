import asyncio
import hashlib
import time
from typing import Any

from app.ingestion.kibana_client import KibanaProxyClient

from app.logging_config import get_logger
logger = get_logger(__name__)

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

async def fetch_logs(
    client: KibanaProxyClient,
    index_pattern: str,
    since_minutes: int = 5,
    size: int = 1000,
    additional_filters: list[dict[str, Any]] | None = None
) -> list[dict]:
    """
    Query using range filter on @timestamp for last since_minutes minutes.
    Uses search_after for pagination if size > 1000 since Kibana Proxy does not support scroll.
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

    filters = [
        {
            "range": {
                "@timestamp": {
                    "gte": f"now-{since_minutes}m",
                    "lte": "now"
                }
            }
        }
    ] + additional_filters

    query = {
        "query": {
            "bool": {
                "filter": filters
            }
        },
        "sort": [{"@timestamp": {"order": "desc"}}],
        "_source": ["host", "user", "@timestamp", "message", "process", "event", "winlog", "kibana"]
    }

    results = []
    page_size = 1000 if size > 1000 else size
    search_after = None

    while len(results) < size:
        current_query = dict(query)
        if search_after:
            current_query["search_after"] = search_after
            
        try:
            resp = await client.search(index=index_pattern, body=current_query, size=page_size)
        except Exception as e:
            logger.error(f"Search failed for pattern {index_pattern}: {e}")
            break
            
        hits = resp.get("hits", {}).get("hits", [])
        
        if not hits:
            break
            
        for hit in hits:
            if len(results) >= size:
                break
            doc = hit.get("_source", {})
            doc["_id"] = hit.get("_id")
            doc["_index"] = hit.get("_index")
            results.append(doc)
            
        if len(results) >= size or len(hits) < page_size:
            break
            
        search_after = hits[-1].get("sort")
        if not search_after:
            break

    # Update cache
    _empty_query_cache[query_hash] = (time.time(), len(results))

    # Cleanup old cache entries (older than 1 hour)
    if len(_empty_query_cache) > 1000:
        cutoff = time.time() - 3600
        for k in list(_empty_query_cache.keys()):
            if _empty_query_cache[k][0] < cutoff:
                del _empty_query_cache[k]

    return results

async def fetch_all_sources(client: KibanaProxyClient, since_minutes: int = 5) -> dict[str, list[dict]]:
    """
    Calls fetch_logs for all three patterns concurrently.
    Tags each doc with its log_type before returning.
    """
    tasks = []
    log_types = list(SOURCE_PATTERNS.keys())

    for log_type in log_types:
        pattern = SOURCE_PATTERNS[log_type]
        tasks.append(fetch_logs(client, pattern, since_minutes=since_minutes, size=1000))

    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    final_results = {log_type: [] for log_type in log_types}

    for log_type, result in zip(log_types, results_list):
        if isinstance(result, Exception):
            logger.error(f"Failed to fetch logs for {log_type}: {result}")
            continue

        for doc in result:
            doc["log_type"] = log_type
            final_results[log_type].append(doc)

    return final_results

async def fetch_by_entity(client: KibanaProxyClient, host_id: str, user_name: str, since_minutes: int = 30) -> dict[str, list[dict]]:
    """
    Fetch logs filtered by host.id and user.name.
    Same return structure as fetch_all_sources.
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
                client,
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

async def fetch_raw_query(client: KibanaProxyClient, index: str, dsl_body: dict) -> dict:
    """
    Generic passthrough for ad-hoc queries (used by SLM RAG).
    Returns full raw response dict (not just hits).
    """
    try:
        return await client.search(index=index, body=dsl_body)
    except Exception as e:
        logger.error(f"Failed raw query on {index}: {e}")
        raise
