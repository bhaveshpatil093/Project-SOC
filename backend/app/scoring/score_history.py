from datetime import datetime, timedelta

import numpy as np

from app.models.model_manager import ScoringResult

from app.logging_config import get_logger
logger = get_logger(__name__)

INDEX_NAME = "soc-score-history"

async def record_score_history(es, entity_key: str, window_bucket: str, scoring_result: ScoringResult):
    try:
        doc = {
            "entity_key": entity_key,
            "window_bucket": window_bucket,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "threat_score": scoring_result.threat_score,
            "network_score": scoring_result.network_anomaly_score,
            "process_score": scoring_result.process_anomaly_score,
            "sequence_score": scoring_result.sequence_anomaly_score,
            "rule_score": scoring_result.rule_score,
            "threat_level": scoring_result.threat_level
        }
        # Index into score history
        await es.index(index=INDEX_NAME, document=doc)
    except Exception as e:
        logger.error(f"Failed to record score history for {entity_key}: {e}")

async def get_score_history(es, entity_key: str, since_hours: int = 168) -> list[dict]:
    cutoff = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat() + "Z"
    try:
        query = {
            "size": 1000,
            "sort": [{"timestamp": {"order": "asc"}}],
            "query": {
                "bool": {
                    "must": [
                        {"term": {"entity_key.keyword": entity_key}},
                        {"range": {"timestamp": {"gte": cutoff}}}
                    ]
                }
            }
        }
        res = await es.search(index=INDEX_NAME, body=query, ignore_unavailable=True)
        return [hit["_source"] for hit in res.get("hits", {}).get("hits", [])]
    except Exception as e:
        logger.error(f"Failed to get score history for {entity_key}: {e}")
        return []

async def get_score_trends(es, entity_key: str) -> dict:
    history = await get_score_history(es, entity_key, since_hours=168)
    if not history:
        return {
            "trend_7d": "stable",
            "peak_score": 0.0,
            "peak_at": None,
            "current_score": 0.0,
            "avg_score_last_24h": 0.0,
            "avg_score_last_7d": 0.0,
            "score_volatility": 0.0,
            "recent_scores": []
        }

    now = datetime.utcnow()
    last_24h = [h for h in history if (now - datetime.fromisoformat(h["timestamp"].replace("Z", ""))).total_seconds() < 86400]

    scores_7d = [h["threat_score"] for h in history]
    scores_24h = [h["threat_score"] for h in last_24h]

    peak_record = max(history, key=lambda x: x["threat_score"])

    avg_7d = sum(scores_7d) / len(scores_7d) if scores_7d else 0.0
    avg_24h = sum(scores_24h) / len(scores_24h) if scores_24h else 0.0

    volatility = float(np.std(scores_24h)) if len(scores_24h) > 1 else 0.0

    # Calculate trend_7d
    older_avg = sum(scores_7d[:-len(scores_24h)]) / len(scores_7d[:-len(scores_24h)]) if len(scores_7d) > len(scores_24h) else 0.0
    if avg_24h > older_avg + 0.1:
        trend = "increasing"
    elif avg_24h < older_avg - 0.1:
        trend = "decreasing"
    else:
        trend = "stable"

    return {
        "trend_7d": trend,
        "peak_score": peak_record["threat_score"],
        "peak_at": peak_record["timestamp"],
        "current_score": history[-1]["threat_score"],
        "avg_score_last_24h": avg_24h,
        "avg_score_last_7d": avg_7d,
        "score_volatility": volatility,
        "recent_scores": scores_24h[-10:] if scores_24h else []
    }

async def get_system_score_trends(es) -> dict:
    # Get macro system trends using Date Histogram aggregation on threat_score
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
    try:
        query = {
            "size": 0,
            "query": {
                "range": {"timestamp": {"gte": cutoff}}
            },
            "aggs": {
                "hourly_trends": {
                    "date_histogram": {
                        "field": "timestamp",
                        "calendar_interval": "1h"
                    },
                    "aggs": {
                        "avg_threat": {
                            "avg": {"field": "threat_score"}
                        }
                    }
                }
            }
        }
        res = await es.search(index=INDEX_NAME, body=query, ignore_unavailable=True)
        buckets = res.get("aggregations", {}).get("hourly_trends", {}).get("buckets", [])

        hourly_data = []
        for b in buckets:
            hourly_data.append({
                "timestamp": b["key_as_string"],
                "avg_score": b["avg_threat"]["value"] if b["avg_threat"]["value"] is not None else 0.0
            })

        return {"hourly_avg_threat_score": hourly_data}
    except Exception as e:
        logger.error(f"Failed to get system score trends: {e}")
        return {"hourly_avg_threat_score": []}
