import datetime
import uuid
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

from app.logging_config import get_logger
logger = get_logger(__name__)

@dataclass
class ResponseMetrics:
    generation_time_ms: int
    prompt_tokens: int
    completion_tokens: int
    quality_score: float

@dataclass
class SLMQueryEvent:
    event_id: str
    timestamp: str
    conversation_id: str
    question: str
    question_type: str
    alert_id: Optional[str]
    response_metrics: dict

class SLMAnalytics:
    INDEX_NAME = "soc-slm-analytics"

    async def _ensure_index(self, es):
        try:
            if not await es.indices.exists(index=self.INDEX_NAME):
                await es.indices.create(index=self.INDEX_NAME, body={
                    "mappings": {
                        "properties": {
                            "event_id": {"type": "keyword"},
                            "timestamp": {"type": "date"},
                            "conversation_id": {"type": "keyword"},
                            "question": {"type": "text", "analyzer": "standard"},
                            "question_type": {"type": "keyword"},
                            "alert_id": {"type": "keyword"},
                            "response_metrics": {
                                "properties": {
                                    "generation_time_ms": {"type": "long"},
                                    "prompt_tokens": {"type": "long"},
                                    "completion_tokens": {"type": "long"},
                                    "quality_score": {"type": "float"}
                                }
                            }
                        }
                    }
                })
        except Exception as e:
            logger.error("failed_to_ensure_slm_analytics_index", error=str(e))

    async def track_query(self, es, conversation_id: str, question: str, question_type: str, alert_id: Optional[str], response_metrics: ResponseMetrics):
        try:
            await self._ensure_index(es)
            event = SLMQueryEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                conversation_id=conversation_id,
                question=question,
                question_type=question_type,
                alert_id=alert_id,
                response_metrics=asdict(response_metrics)
            )
            await es.index(index=self.INDEX_NAME, body=asdict(event))
        except Exception as e:
            logger.error("failed_to_track_slm_query", error=str(e))

    async def get_top_questions(self, es, since_days: int = 7, n: int = 20) -> List[Dict]:
        try:
            await self._ensure_index(es)
            since_time = (datetime.datetime.utcnow() - datetime.timedelta(days=since_days)).isoformat() + "Z"
            # In a real system, we might use KNN clustering on embeddings here.
            # For simplicity, we use term aggregation on significant text or exact phrases.
            resp = await es.search(index=self.INDEX_NAME, body={
                "query": {"range": {"timestamp": {"gte": since_time}}},
                "size": 0,
                "aggs": {
                    "common_phrases": {
                        "significant_text": {
                            "field": "question",
                            "size": n
                        }
                    }
                }
            }, ignore_unavailable=True)
            
            buckets = resp.get("aggregations", {}).get("common_phrases", {}).get("buckets", [])
            results = []
            for b in buckets:
                results.append({"cluster": b["key"], "count": b["doc_count"], "examples": [b["key"]]})
            
            # Fallback if significant text doesn't work well (needs enough documents)
            if not results:
                resp = await es.search(index=self.INDEX_NAME, body={
                    "query": {"range": {"timestamp": {"gte": since_time}}},
                    "size": 100
                }, ignore_unavailable=True)
                # simple word count
                words = {}
                for hit in resp.get("hits", {}).get("hits", []):
                    q = hit["_source"].get("question", "")
                    for w in q.split():
                        if len(w) > 4:
                            words[w.lower()] = words.get(w.lower(), 0) + 1
                top_words = sorted(words.items(), key=lambda x: x[1], reverse=True)[:n]
                results = [{"cluster": w[0], "count": w[1], "examples": [w[0]]} for w in top_words]

            return results
        except Exception as e:
            logger.error("failed_to_get_top_questions", error=str(e))
            return []

    async def get_usage_trends(self, es, since_days: int = 30) -> Dict:
        try:
            await self._ensure_index(es)
            since_time = (datetime.datetime.utcnow() - datetime.timedelta(days=since_days)).isoformat() + "Z"
            
            resp = await es.search(index=self.INDEX_NAME, body={
                "query": {"range": {"timestamp": {"gte": since_time}}},
                "size": 0,
                "aggs": {
                    "daily_queries": {
                        "date_histogram": {"field": "timestamp", "calendar_interval": "day"}
                    },
                    "query_type_distribution": {
                        "terms": {"field": "question_type"}
                    },
                    "peak_hour": {
                        "terms": {"field": "timestamp", "script": "doc['timestamp'].value.getHour()", "size": 1}
                    },
                    "avg_response_time": {
                        "date_histogram": {"field": "timestamp", "calendar_interval": "day"},
                        "aggs": {"avg_ms": {"avg": {"field": "response_metrics.generation_time_ms"}}}
                    },
                    "quality_score_trend": {
                        "date_histogram": {"field": "timestamp", "calendar_interval": "day"},
                        "aggs": {"avg_quality": {"avg": {"field": "response_metrics.quality_score"}}}
                    }
                }
            }, ignore_unavailable=True)

            aggs = resp.get("aggregations", {})
            
            daily_queries = [{"date": b["key_as_string"], "count": b["doc_count"]} for b in aggs.get("daily_queries", {}).get("buckets", [])]
            
            type_dist = {b["key"]: b["doc_count"] for b in aggs.get("query_type_distribution", {}).get("buckets", [])}
            
            peak_hour_buckets = aggs.get("peak_hour", {}).get("buckets", [])
            peak_hour = int(peak_hour_buckets[0]["key"]) if peak_hour_buckets else 0

            avg_response = [{"date": b["key_as_string"], "avg_ms": b.get("avg_ms", {}).get("value") or 0} for b in aggs.get("avg_response_time", {}).get("buckets", [])]
            
            quality_trend = [{"date": b["key_as_string"], "avg_quality": b.get("avg_quality", {}).get("value") or 0} for b in aggs.get("quality_score_trend", {}).get("buckets", [])]

            return {
                "daily_queries": daily_queries,
                "query_type_distribution": type_dist,
                "peak_hour": peak_hour,
                "avg_response_time_trend": avg_response,
                "quality_score_trend": quality_trend
            }
        except Exception as e:
            logger.error("failed_to_get_usage_trends", error=str(e))
            return {}

    async def get_knowledge_gaps(self, es) -> List[str]:
        try:
            await self._ensure_index(es)
            # Find questions where quality score < 0.5
            resp = await es.search(index=self.INDEX_NAME, body={
                "query": {"range": {"response_metrics.quality_score": {"lt": 0.5}}},
                "size": 50,
                "sort": [{"timestamp": "desc"}]
            }, ignore_unavailable=True)
            
            gaps = []
            for hit in resp.get("hits", {}).get("hits", []):
                gaps.append(hit["_source"].get("question", "Unknown topic"))
            
            # Simple deduplication
            return list(set(gaps))[:10]
        except Exception as e:
            logger.error("failed_to_get_knowledge_gaps", error=str(e))
            return []

    async def get_most_investigated_entities(self, es, since_days: int = 7) -> List[Dict]:
        try:
            await self._ensure_index(es)
            since_time = (datetime.datetime.utcnow() - datetime.timedelta(days=since_days)).isoformat() + "Z"
            resp = await es.search(index=self.INDEX_NAME, body={
                "query": {
                    "bool": {
                        "must": [{"range": {"timestamp": {"gte": since_time}}}],
                        "must_not": [{"term": {"alert_id": ""}}]
                    }
                },
                "size": 0,
                "aggs": {
                    "top_alerts": {
                        "terms": {"field": "alert_id", "size": 10}
                    }
                }
            }, ignore_unavailable=True)
            
            buckets = resp.get("aggregations", {}).get("top_alerts", {}).get("buckets", [])
            return [{"alert_id": b["key"], "queries": b["doc_count"]} for b in buckets]
        except Exception as e:
            logger.error("failed_to_get_most_investigated_entities", error=str(e))
            return []

slm_analytics_instance = SLMAnalytics()
