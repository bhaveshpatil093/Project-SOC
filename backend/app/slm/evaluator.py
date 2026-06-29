from dataclasses import asdict, dataclass
from datetime import datetime

from app.logging_config import get_logger
logger = get_logger(__name__)

@dataclass
class ResponseMetrics:
    conversation_id: str
    turn_id: str
    question_type: str
    response_time_ms: float
    input_tokens: int
    output_tokens: int
    tokens_per_second: float

    has_summary: bool
    has_evidence: bool
    has_action_items: bool
    action_item_count: int
    has_mitre_reference: bool
    response_length_words: int
    verdict_confidence: str | None

    mentions_host: bool
    mentions_technique: bool
    is_too_short: bool
    is_too_long: bool

class SLMEvaluator:
    def __init__(self):
        pass

    def evaluate_response(self,
                          question: str,
                          response: str,
                          alert: dict,
                          parsed: dict,
                          response_time_ms: float,
                          input_tokens: int,
                          output_tokens: int,
                          conversation_id: str = "N/A",
                          turn_id: str = "N/A",
                          question_type: str = "general") -> ResponseMetrics:

        words = response.split()
        length_words = len(words)

        has_summary = bool(parsed.get("summary"))
        has_evidence = bool(parsed.get("evidence_points"))
        action_items = parsed.get("action_items") or []
        has_action_items = len(action_items) > 0
        has_mitre = bool(parsed.get("mitre_techniques"))
        verdict_conf = parsed.get("confidence")

        host_mentioned = False
        if alert and alert.get("entity_key"):
            host = alert["entity_key"].split("|")[0].lower()
            if host in response.lower():
                host_mentioned = True

        technique_mentioned = False
        if alert and alert.get("mitre_tactics"):
            tactics = " ".join(alert["mitre_tactics"]).lower()
            if any(t in response.lower() for t in tactics.split()):
                technique_mentioned = True

        tps = output_tokens / (response_time_ms / 1000.0) if response_time_ms > 0 else 0.0

        return ResponseMetrics(
            conversation_id=conversation_id,
            turn_id=turn_id,
            question_type=question_type,
            response_time_ms=response_time_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tokens_per_second=tps,
            has_summary=has_summary,
            has_evidence=has_evidence,
            has_action_items=has_action_items,
            action_item_count=len(action_items),
            has_mitre_reference=has_mitre,
            response_length_words=length_words,
            verdict_confidence=verdict_conf,
            mentions_host=host_mentioned,
            mentions_technique=technique_mentioned,
            is_too_short=length_words < 30,
            is_too_long=length_words > 500
        )

    def compute_quality_score(self, metrics: ResponseMetrics) -> float:
        score = 0.0
        if metrics.has_summary: score += 0.2
        if metrics.has_evidence: score += 0.2
        if metrics.has_action_items: score += 0.2
        if metrics.has_mitre_reference: score += 0.1
        if metrics.mentions_host: score += 0.1
        if metrics.mentions_technique: score += 0.1

        if metrics.is_too_short: score -= 0.3
        if metrics.is_too_long: score -= 0.1

        return max(0.0, min(1.0, score))

    async def store_metrics(self, es, metrics: ResponseMetrics, quality_score: float):
        if not es:
            return

        doc = asdict(metrics)
        doc["quality_score"] = quality_score
        doc["timestamp"] = datetime.utcnow().isoformat() + "Z"

        try:
            await es.index(index="soc-slm-metrics", document=doc)
        except Exception as e:
            logger.error(f"Failed to index SLM metrics: {e}")

    async def get_aggregate_stats(self, es, since_hours: int = 24) -> dict:
        if not es:
            return {"error": "ES not connected"}

        query = {
            "query": {
                "range": {
                    "timestamp": {"gte": f"now-{since_hours}h"}
                }
            },
            "aggs": {
                "avg_response_time": {"avg": {"field": "response_time_ms"}},
                "avg_quality_score": {"avg": {"field": "quality_score"}},
                "avg_tokens_per_sec": {"avg": {"field": "tokens_per_second"}},
                "quality_distribution": {
                    "histogram": {"field": "quality_score", "interval": 0.2}
                },
                "slowest_queries": {
                    "top_hits": {
                        "sort": [{"response_time_ms": {"order": "desc"}}],
                        "size": 5,
                        "_source": ["question_type", "response_time_ms", "quality_score"]
                    }
                }
            },
            "size": 0
        }

        try:
            res = await es.search(index="soc-slm-metrics", body=query, ignore_unavailable=True)
            total = res.get("hits", {}).get("total", {}).get("value", 0)
            aggs = res.get("aggregations", {})

            dist = []
            if "quality_distribution" in aggs:
                for b in aggs["quality_distribution"]["buckets"]:
                    dist.append({"bucket": b["key"], "count": b["doc_count"]})

            slowest = []
            if "slowest_queries" in aggs:
                for h in aggs["slowest_queries"]["hits"]["hits"]:
                    slowest.append(h["_source"])

            return {
                "total_queries": total,
                "avg_response_time": round(aggs.get("avg_response_time", {}).get("value") or 0.0, 2),
                "avg_quality_score": round(aggs.get("avg_quality_score", {}).get("value") or 0.0, 2),
                "avg_tokens_per_sec": round(aggs.get("avg_tokens_per_sec", {}).get("value") or 0.0, 2),
                "quality_distribution": dist,
                "slowest_queries": slowest
            }
        except Exception as e:
            logger.error(f"Error fetching aggregate SLM stats: {e}")
            return {"error": str(e)}

_evaluator = SLMEvaluator()

def get_slm_evaluator() -> SLMEvaluator:
    return _evaluator
