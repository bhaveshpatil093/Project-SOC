import uuid
import json
from datetime import datetime

from pydantic import BaseModel

from app.storage import local_db
from app.config import settings

from app.logging_config import get_logger
logger = get_logger(__name__)


class AnalystFeedback(BaseModel):
    alert_id: str
    analyst_name: str
    label: str  # TP, FP, Benign
    notes: str | None = ""
    mitre_override: list[str] | None = []


async def submit_feedback(db_path: str, feedback: AnalystFeedback) -> dict:
    """Inserts a new feedback record mapping directly to SQLite."""
    doc = feedback.dict()
    doc["feedback_id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.utcnow().isoformat() + "Z"

    # SQLite needs strings for arrays
    doc["mitre_override"] = json.dumps(doc.get("mitre_override", []))

    try:
        feedback_id = await local_db.insert_feedback(db_path, doc)
        return {"status": "success", "id": feedback_id}
    except Exception as e:
        logger.error(f"Error submitting feedback mapping: {e}")
        return {"status": "error", "message": str(e)}


async def get_feedback_for_alert(db_path: str, alert_id: str) -> list[dict]:
    """Retrieves all feedback records tied to a specific alert."""
    try:
        # Fetch up to 10k feedback items and filter manually (since local_db.list_feedback only filters by label currently)
        all_feedback = await local_db.list_feedback(db_path, limit=10000)
        return [f for f in all_feedback if f.get("alert_id") == alert_id]
    except Exception:
        return []


async def get_all_feedback(db_path: str, label: str = None, limit: int = 500) -> list[dict]:
    """Retrieves a bulk list of feedback records from SQLite."""
    try:
        return await local_db.list_feedback(db_path, label=label, limit=limit)
    except Exception:
        return []


async def get_fp_suppression_patterns(db_path: str) -> list[dict]:
    """Isolates explicit False Positive bounds mapping historical intersections recursively matching entities + heuristics."""
    try:
        fp_feedback = await local_db.list_feedback(db_path, label="FP", limit=10000)

        # We need entity_key and triggered_rules. Feedback doesn't store these directly,
        # so we fetch the corresponding alerts.
        patterns_map = {}

        for fb in fp_feedback:
            alert = await local_db.get_alert(db_path, fb.get("alert_id"))
            if not alert:
                continue

            entity_key = alert.get("entity_key")
            rules = alert.get("triggered_rules", [])

            if not entity_key:
                continue

            # Map entity to each triggered rule
            for rule in rules:
                key = (entity_key, rule)
                if key not in patterns_map:
                    patterns_map[key] = {"entity_key": entity_key, "rule": rule, "count": 0}
                patterns_map[key]["count"] += 1

        # Group by entity mapping rules linearly
        entity_rule_groups = {}
        for (entity, rule), data in patterns_map.items():
            if entity not in entity_rule_groups:
                entity_rule_groups[entity] = {"rules": [], "count": 0}
            entity_rule_groups[entity]["rules"].append(rule)
            entity_rule_groups[entity]["count"] += data["count"]

        patterns = []
        for entity, data in entity_rule_groups.items():
            patterns.append({
                "entity_key": entity,
                "rules": data["rules"],
                "count": data["count"]
            })

        return patterns
    except Exception as e:
        logger.error(f"Error fetching FP patterns: {e}")
        return []
