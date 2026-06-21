import hashlib
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AlertDeduplicator:
    def __init__(self, dedup_window_minutes: int = 30, similarity_threshold: float = 0.85):
        self.dedup_window_minutes = dedup_window_minutes
        self.similarity_threshold = similarity_threshold

    def compute_alert_fingerprint(self, scoring_result) -> str:
        # We assume scoring_result has an entity_key, mitre_tactics list, and triggered_rules list
        entity_key = getattr(scoring_result, "entity_key", "unknown")

        # Sort to ensure order invariance
        tactics = sorted(getattr(scoring_result, "mitre_tactics", []))
        rules = sorted(getattr(scoring_result, "triggered_rules", []))

        fingerprint_data = {
            "entity_key": entity_key,
            "mitre_tactics": tactics,
            "triggered_rules": rules
        }

        # Serialize and hash
        serialized = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.md5(serialized.encode("utf-8")).hexdigest()[:8]

    async def is_duplicate(self, es, scoring_result) -> tuple[bool, str | None]:
        fingerprint = self.compute_alert_fingerprint(scoring_result)
        cutoff_time = (datetime.utcnow() - timedelta(minutes=self.dedup_window_minutes)).isoformat() + "Z"

        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"dedup_fingerprint.keyword": fingerprint}},
                        {"range": {"created_at": {"gte": cutoff_time}}}
                    ],
                    "must_not": [
                        {"term": {"status.keyword": "closed"}}
                    ]
                }
            },
            "size": 1,
            "sort": [{"created_at": {"order": "desc"}}]
        }

        try:
            res = await es.search(index="soc-processed-alerts", body=query)
            hits = res["hits"]["hits"]
            if hits:
                return True, hits[0]["_id"]
        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")

        return False, None

    async def update_existing_alert(self, es, alert_id: str, new_result):
        # We need to fetch the existing alert to merge occurrences properly
        # Or we can do a scripted update. For safety, let's do a scripted update if possible,
        # or just fetch, merge, and index. Fetch-merge-index is cleaner for tracking.
        try:
            res = await es.get(index="soc-processed-alerts", id=alert_id)
            existing = res["_source"]

            # 1. Update timestamp
            existing["last_seen"] = datetime.utcnow().isoformat() + "Z"

            # 2. Update threat score if higher
            new_score = getattr(new_result, "threat_score", 0.0)
            if new_score > existing.get("threat_score", 0.0):
                existing["threat_score"] = new_score
                existing["network_score"] = getattr(new_result, "network_score", existing.get("network_score", 0.0))
                existing["process_score"] = getattr(new_result, "process_score", existing.get("process_score", 0.0))

            # 3. Increment occurrence count
            existing["occurrence_count"] = existing.get("occurrence_count", 1) + 1

            # 4. Append occurrences
            occurrences = existing.get("occurrences", [])
            occurrences.append({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "score": new_score
            })
            # keep max 20
            existing["occurrences"] = occurrences[-20:]

            # 5. Merge rules
            new_rules = getattr(new_result, "triggered_rules", [])
            existing["triggered_rules"] = list(set(existing.get("triggered_rules", []) + new_rules))

            await es.index(index="soc-processed-alerts", id=alert_id, body=existing)
        except Exception as e:
            logger.error(f"Failed to update duplicate alert {alert_id}: {e}")

    async def deduplicate_batch(self, es, scoring_results: list) -> dict:
        new_alerts = []
        updated_alerts = []

        for result in scoring_results:
            is_dup, alert_id = await self.is_duplicate(es, result)
            if is_dup:
                updated_alerts.append((alert_id, result))
            else:
                # Add fingerprint data for indexing
                result.dedup_fingerprint = self.compute_alert_fingerprint(result)
                result.occurrence_count = 1
                result.occurrences = [{"timestamp": datetime.utcnow().isoformat() + "Z", "score": getattr(result, "threat_score", 0.0)}]
                new_alerts.append(result)

        total = len(scoring_results)
        num_new = len(new_alerts)
        num_dedup = len(updated_alerts)

        return {
            "new": new_alerts,
            "updated": updated_alerts,
            "dedup_stats": {
                "total": total,
                "new": num_new,
                "deduplicated": num_dedup,
                "dedup_rate": (num_dedup / total) if total > 0 else 0.0
            }
        }
