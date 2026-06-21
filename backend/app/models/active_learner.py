import logging

import numpy as np

from app.models.model_manager import ScoringResult

logger = logging.getLogger(__name__)

class ActiveLearner:
    def __init__(self, uncertainty_threshold_range: tuple = (0.35, 0.65)):
        self.uncertainty_threshold_range = uncertainty_threshold_range

    def compute_model_disagreement(self, result: ScoringResult) -> float:
        """
        Computes the standard deviation across different model anomaly scores.
        High std dev indicates models disagree (e.g., IF=0.9, AE=0.1).
        """
        scores = [result.network_anomaly_score, result.process_anomaly_score, result.rule_score]
        return float(np.std(scores))

    def compute_uncertainty_score(self, scoring_result: ScoringResult) -> float:
        """
        Measures overall model uncertainty (0-1).
        1. Proximity to 0.5 boundary (uncertain).
        2. Model disagreement variance.
        """
        # Proximity to 0.5: Maximum uncertainty (1.0) is at 0.5, minimum (0.0) is at 0 or 1.
        proximity = 1.0 - (abs(scoring_result.threat_score - 0.5) * 2)

        # Disagreement
        disagreement = self.compute_model_disagreement(scoring_result)

        # Combined
        uncertainty = (0.6 * proximity) + (0.4 * disagreement)

        # Bound between 0 and 1
        return float(np.clip(uncertainty, 0.0, 1.0))

    def select_samples_for_labeling(self, scoring_results: list[ScoringResult],
                                   already_labeled: set[str],
                                   n_samples: int = 10) -> list[dict]:
        """
        Selects top n_samples based on uncertainty, filtering out already labeled ones.
        Also applies a diversity filter (max 2 from same entity_key).
        Returns list of dicts with scoring result and uncertainty info.
        """
        candidates = []
        for res in scoring_results:
            if res.entity_key in already_labeled:
                continue

            uncertainty = self.compute_uncertainty_score(res)

            # Form reason
            disagreement = self.compute_model_disagreement(res)
            if disagreement > 0.2:
                reason = f"Models disagree: IF={res.network_anomaly_score:.2f}, AE={res.process_anomaly_score:.2f}, Rule={res.rule_score:.2f}"
            elif 0.4 <= res.threat_score <= 0.6:
                reason = f"Boundary score ({res.threat_score:.2f}): highly uncertain."
            else:
                reason = "High general uncertainty."

            candidates.append({
                "alert": res.__dict__,
                "uncertainty_score": uncertainty,
                "model_scores": {
                    "network": res.network_anomaly_score,
                    "process": res.process_anomaly_score,
                    "sequence": res.sequence_anomaly_score,
                    "rule": res.rule_score
                },
                "reason_for_selection": reason
            })

        # Sort descending by uncertainty
        candidates.sort(key=lambda x: x["uncertainty_score"], reverse=True)

        # Diversity filter
        final_selection = []
        entity_counts = {}

        for cand in candidates:
            ekey = cand["alert"]["entity_key"]
            if entity_counts.get(ekey, 0) < 2:
                final_selection.append(cand)
                entity_counts[ekey] = entity_counts.get(ekey, 0) + 1
            if len(final_selection) >= n_samples:
                break

        return final_selection

    async def get_labeling_queue(self, es, n_samples: int = 10) -> list[dict]:
        """
        Fetches recent unscored alerts (last 24h) lacking feedback, evaluates uncertainty,
        and returns the top n_samples for labeling.
        """
        from datetime import datetime, timedelta

        from app.feedback.label_store import FEEDBACK_INDEX

        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()

        # 1. Fetch already labeled entity keys (to avoid asking again)
        # In a real system we'd check if the specific alert was labeled, but
        # we'll fetch recently labeled alerts.
        query_feedback = {
            "size": 10000,
            "_source": ["alert_id", "entity_key"],
            "query": {"match_all": {}}
        }
        already_labeled_keys = set()
        already_labeled_ids = set()
        try:
            res_fb = await es.search(index=FEEDBACK_INDEX, body=query_feedback, ignore_unavailable=True)
            for hit in res_fb.get("hits", {}).get("hits", []):
                src = hit.get("_source", {})
                if src.get("entity_key"):
                    already_labeled_keys.add(src["entity_key"])
                if src.get("alert_id"):
                    already_labeled_ids.add(src["alert_id"])
        except Exception:
            pass

        # 2. Fetch recent alerts from soc-processed-alerts
        query_alerts = {
            "size": 1000,
            "sort": [{"timestamp": {"order": "desc"}}],
            "query": {
                "range": {"timestamp": {"gte": yesterday}}
            }
        }

        raw_alerts = []
        try:
            res_alerts = await es.search(index="soc-processed-alerts", body=query_alerts, ignore_unavailable=True)
            hits = res_alerts.get("hits", {}).get("hits", [])
            for h in hits:
                alert = h["_source"]
                alert["id"] = h["_id"]
                if alert["id"] not in already_labeled_ids and alert.get("entity_key") not in already_labeled_keys:
                    raw_alerts.append(alert)
        except Exception as e:
            logger.error(f"Error fetching alerts for labeling queue: {e}")
            return []

        # 3. Re-hydrate ScoringResult to compute uncertainty
        scoring_results = []
        for a in raw_alerts:
            # We map the dict back to ScoringResult for the function
            sr = ScoringResult(
                entity_key=a.get("entity_key", ""),
                window_bucket=a.get("window_bucket", ""),
                network_anomaly_score=a.get("network_anomaly_score", 0.0),
                process_anomaly_score=a.get("process_anomaly_score", 0.0),
                sequence_anomaly_score=a.get("sequence_anomaly_score", 0.0),
                rule_score=a.get("rule_score", 0.0),
                triggered_rules=a.get("triggered_rules", []),
                mitre_tactics=a.get("mitre_tactics", []),
                mitre_technique_ids=a.get("mitre_technique_ids", []),
                threat_score=a.get("threat_score", 0.0),
                threat_level=a.get("threat_level", "low"),
                top_features=a.get("top_features", []),
                human_explanation=a.get("human_explanation", "")
            )
            # monkey patch id back into dict representation later
            sr._raw_id = a["id"]
            sr._timestamp = a.get("timestamp")
            scoring_results.append(sr)

        # 4. Select top candidates
        selected = self.select_samples_for_labeling(scoring_results, already_labeled_keys, n_samples)

        # Put id and timestamp back into alert dict
        for cand in selected:
            # retrieve from monkey patch
            raw_obj = [sr for sr in scoring_results if sr.entity_key == cand["alert"]["entity_key"] and sr.window_bucket == cand["alert"]["window_bucket"]][0]
            cand["alert"]["id"] = getattr(raw_obj, "_raw_id", "")
            cand["alert"]["timestamp"] = getattr(raw_obj, "_timestamp", "")

        return selected

    async def get_labeling_stats(self, es) -> dict:
        """
        Returns stats about the current labeling backlog and uncertainty distributions.
        """
        try:
            queue = await self.get_labeling_queue(es, n_samples=1000)
            if not queue:
                return {
                    "total_unlabeled": 0,
                    "avg_uncertainty": 0.0,
                    "high_uncertainty_count": 0,
                    "estimated_labels_needed_for_retrain": 50
                }

            total = len(queue)
            avg_u = sum(c["uncertainty_score"] for c in queue) / total
            high_u = sum(1 for c in queue if c["uncertainty_score"] > 0.6)

            # Simple heuristic: 1 label = 0.01 reduction in uncertainty
            # Require at least 50 labels
            needed = max(50, int(high_u * 0.5))

            return {
                "total_unlabeled": total,
                "avg_uncertainty": round(avg_u, 3),
                "high_uncertainty_count": high_u,
                "estimated_labels_needed_for_retrain": needed
            }
        except Exception as e:
            logger.error(f"Error computing labeling stats: {e}")
            return {
                "total_unlabeled": 0,
                "avg_uncertainty": 0.0,
                "high_uncertainty_count": 0,
                "estimated_labels_needed_for_retrain": 50
            }
