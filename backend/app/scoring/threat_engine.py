import logging
import time
import pandas as pd
from typing import Dict, Any

from app.ingestion.es_client import INDEX_NAMES, get_es_client
from app.features.feature_merger import run_feature_pipeline, store_feature_vectors
from app.models.model_manager import ModelManager, get_model_manager
from app.scoring.explainability import ExplainabilityEngine, explain_scoring_result, build_explanation_context
from app.scoring.correlator import AlertCorrelator
from app.ingestion.scheduler import bulk_index

from app.logging_config import get_logger

logger = get_logger(__name__)

class ThreatEngine:
    """The central orchestrator driving feature extraction, mathematical evaluations, and linguistic generation safely down pipeline arrays."""
    
    def __init__(self, es, model_manager: ModelManager, explainability_engine: ExplainabilityEngine):
        self.es = es
        self.model_manager = model_manager
        self.explainability_engine = explainability_engine
        self.correlator = AlertCorrelator()

    async def run_scoring_cycle(self, since_minutes=5) -> dict:
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
                    
                # Bind localized SHAP explainer attributes directly over anomaly outputs
                explained_res = explain_scoring_result(res, feature_row, self.explainability_engine)
                ctx = build_explanation_context(explained_res)
                
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
                await self.correlator.store_incident(self.es, inc)
            
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
