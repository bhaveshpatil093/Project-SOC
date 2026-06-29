from dataclasses import asdict, dataclass, field
from datetime import datetime

from app.logging_config import get_logger
logger = get_logger(__name__)

@dataclass
class EntityRiskProfile:
    entity_key: str
    current_risk_score: float = 0.0
    peak_risk_score: float = 0.0
    risk_level: str = "low"
    total_alerts: int = 0
    total_incidents: int = 0
    last_alert_at: str = None
    first_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    top_tactics: list[str] = field(default_factory=list)
    top_techniques: list[str] = field(default_factory=list)
    is_watchlisted: bool = False
    watchlist_reason: str = None
    risk_trend: str = "stable"
    recent_scores: list[float] = field(default_factory=list)

class EntityRiskScorer:
    def __init__(self, decay_half_life_hours: float = 48.0):
        self.decay_half_life_hours = decay_half_life_hours
        self.INDEX_NAME = "soc-entity-profiles"

    def compute_risk_level(self, score: float) -> str:
        if score < 20: return "low"
        if score < 50: return "medium"
        if score < 75: return "high"
        return "critical"

    def _determine_trend(self, recent_scores: list[float]) -> str:
        if len(recent_scores) < 3:
            return "stable"

        mid = len(recent_scores) // 2
        older = recent_scores[:mid]
        newer = recent_scores[mid:]

        older_avg = sum(older) / len(older)
        newer_avg = sum(newer) / len(newer)

        if newer_avg > older_avg + 5:
            return "increasing"
        if newer_avg < older_avg - 5:
            return "decreasing"
        return "stable"

    def update_risk_profile(self, profile: EntityRiskProfile, new_alert_score: float, new_alert: dict) -> EntityRiskProfile:
        now = datetime.utcnow()

        if profile.last_alert_at:
            try:
                last_dt = datetime.fromisoformat(profile.last_alert_at.replace("Z", ""))
                hours_since_last = (now - last_dt).total_seconds() / 3600.0
            except ValueError:
                hours_since_last = 0.0
        else:
            hours_since_last = 0.0

        # Decay the score
        decay_factor = 0.5 ** (hours_since_last / self.decay_half_life_hours) if hours_since_last > 0 else 1.0
        decayed = profile.current_risk_score * decay_factor

        # Add new alert contribution
        # new_alert_score is 0.0-1.0 from ThreatEngine
        # We scale it to 20 points per 1.0 alert score to cumulatively build up.
        new_cumulative = min(100.0, decayed + (new_alert_score * 20))

        profile.current_risk_score = float(new_cumulative)
        profile.peak_risk_score = max(profile.peak_risk_score, profile.current_risk_score)
        profile.risk_level = self.compute_risk_level(profile.current_risk_score)

        profile.total_alerts += 1
        profile.last_alert_at = now.isoformat() + "Z"
        profile.last_updated = now.isoformat() + "Z"

        # Keep recent scores queue
        profile.recent_scores.append(float(new_cumulative))
        if len(profile.recent_scores) > 10:
            profile.recent_scores = profile.recent_scores[-10:]

        profile.risk_trend = self._determine_trend(profile.recent_scores)

        # Update Tactics/Techniques aggregations heuristically
        tactics = set(profile.top_tactics)
        techniques = set(profile.top_techniques)
        if new_alert.get("mitre_tactics"):
            tactics.update(new_alert["mitre_tactics"])
        if new_alert.get("mitre_technique_ids"):
            techniques.update(new_alert["mitre_technique_ids"])

        profile.top_tactics = list(tactics)[:5]
        profile.top_techniques = list(techniques)[:10]

        return profile

    async def get_or_create_profile(self, es, entity_key: str) -> EntityRiskProfile:
        try:
            res = await es.get(index=self.INDEX_NAME, id=entity_key, ignore_unavailable=True)
            if res and res.get("found"):
                data = res["_source"]
                return EntityRiskProfile(**data)
        except Exception as e:
            logger.debug(f"Profile not found for {entity_key}, returning new. {e}")

        return EntityRiskProfile(entity_key=entity_key)

    async def save_profile(self, es, profile: EntityRiskProfile):
        try:
            doc = asdict(profile)
            await es.index(index=self.INDEX_NAME, id=profile.entity_key, document=doc)
        except Exception as e:
            logger.error(f"Failed to save profile {profile.entity_key}: {e}")

    async def get_top_risk_entities(self, es, n: int = 10) -> list[dict]:
        try:
            query = {
                "size": n,
                "sort": [{"current_risk_score": {"order": "desc"}}],
                "query": {"match_all": {}}
            }
            res = await es.search(index=self.INDEX_NAME, body=query, ignore_unavailable=True)
            return [hit["_source"] for hit in res.get("hits", {}).get("hits", [])]
        except Exception as e:
            logger.error(f"Failed to get top entities: {e}")
            return []

    async def get_watchlist(self, es) -> list[dict]:
        try:
            query = {
                "size": 100,
                "query": {"term": {"is_watchlisted": True}}
            }
            res = await es.search(index=self.INDEX_NAME, body=query, ignore_unavailable=True)
            return [hit["_source"] for hit in res.get("hits", {}).get("hits", [])]
        except Exception as e:
            logger.error(f"Failed to get watchlist: {e}")
            return []

    async def add_to_watchlist(self, es, entity_key: str, reason: str):
        profile = await self.get_or_create_profile(es, entity_key)
        profile.is_watchlisted = True
        profile.watchlist_reason = reason
        profile.last_updated = datetime.utcnow().isoformat() + "Z"
        await self.save_profile(es, profile)

    async def remove_from_watchlist(self, es, entity_key: str):
        profile = await self.get_or_create_profile(es, entity_key)
        profile.is_watchlisted = False
        profile.watchlist_reason = None
        profile.last_updated = datetime.utcnow().isoformat() + "Z"
        await self.save_profile(es, profile)
