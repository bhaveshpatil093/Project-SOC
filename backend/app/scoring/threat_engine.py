import time
import uuid
import datetime
import pandas as pd
from typing import Any

from app.features.feature_merger import run_feature_pipeline
from app.logging_config import get_logger
from app.auth.team_manager import team_manager_instance
from app.ingestion.log_fetcher import fetch_by_entity

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
from app.storage import local_db
from app.ingestion.kibana_client import KibanaProxyClient
from app.config import settings

logger = get_logger(__name__)


class ThreatEngine:
    def __init__(self, kibana_client: KibanaProxyClient, model_manager: ModelManager, explainability_engine: ExplainabilityEngine, db_path: str) -> None:
        self.kibana_client = kibana_client
        self.model_manager = model_manager
        self.explainability_engine = explainability_engine
        self.db_path = db_path
        
        self.correlator = AlertCorrelator()
        self.baseline_learner = BaselineLearner()
        self.intel_enricher = ThreatIntelEnricher()
        self.pattern_detector = PatternDetector()
        self.temporal_analyzer = TemporalAnalyzer()
        self.entity_risk_scorer = EntityRiskScorer()

    async def assign_alert_to_team(self, alert: dict) -> str | None:
        try:
            teams = await team_manager_instance.list_teams(self.kibana_client)
            if not teams:
                return None
            assigned_team = teams[0].team_id
            alert["assigned_team"] = assigned_team
            alert["assigned_at"] = datetime.datetime.utcnow().isoformat() + "Z"
            return assigned_team
        except Exception as e:
            logger.error(f"Error assigning alert to team: {e}")
            return None

    async def run_scoring_cycle(self, since_minutes: int = 5) -> dict[str, Any]:
        start_t = time.time()

        # 1. Pipeline Execution
        feature_df, normalized_df = await run_feature_pipeline(self.kibana_client, since_minutes=since_minutes)
        if feature_df.empty:
            return {
                "scored": 0, "alerts_above_threshold": 0, "critical": 0,
                "high": 0, "medium": 0, "low": 0, "cycle_time_ms": 0.0
            }

        # Save feature mapping states to SQLite
        for _, row in feature_df.iterrows():
            record = {
                "feature_id": str(uuid.uuid4()),
                "entity_key": row.get("entity_key"),
                "host_id": row.get("host_id", ""),
                "user_name": row.get("user_name", ""),
                "window_bucket": row.get("window_bucket"),
                "feature_vector": row.to_dict(),
                "feature_names": list(row.index),
                "created_at": datetime.datetime.utcnow().isoformat() + "Z"
            }
            await local_db.insert_feature_vector(self.db_path, record)

        # 2. Universal ML Inference
        scoring_results = await self.model_manager.score_all_entities(feature_df, normalized_df)

        # 3. Filtering and Alerting Execution Boundaries
        alerts_to_store = []
        stats = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for res in scoring_results:
            if res.threat_score > 0.3:
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
                timestamp_str = feature_row.get("timestamp") or datetime.datetime.utcnow().isoformat()
                try:
                    ts = pd.to_datetime(timestamp_str)
                except:
                    ts = datetime.datetime.utcnow()

                temporal_baseline = await self.temporal_analyzer.load_temporal_baseline(self.kibana_client, res.entity_key)
                if not temporal_baseline:
                    temporal_baseline = TemporalBaseline(res.entity_key, {}, (9, 18), False)

                temporal_ctx = self.temporal_analyzer.compute_temporal_anomaly_score(feature_row, temporal_baseline, ts)

                res.threat_score = min(1.0, res.threat_score * temporal_ctx["off_hours_severity"])
                res.human_explanation = f"Time Context: {temporal_ctx['context']}\n\n{res.human_explanation or ''}".strip()

                feature_row["temporal_context"] = temporal_ctx['context']
                feature_row["is_off_hours"] = temporal_ctx['is_off_hours']

                # Inject Baseline Behavior Deviations
                baseline = await self.baseline_learner.get_baseline(self.kibana_client, res.entity_key)
                if baseline:
                    devs = self.baseline_learner.compute_deviation_ratios(baseline, feature_row)
                    dev_ctx = self.baseline_learner.format_deviation_context(devs, feature_row, baseline)
                    if dev_ctx:
                        res.human_explanation = f"Behavior Context: {dev_ctx}\n\n{res.human_explanation or ''}".strip()

                explained_res = explain_scoring_result(res, feature_row, self.explainability_engine)
                ctx = build_explanation_context(explained_res)

                ctx = self.intel_enricher.enrich_alert(ctx, feature_row)
                intel = ctx.get("threat_intel", {})

                ctx["threat_score"] = self.intel_enricher.adjust_threat_score(ctx["threat_score"], intel)
                if ctx["threat_score"] >= 0.8:
                    ctx["threat_level"] = "critical"
                elif ctx["threat_score"] >= 0.6:
                    ctx["threat_level"] = "high"
                elif ctx["threat_score"] >= 0.4:
                    ctx["threat_level"] = "medium"
                else:
                    ctx["threat_level"] = "low"

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
                    
                ctx["alert_id"] = str(uuid.uuid4())
                ctx["created_at"] = datetime.datetime.utcnow().isoformat() + "Z"
                
                # SQLite mapping
                alert_dict = {
                    "alert_id": ctx["alert_id"],
                    "entity_key": ctx.get("entity_key"),
                    "host_id": feature_row.get("host_id", ""),
                    "user_name": feature_row.get("user_name", ""),
                    "log_type": "anomaly",
                    "threat_score": ctx.get("threat_score"),
                    "threat_level": ctx.get("threat_level"),
                    "anomaly_scores": ctx.get("anomaly_scores"),
                    "shap_features": ctx.get("shap_features"),
                    "triggered_rules": ctx.get("triggered_rules"),
                    "mitre_tactic": ctx.get("mitre_tactic"),
                    "mitre_technique": ctx.get("mitre_technique"),
                    "human_explanation": ctx.get("human_explanation"),
                    "alert_status": ctx.get("status", "open"),
                    "suppressed": 1 if ctx.get("suppressed") else 0,
                    "created_at": ctx["created_at"],
                    "raw_context": ctx
                }
                
                await local_db.insert_alert(self.db_path, alert_dict)
                alerts_to_store.append(ctx)

                lvl = explained_res.threat_level
                if lvl in stats:
                    stats[lvl] += 1

        # 4. Post-processing
        if alerts_to_store:
            from app.api.routes.websocket import manager
            from app.slm.rag_pipeline import _rag_pipeline

            incidents = self.correlator.correlate(alerts_to_store)
            for inc in incidents:
                inc_alerts = [a for a in alerts_to_store if a.get("alert_id") in inc.alert_ids]
                matches = self.pattern_detector.detect_patterns(inc, inc_alerts)
                from dataclasses import asdict
                inc.matched_patterns = [asdict(m) for m in matches]

                try:
                    await self.correlator.store_incident(self.kibana_client, inc)
                except Exception:
                    pass

                try:
                    from app.integrations.webhook_manager import webhook_manager
                    await webhook_manager.dispatch_event(self.kibana_client, "new_incident", {
                        "incident_id": inc.incident_id,
                        "attack_stage": inc.attack_stage,
                        "alert_count": len(inc.alert_ids),
                        "is_multi_stage": inc.is_multi_stage,
                        "link": f"http://soc.isro.gov.in/incidents/{inc.incident_id}",
                    })
                except Exception as wh_err:
                    logger.warning(f"Webhook incident dispatch failed: {wh_err}")

            for alert in alerts_to_store:
                if alert.get("threat_score", 0) > 0.3:
                    await _rag_pipeline.index_alert(alert)
                    await manager.broadcast({
                        "type": "new_alert",
                        "data": alert,
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    })

                    try:
                        from app.integrations.webhook_manager import webhook_manager
                        alert_payload = {
                            "id": alert.get("alert_id", ""),
                            "entity_key": alert.get("entity_key", ""),
                            "threat_level": alert.get("threat_level", ""),
                            "threat_score": alert.get("threat_score", 0),
                            "mitre_tactics": alert.get("mitre_tactics", []),
                            "human_explanation": alert.get("human_explanation", ""),
                            "link": f"http://soc.isro.gov.in/alerts/{alert.get('alert_id', '')}",
                        }
                        await webhook_manager.dispatch_event(self.kibana_client, "new_alert", {"alert": alert_payload})
                    except Exception as wh_err:
                        logger.warning(f"Webhook dispatch failed: {wh_err}")

            from app.cache.cache_manager import cache
            await cache.delete("alert_stats")
            if incidents:
                await cache.delete("incident_stats")

        # 5. Evolve baselines
        await self.baseline_learner.update_all_baselines(self.kibana_client, feature_df)

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
        alert = await local_db.get_alert(self.db_path, alert_id)
        return alert.get("raw_context", {}) if alert else {}

    async def list_alerts(self, status="open", limit=50, offset=0) -> dict:
        alerts = await local_db.list_alerts(self.db_path, status=status, limit=limit, offset=offset)
        return {
            "total": len(alerts),
            "alerts": [a.get("raw_context", {}) for a in alerts]
        }

    async def update_alert_status(self, alert_id: str, status: str):
        await local_db.update_alert_status(self.db_path, alert_id, status)

    async def get_entity_timeline(self, entity_key: str) -> list[dict]:
        host_id = entity_key.split("|")[0] if "|" in entity_key else entity_key
        user_name = entity_key.split("|")[1] if "|" in entity_key else ""
        
        # Pull alerts from SQLite
        all_alerts = await local_db.list_alerts(self.db_path, host_id=host_id, limit=1000)
        entity_alerts = [a for a in all_alerts if a.get("entity_key") == entity_key]
        
        # Pull raw logs from Kibana
        raw_logs = await fetch_by_entity(self.kibana_client, host_id, user_name, since_minutes=1440)
        
        combined = []
        for a in entity_alerts:
            ctx = a.get("raw_context", {})
            ctx["event_type"] = "alert"
            ctx["@timestamp"] = a.get("created_at")
            combined.append(ctx)
            
        for log_type, logs in raw_logs.items():
            for log in logs:
                log["event_type"] = "raw_log"
                log["log_type"] = log_type
                combined.append(log)
                
        # Sort combined list
        combined.sort(key=lambda x: x.get("@timestamp") or "", reverse=True)
        return combined

_threat_engine_instance = None

async def init_threat_engine():
    global _threat_engine_instance
    from app.config import settings
    
    kibana_client = KibanaProxyClient()
    mm = get_model_manager()
    ee = ExplainabilityEngine()

    _threat_engine_instance = ThreatEngine(kibana_client, mm, ee, db_path=settings.DB_PATH)

    # Pre-warm False Positive lists securely off Kibana boundaries
    from app.feedback.suppressor import get_suppressor
    await get_suppressor().refresh_suppression_list(settings.DB_PATH)

    logger.info("threat_engine_initialized", message="Central ThreatEngine fully initialized and wired to ML subsystems.")

def get_threat_engine() -> ThreatEngine:
    global _threat_engine_instance
    if _threat_engine_instance is None:
        raise RuntimeError("ThreatEngine accessed before async initialization. Check lifespan wrappers.")
    return _threat_engine_instance
