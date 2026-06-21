import datetime
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class LogViewer:
    INDEX_NAME = "soc-application-logs"

    async def initialize(self, es):
        # Ensure the index exists with proper mapping
        exists = await es.indices.exists(index=self.INDEX_NAME)
        if not exists:
            mapping = {
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "level": {"type": "keyword"},
                        "logger_name": {"type": "keyword"},
                        "message": {"type": "text"},
                        "correlation_id": {"type": "keyword"},
                        "module": {"type": "keyword"},
                        "funcName": {"type": "keyword"},
                        "lineno": {"type": "integer"}
                    }
                }
            }
            await es.indices.create(index=self.INDEX_NAME, body=mapping)
            logger.info(f"Created index {self.INDEX_NAME}")

    async def get_recent_logs(self, es, level: str = None, component: str = None,
                              since_minutes: int = 60, limit: int = 100) -> list[dict]:
        since_time = (datetime.datetime.utcnow() - datetime.timedelta(minutes=since_minutes)).isoformat() + "Z"
        
        must_queries = [{"range": {"timestamp": {"gte": since_time}}}]
        if level:
            must_queries.append({"match": {"level": level.upper()}})
        if component:
            must_queries.append({"match": {"logger_name": component}})
            
        try:
            resp = await es.search(index=self.INDEX_NAME, body={
                "query": {"bool": {"must": must_queries}},
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": limit
            }, ignore_unavailable=True)
            return [hit["_source"] for hit in resp.get("hits", {}).get("hits", [])]
        except Exception as e:
            logger.error(f"Error fetching recent logs: {e}")
            return []

    async def get_error_summary(self, es, since_hours: int = 24) -> dict:
        since_time = (datetime.datetime.utcnow() - datetime.timedelta(hours=since_hours)).isoformat() + "Z"
        try:
            resp = await es.search(index=self.INDEX_NAME, body={
                "query": {
                    "bool": {
                        "must": [
                            {"range": {"timestamp": {"gte": since_time}}},
                            {"terms": {"level": ["ERROR", "CRITICAL"]}}
                        ]
                    }
                },
                "size": 0,
                "aggs": {
                    "by_component": {
                        "terms": {"field": "logger_name", "size": 20},
                        "aggs": {
                            "by_message": {
                                "terms": {"field": "message.keyword", "size": 10},
                                "aggs": {
                                    "last_seen": {"max": {"field": "timestamp"}},
                                    "sample": {"top_hits": {"size": 1}}
                                }
                            }
                        }
                    }
                }
            }, ignore_unavailable=True)
            
            summary = {}
            aggs = resp.get("aggregations", {}).get("by_component", {}).get("buckets", [])
            for comp_bucket in aggs:
                component = comp_bucket["key"]
                summary[component] = []
                for msg_bucket in comp_bucket.get("by_message", {}).get("buckets", []):
                    sample_hit = msg_bucket.get("sample", {}).get("hits", {}).get("hits", [])
                    correlation_id = sample_hit[0]["_source"].get("correlation_id") if sample_hit else None
                    
                    last_seen_ts = msg_bucket.get("last_seen", {}).get("value_as_string")
                    
                    summary[component].append({
                        "message_pattern": msg_bucket["key"],
                        "count": msg_bucket["doc_count"],
                        "last_seen": last_seen_ts,
                        "sample_correlation_id": correlation_id
                    })
            return summary
        except Exception as e:
            logger.error(f"Error fetching error summary: {e}")
            return {}

    async def search_logs(self, es, query: str, since_hours: int = 24, limit: int = 100) -> list[dict]:
        since_time = (datetime.datetime.utcnow() - datetime.timedelta(hours=since_hours)).isoformat() + "Z"
        try:
            resp = await es.search(index=self.INDEX_NAME, body={
                "query": {
                    "bool": {
                        "must": [
                            {"range": {"timestamp": {"gte": since_time}}},
                            {"multi_match": {"query": query, "fields": ["message", "logger_name", "correlation_id"]}}
                        ]
                    }
                },
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": limit
            }, ignore_unavailable=True)
            return [hit["_source"] for hit in resp.get("hits", {}).get("hits", [])]
        except Exception as e:
            logger.error(f"Error searching logs: {e}")
            return []

    async def get_correlation_trace(self, es, correlation_id: str) -> list[dict]:
        try:
            resp = await es.search(index=self.INDEX_NAME, body={
                "query": {"match": {"correlation_id": correlation_id}},
                "sort": [{"timestamp": {"order": "asc"}}],
                "size": 500
            }, ignore_unavailable=True)
            return [hit["_source"] for hit in resp.get("hits", {}).get("hits", [])]
        except Exception as e:
            logger.error(f"Error fetching correlation trace: {e}")
            return []

log_viewer_instance = LogViewer()
