from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
import uuid
from typing import List, Dict, Any
from app.logging_config import get_logger
from app.ingestion.es_client import INDEX_NAMES

logger = get_logger(__name__)

@dataclass
class Incident:
    incident_id: str
    entity_key: str
    host_id: str
    user_name: str | None
    started_at: datetime
    last_seen: datetime
    duration_seconds: float
    alert_ids: list[str]
    alert_count: int
    log_types_involved: list[str]
    max_threat_score: float
    mean_threat_score: float
    incident_threat_score: float
    threat_level: str
    mitre_tactics: list[str]
    mitre_techniques: list[str]
    attack_stage: str
    is_multi_stage: bool
    status: str
    created_at: datetime

class AlertCorrelator:
    def __init__(self, time_window_minutes: int = 15, min_alerts_for_incident: int = 2, score_threshold: float = 0.4):
        self.time_window_minutes = time_window_minutes
        self.min_alerts_for_incident = min_alerts_for_incident
        self.score_threshold = score_threshold

    def correlate(self, alerts: List[Dict[str, Any]]) -> List[Incident]:
        if not alerts:
            return []

        # Group alerts by entity_key
        entity_groups = {}
        for alert in alerts:
            key = f"{alert.get('host_id', '')}:{alert.get('user_name', '')}"
            entity_groups.setdefault(key, []).append(alert)

        incidents = []
        for key, entity_alerts in entity_groups.items():
            # Sort by timestamp
            entity_alerts.sort(key=lambda a: self._parse_date(a.get("timestamp", datetime.utcnow().isoformat())))
            
            # Simple clustering by time window
            clusters = []
            current_cluster = []
            cluster_start = None

            for alert in entity_alerts:
                ts = self._parse_date(alert.get("timestamp", datetime.utcnow().isoformat()))
                if not current_cluster:
                    current_cluster.append(alert)
                    cluster_start = ts
                else:
                    if (ts - cluster_start).total_seconds() <= self.time_window_minutes * 60:
                        current_cluster.append(alert)
                    else:
                        clusters.append(current_cluster)
                        current_cluster = [alert]
                        cluster_start = ts
            
            if current_cluster:
                clusters.append(current_cluster)

            for cluster in clusters:
                max_score = max((a.get("threat_score", 0.0) for a in cluster), default=0.0)
                if len(cluster) >= self.min_alerts_for_incident or max_score >= 0.8:
                    incident = self._create_incident_from_cluster(cluster)
                    if incident:
                        incidents.append(incident)

        return incidents

    def _parse_date(self, date_str: str | datetime) -> datetime:
        if isinstance(date_str, datetime):
            return date_str
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return datetime.utcnow()

    def _create_incident_from_cluster(self, cluster: List[Dict[str, Any]]) -> Incident:
        if not cluster:
            return None

        entity_key = f"{cluster[0].get('host_id', '')}:{cluster[0].get('user_name', '')}"
        host_id = cluster[0].get('host_id', '')
        user_name = cluster[0].get('user_name', None)
        
        timestamps = [self._parse_date(a.get("timestamp", datetime.utcnow().isoformat())) for a in cluster]
        started_at = min(timestamps)
        last_seen = max(timestamps)
        duration_seconds = (last_seen - started_at).total_seconds()
        
        alert_ids = [a.get("id") or a.get("_id") for a in cluster if (a.get("id") or a.get("_id"))]
        if not alert_ids: # Provide fallback UUIDs if not yet indexed
            alert_ids = [str(uuid.uuid4()) for _ in cluster]

        log_types_involved = list(set(a.get("log_type") for a in cluster if a.get("log_type")))
        
        scores = [a.get("threat_score", 0.0) for a in cluster]
        max_threat_score = max(scores, default=0.0)
        mean_threat_score = sum(scores) / len(scores) if scores else 0.0
        
        multi_log_type_bonus = 0.2 if len(log_types_involved) >= 2 else 0.0
        incident_threat_score = (max_threat_score * 0.5) + (mean_threat_score * 0.3) + multi_log_type_bonus
        incident_threat_score = min(incident_threat_score, 1.0) # cap at 1.0
        
        if incident_threat_score >= 0.8:
            threat_level = "critical"
        elif incident_threat_score >= 0.6:
            threat_level = "high"
        elif incident_threat_score >= 0.4:
            threat_level = "medium"
        else:
            threat_level = "low"

        mitre_tactics = list(set(a.get("mitre_tactic") for a in cluster if a.get("mitre_tactic")))
        mitre_techniques = list(set(a.get("mitre_technique") for a in cluster if a.get("mitre_technique")))
        
        attack_stage = self.determine_attack_stage(mitre_tactics)
        is_multi_stage = len(mitre_tactics) >= 3

        return Incident(
            incident_id=f"INC-{uuid.uuid4()}",
            entity_key=entity_key,
            host_id=host_id,
            user_name=user_name,
            started_at=started_at,
            last_seen=last_seen,
            duration_seconds=duration_seconds,
            alert_ids=alert_ids,
            alert_count=len(cluster),
            log_types_involved=log_types_involved,
            max_threat_score=max_threat_score,
            mean_threat_score=mean_threat_score,
            incident_threat_score=incident_threat_score,
            threat_level=threat_level,
            mitre_tactics=mitre_tactics,
            mitre_techniques=mitre_techniques,
            attack_stage=attack_stage,
            is_multi_stage=is_multi_stage,
            status="active",
            created_at=datetime.utcnow()
        )

    def determine_attack_stage(self, tactics: List[str]) -> str:
        if not tactics:
            return "unknown"
            
        stages = set()
        for t in tactics:
            t_lower = t.lower()
            if "reconnaissance" in t_lower:
                stages.add("reconnaissance")
            elif "initial access" in t_lower or "execution" in t_lower:
                stages.add("initial_access")
            elif "persistence" in t_lower or "privilege escalation" in t_lower:
                stages.add("persistence")
            elif "lateral movement" in t_lower or "discovery" in t_lower:
                stages.add("lateral_movement")
            elif "collection" in t_lower or "exfiltration" in t_lower:
                stages.add("exfiltration")
        
        if len(stages) > 1:
            return "multi_stage"
        elif len(stages) == 1:
            return list(stages)[0]
        else:
            return "unknown"

    def merge_incidents(self, existing: Incident, new_alerts: List[Dict[str, Any]]) -> Incident:
        new_timestamps = [self._parse_date(a.get("timestamp", datetime.utcnow().isoformat())) for a in new_alerts]
        all_timestamps = [existing.started_at, existing.last_seen] + new_timestamps
        
        existing.started_at = min(all_timestamps)
        existing.last_seen = max(all_timestamps)
        existing.duration_seconds = (existing.last_seen - existing.started_at).total_seconds()
        
        new_ids = [a.get("id") or a.get("_id") for a in new_alerts if (a.get("id") or a.get("_id"))]
        existing.alert_ids = list(set(existing.alert_ids + new_ids))
        existing.alert_count = len(existing.alert_ids)
        
        new_logs = [a.get("log_type") for a in new_alerts if a.get("log_type")]
        existing.log_types_involved = list(set(existing.log_types_involved + new_logs))
        
        # We don't have all historical alert scores readily available here, so we approximate
        new_scores = [a.get("threat_score", 0.0) for a in new_alerts]
        if new_scores:
            existing.max_threat_score = max(existing.max_threat_score, max(new_scores))
            # Rough mean update
            existing.mean_threat_score = (existing.mean_threat_score + sum(new_scores)/len(new_scores)) / 2.0
            
        multi_log_type_bonus = 0.2 if len(existing.log_types_involved) >= 2 else 0.0
        incident_threat_score = (existing.max_threat_score * 0.5) + (existing.mean_threat_score * 0.3) + multi_log_type_bonus
        existing.incident_threat_score = min(incident_threat_score, 1.0)
        
        if existing.incident_threat_score >= 0.8:
            existing.threat_level = "critical"
        elif existing.incident_threat_score >= 0.6:
            existing.threat_level = "high"
        elif existing.incident_threat_score >= 0.4:
            existing.threat_level = "medium"
        else:
            existing.threat_level = "low"

        new_tactics = [a.get("mitre_tactic") for a in new_alerts if a.get("mitre_tactic")]
        existing.mitre_tactics = list(set(existing.mitre_tactics + new_tactics))
        
        new_techniques = [a.get("mitre_technique") for a in new_alerts if a.get("mitre_technique")]
        existing.mitre_techniques = list(set(existing.mitre_techniques + new_techniques))
        
        existing.attack_stage = self.determine_attack_stage(existing.mitre_tactics)
        existing.is_multi_stage = len(existing.mitre_tactics) >= 3
        
        return existing

    async def store_incident(self, es, incident: Incident):
        doc = asdict(incident)
        doc["started_at"] = doc["started_at"].isoformat()
        doc["last_seen"] = doc["last_seen"].isoformat()
        doc["created_at"] = doc["created_at"].isoformat()
        
        try:
            await es.index(index=INDEX_NAMES["incidents"], id=incident.incident_id, document=doc)
            logger.info("incident_stored", incident_id=incident.incident_id, threat_level=incident.threat_level)
        except Exception as e:
            logger.error("failed_to_store_incident", incident_id=incident.incident_id, error=str(e))

    async def get_active_incidents(self, es, limit: int = 20) -> List[Incident]:
        query = {
            "size": limit,
            "sort": [{"last_seen": {"order": "desc"}}],
            "query": {
                "match": {
                    "status": "active"
                }
            }
        }
        try:
            resp = await es.search(index=INDEX_NAMES["incidents"], body=query)
            hits = resp.get("hits", {}).get("hits", [])
            incidents = []
            for h in hits:
                s = h["_source"]
                s["started_at"] = self._parse_date(s["started_at"])
                s["last_seen"] = self._parse_date(s["last_seen"])
                s["created_at"] = self._parse_date(s["created_at"])
                incidents.append(Incident(**s))
            return incidents
        except Exception as e:
            logger.error("failed_to_get_active_incidents", error=str(e))
            return []
