import time
from datetime import datetime

import pandas as pd

from app.features.feature_merger import run_feature_pipeline, store_feature_vectors
from app.ingestion.es_client import INDEX_NAMES, get_es_client
from app.ingestion.scheduler import bulk_index
from app.logging_config import get_logger
from app.auth.team_manager import team_manager_instance

from app.models.baseline_learner import BaselineLearner
from app.models.model_manager import ModelManager, get_model_manager
from app.models.pattern_detector import PatternDetector
from app.models.temporal_analyzer import TemporalAnalyzer, TemporalBaseline
from app.scoring.correlator import AlertCorrelator
from app.scoring.entity_risk import EntityRiskScorer
from app.scoring.explainability import (
    ExplainabilityEngine,
    build_explanation_context,
    explain_scoring_result,
)
from app.scoring.threat_intel import ThreatIntelEnricher

logger = get_logger(__name__)

from typing import Any


class ThreatEngine:

    async def assign_alert_to_team(self, es, alert: dict) -> str | None:
        try:
            teams = await team_manager_instance.list_teams(es)
            if not teams:
                return None
            
            # Simple assignment: pick first team or base it on workload
            # For now, just assign to the first team available
            assigned_team = teams[0].team_id
            alert["assigned_team"] = assigned_team
            alert["assigned_at"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
            return assigned_team
        except Exception as e:
            logger.error(f"Error assigning alert to team: {e}")
            return None

    """The central orchestrator driving feature extraction, mathematical evaluations, and linguistic generation safely down pipeline arrays."""

    def __init__(self, es: "AsyncElasticsearch", model_manager: ModelManager, explainability_engine: ExplainabilityEngine) -> None:
        """Initialize the ThreatEngine orchestrator.
        
        Args:
            es: AsyncElasticsearch client instance.
            model_manager: ModelManager instance for inference.
            explainability_engine: ExplainabilityEngine for SHAP/LIME values.
        """
        self.es = es
        self.model_manager = model_manager
        self.explainability_engine = explainability_engine
        self.correlator = AlertCorrelator()
        self.baseline_learner = BaselineLearner()
        self.intel_enricher = ThreatIntelEnricher()
        self.pattern_detector = PatternDetector()
        self.temporal_analyzer = TemporalAnalyzer()
        self.entity_risk_scorer = EntityRiskScorer()

    async def run_scoring_cycle(self, since_minutes: int = 5) -> dict[str, Any]:
        """Execute a full feature extraction and scoring cycle across all active entities.

        Args:
            since_minutes: The lookback window in minutes to evaluate.

        Returns:
            Dictionary containing metrics for the scoring cycle including counts of critical, high, medium, and low alerts.
            
        Raises:
            ConnectionError: If Elasticsearch is unreachable.
        """
        start_t = time.time()

        # 1. Pipeline Execution
        feature_df, normalized_df = await run_feature_pipeline(self.es, since_minutes=since_minutes)
        if feature_df.empty:
            return {
                "scored": 0, "alerts_above_threshold": 0, "critical": 0,
                "high": 0, "medium": 0, "low": 0, "cycle_time_ms": 0.0
            }

        # Optional: Save feature mapping states to vector index seamlessly bounding upstream architectures
        await store_feature_vectors(self.es, feature_df)

        # 2. Universal ML Inference
        scoring_results = await self.model_manager.score_all_entities(feature_df, normalized_df)

        # 3. Filtering and Alerting Execution Boundaries
        alerts_to_store = []
        stats = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for res in scoring_results:
            if res.threat_score > 0.3:
                # Isolate context features identically tracking downstream dependencies
                row_match = feature_df[
                    (feature_df['entity_key'] == res.entity_key) &
                    (feature_df['window_bucket'] == res.window_bucket)
                ]

                feature_row = row_match.iloc[0].to_dict() if not row_match.empty else {}

                # Evaluate FP suppression heuristics locally
                from app.feedback.suppressor import get_suppressor
                suppressor = get_suppressor()
                is_suppressed, reason = suppressor.should_suppress(res, feature_row)
                if is_suppressed:
                    res.threat_score *= 0.1
                    res.threat_level = "low"

                # Temporal Pattern Analysis
                timestamp_str = feature_row.get("timestamp") or datetime.utcnow().isoformat()
                try:
                    ts = pd.to_datetime(timestamp_str)
                except:
                    ts = datetime.utcnow()

                temporal_baseline = await self.temporal_analyzer.load_temporal_baseline(self.es, res.entity_key)
                if not temporal_baseline:
                    # Create empty/default for the function if missing
                    temporal_baseline = TemporalBaseline(res.entity_key, {}, (9, 18), False)

                temporal_ctx = self.temporal_analyzer.compute_temporal_anomaly_score(feature_row, temporal_baseline, ts)

                # Boost threat score based on temporal anomaly
                res.threat_score = min(1.0, res.threat_score * temporal_ctx["off_hours_severity"])

                # Append temporal context string
                res.human_explanation = f"Time Context: {temporal_ctx['context']}\n\n{res.human_explanation or ''}".strip()

                # Add to row dict for downstream indexing (we'll inject it into ctx later)
                feature_row["temporal_context"] = temporal_ctx['context']
                feature_row["is_off_hours"] = temporal_ctx['is_off_hours']

                # Inject Baseline Behavior Deviations
                baseline = await self.baseline_learner.get_baseline(self.es, res.entity_key)
                if baseline:
                    devs = self.baseline_learner.compute_deviation_ratios(baseline, feature_row)
                    dev_ctx = self.baseline_learner.format_deviation_context(devs, feature_row, baseline)
                    if dev_ctx:
                        res.human_explanation = f"Behavior Context: {dev_ctx}\n\n{res.human_explanation or ''}".strip()

                # Bind localized SHAP explainer attributes directly over anomaly outputs
                explained_res = explain_scoring_result(res, feature_row, self.explainability_engine)
                ctx = build_explanation_context(explained_res)

                # Enrich with Offline Threat Intelligence
                ctx = self.intel_enricher.enrich_alert(ctx, feature_row)
                intel = ctx.get("threat_intel", {})

                # Adjust threat score dynamically
                ctx["threat_score"] = self.intel_enricher.adjust_threat_score(ctx["threat_score"], intel)
                # Recalculate threat level
                if ctx["threat_score"] >= 0.8:
                    ctx["threat_level"] = "critical"
                elif ctx["threat_score"] >= 0.6:
                    ctx["threat_level"] = "high"
                elif ctx["threat_score"] >= 0.4:
                    ctx["threat_level"] = "medium"
                else:
                    ctx["threat_level"] = "low"

                # Append Intel to explanation
                intel_strs = []
                if intel.get("ip_reputation", {}).get("src_ip_is_bad"):
                    intel_strs.append(f"Source IP matches known malicious range ({intel['ip_reputation']['matching_range']}).")
                if intel.get("ip_reputation", {}).get("dst_ip_is_bad"):
                    intel_strs.append(f"Destination IP matches known malicious range ({intel['ip_reputation']['matching_range']}).")
                if intel.get("process_reputation", {}).get("is_known_malicious"):
                    intel_strs.append(f"Process matches known malware/tool signature ({intel['process_reputation']['process_name']}).")
                if intel.get("domain_reputation", {}).get("has_suspicious_tld"):
                    intel_strs.append("Domain utilizes a highly suspicious TLD.")
                if intel.get("domain_reputation", {}).get("has_c2_pattern"):
                    intel_strs.append("Domain matches a known Command & Control pattern.")

                if intel_strs:
                    intel_summary = " Threat Intel: " + " ".join(intel_strs)
                    ctx["human_explanation"] = ctx["human_explanation"] + "\n\n" + intel_summary

                ctx["status"] = "open"
                if is_suppressed:
                    ctx["suppressed"] = True
                    ctx["suppression_reason"] = reason
                else:
                    ctx["suppressed"] = False

                alerts_to_store.append(ctx)

                lvl = explained_res.threat_level
                if lvl in stats:
                    stats[lvl] += 1

        # 4. Structural Storage Commits tracking natively against soc-processed-alerts
        if alerts_to_store:
            from app.api.routes.websocket import manager
            from app.slm.rag_pipeline import _rag_pipeline

            await bulk_index(self.es, alerts_to_store, INDEX_NAMES["alerts_processed"])

            # Group into unified incidents
            incidents = self.correlator.correlate(alerts_to_store)
            for inc in incidents:
                # Filter alerts bound to this specific incident for pattern detection
                inc_alerts = [a for a in alerts_to_store if a.get("id", a.get("_id")) in inc.alert_ids]
                matches = self.pattern_detector.detect_patterns(inc, inc_alerts)
                from dataclasses import asdict
                inc.matched_patterns = [asdict(m) for m in matches]

                await self.correlator.store_incident(self.es, inc)

                # Dispatch webhook event for new incident
                try:
                    from app.integrations.webhook_manager import webhook_manager
                    from dataclasses import asdict as _asdict
                    await webhook_manager.dispatch_event(self.es, "new_incident", {
                        "incident_id": inc.incident_id,
                        "attack_stage": inc.attack_stage,
                        "alert_count": len(inc.alert_ids),
                        "is_multi_stage": inc.is_multi_stage,
                        "link": f"http://soc.isro.gov.in/incidents/{inc.incident_id}",
                    })
                except Exception as wh_err:
                    logger.warning(f"Webhook incident dispatch failed: {wh_err}")

            import datetime
            for alert in alerts_to_store:
                if alert.get("threat_score", 0) > 0.3:
                    # Index directly into RAG Vector DB mapping real-time alert boundaries natively
                    await _rag_pipeline.index_alert(alert)

                    # In a real app we'd fetch the ES _id, but sending the payload is sufficient for real-time feed
                    await manager.broadcast({
                        "type": "new_alert",
                        "data": alert,
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    })

                    # Dispatch webhook event for new alert
                    try:
                        from app.integrations.webhook_manager import webhook_manager
                        alert_payload = {
                            "id": alert.get("_id", ""),
                            "entity_key": alert.get("entity_key", ""),
                            "threat_level": alert.get("threat_level", ""),
                            "threat_score": alert.get("threat_score", 0),
                            "mitre_tactics": alert.get("mitre_tactics", []),
                            "human_explanation": alert.get("human_explanation", ""),
                            "link": f"http://soc.isro.gov.in/alerts/{alert.get('_id', '')}",
                        }
                        await webhook_manager.dispatch_event(self.es, "new_alert", {"alert": alert_payload})
                    except Exception as wh_err:
                        logger.warning(f"Webhook dispatch failed: {wh_err}")

            from app.cache.cache_manager import cache
            await cache.delete("alert_stats")
            if incidents:
                await cache.delete("incident_stats")

        # 5. Evolve baselines incrementally over latest mapped boundaries
        await self.baseline_learner.update_all_baselines(self.es, feature_df)

        cycle_time = (time.time() - start_t) * 1000

        return {
            "scored": len(scoring_results),
            "alerts_above_threshold": len(alerts_to_store),
            "critical": stats["critical"],
            "high": stats["high"],
            "medium": stats["medium"],
            "low": stats["low"],
            "cycle_time_ms": round(cycle_time, 2)
        }

    async def get_alert(self, alert_id: str) -> dict:
        """Retrieves exact generated ML threat alerts directly via explicit ID mapping."""
        try:
            resp = await self.es.get(index=INDEX_NAMES["alerts_processed"], id=alert_id)
            return resp.get("_source", {})
        except Exception as e:
            logger.warning("get_alert_failed", alert_id=alert_id, error=str(e))
            return {}

    async def list_alerts(self, status="open", limit=50, offset=0) -> dict:
        """Fetches bulk aggregated ML alerts tracking bounding variables linearly."""
        query = {
            "from": offset,
            "size": limit,
            "sort": [{"timestamp": {"order": "desc"}}],
            "query": {
                "match": {
                    "status": status
                }
            }
        }
        try:
            resp = await self.es.search(index=INDEX_NAMES["alerts_processed"], body=query, ignore_unavailable=True)
            hits = resp.get("hits", {}).get("hits", [])
            return {
                "total": resp.get("hits", {}).get("total", {}).get("value", 0),
                "alerts": [{"id": h["_id"], **h["_source"]} for h in hits]
            }
        except Exception as e:
            logger.warning("list_alerts_failed", status=status, limit=limit, error=str(e))
            return {"total": 0, "alerts": []}

    async def update_alert_status(self, alert_id: str, status: str):
        """Overrides ML tracked alert states enabling interactive frontend mitigations."""
        body = {"doc": {"status": status}}
        try:
            await self.es.update(index=INDEX_NAMES["alerts_processed"], id=alert_id, body=body)
        except Exception as e:
            logger.error("update_alert_status_failed", alert_id=alert_id, status=status, error=str(e))


_threat_engine_instance = None

async def init_threat_engine():
    """Binds architectural components dynamically into native global singletons scaling inference endpoints."""
    global _threat_engine_instance
    es = await get_es_client()
    mm = get_model_manager()
    ee = ExplainabilityEngine()

    _threat_engine_instance = ThreatEngine(es, mm, ee)

    # Pre-warm False Positive lists securely off ES boundaries
    from app.feedback.suppressor import get_suppressor
    await get_suppressor().refresh_suppression_list(es)

    logger.info("threat_engine_initialized", message="Central ThreatEngine fully initialized and wired to ML subsystems.")

def get_threat_engine() -> ThreatEngine:
    global _threat_engine_instance
    if _threat_engine_instance is None:
        raise RuntimeError("ThreatEngine accessed before async initialization. Check lifespan wrappers.")
    return _threat_engine_instance
