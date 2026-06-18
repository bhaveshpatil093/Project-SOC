import logging
from app.models.model_manager import ScoringResult

logger = logging.getLogger(__name__)

class FalsePositiveSuppressor:
    """Manages active ML suppression states averting cyclic alert storm behaviors."""
    
    def __init__(self):
        self.suppressed_entities = {}
        self.stats = {"suppressed_count": 0, "last_refresh": None}

    async def refresh_suppression_list(self, es):
        from app.feedback.label_store import get_fp_suppression_patterns
        from datetime import datetime
        
        patterns = await get_fp_suppression_patterns(es)
        new_map = {}
        for p in patterns:
            entity = p["entity_key"]
            rules = p["rules"]
            if not rules:
                new_map[entity] = ["ALL"]
            else:
                new_map[entity] = rules
                
        self.suppressed_entities = new_map
        self.stats["last_refresh"] = datetime.utcnow().isoformat() + "Z"
        logger.info(f"Refreshed FP suppression list. Tracking {len(new_map)} explicitly suppressed entities natively.")

    def should_suppress(self, result: ScoringResult, feature_row: dict) -> tuple[bool, str]:
        """Calculates precise overlap bindings matching anomaly entities directly overlapping mapped false positive heuristics."""
        if result.entity_key in self.suppressed_entities:
            suppressed_rules = self.suppressed_entities[result.entity_key]
            
            if "ALL" in suppressed_rules:
                self.stats["suppressed_count"] += 1
                return True, f"Entity {result.entity_key} historically marked as globally False Positive."
                
            overlap = set(result.triggered_rules).intersection(set(suppressed_rules))
            if overlap:
                self.stats["suppressed_count"] += 1
                return True, f"Entity {result.entity_key} + Rule {list(overlap)[0]} historically marked as False Positive."
        
        return False, ""

    def get_suppression_stats(self) -> dict:
        return self.stats

_suppressor_instance = FalsePositiveSuppressor()

def get_suppressor() -> FalsePositiveSuppressor:
    return _suppressor_instance
