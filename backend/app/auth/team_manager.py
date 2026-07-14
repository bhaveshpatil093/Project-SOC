from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional
from app.auth.models import UserInDB, USERS_DB

from app.ingestion.es_client_protocol import supports_index_management
from app.logging_config import get_logger
logger = get_logger(__name__)

@dataclass
class Team:
    team_id: str
    name: str
    description: str
    members: list[str]
    alert_filters: dict
    shift_schedule: dict
    created_at: str

class TeamManager:
    INDEX_NAME = "soc-teams"

    async def initialize(self, es) -> None:
        if not supports_index_management(es):
            logger.info(
                "team_manager_index_skipped",
                index=self.INDEX_NAME,
                reason="KibanaProxyClient does not support index management",
            )
            return

        exists = await es.indices.exists(index=self.INDEX_NAME)
        if not exists:
            mapping = {
                "mappings": {
                    "properties": {
                        "team_id": {"type": "keyword"},
                        "name": {"type": "keyword"},
                        "description": {"type": "text"},
                        "members": {"type": "keyword"},
                        "alert_filters": {"type": "object"},
                        "shift_schedule": {"type": "object"},
                        "created_at": {"type": "date"}
                    }
                }
            }
            await es.indices.create(index=self.INDEX_NAME, body=mapping)
            logger.info(f"Created index {self.INDEX_NAME}")
            
            # Create a default team if not exists
            default_team = Team(
                team_id="ISTRAC-SOC-L1",
                name="ISTRAC-SOC-L1",
                description="Level 1 SOC Analysts",
                members=["analyst"],
                alert_filters={"max_threat_level": "medium"},
                shift_schedule={"morning": {"start": 6, "end": 14}, "afternoon": {"start": 14, "end": 22}, "night": {"start": 22, "end": 6}},
                created_at=datetime.utcnow().isoformat() + "Z"
            )
            await self.create_team(es, default_team)

    async def create_team(self, es, team: Team) -> Team:
        try:
            await es.index(index=self.INDEX_NAME, id=team.team_id, body=asdict(team))
            return team
        except Exception as e:
            logger.error(f"Error creating team: {e}")
            raise

    async def get_team(self, es, team_id: str) -> Optional[Team]:
        try:
            resp = await es.get(index=self.INDEX_NAME, id=team_id, ignore=[404])
            if resp and resp.get("found"):
                return Team(**resp["_source"])
            return None
        except Exception as e:
            logger.error(f"Error fetching team {team_id}: {e}")
            return None

    async def list_teams(self, es) -> List[Team]:
        try:
            resp = await es.search(index=self.INDEX_NAME, body={"query": {"match_all": {}}, "size": 100}, ignore_unavailable=True)
            return [Team(**hit["_source"]) for hit in resp.get("hits", {}).get("hits", [])]
        except Exception as e:
            logger.error(f"Error listing teams: {e}")
            return []

    async def update_team(self, es, team_id: str, updates: dict) -> Optional[Team]:
        try:
            await es.update(index=self.INDEX_NAME, id=team_id, body={"doc": updates})
            return await self.get_team(es, team_id)
        except Exception as e:
            logger.error(f"Error updating team {team_id}: {e}")
            raise

    async def add_member(self, es, team_id: str, username: str):
        try:
            team = await self.get_team(es, team_id)
            if team and username not in team.members:
                team.members.append(username)
                await self.update_team(es, team_id, {"members": team.members})
                # Update user in mock DB
                if username in USERS_DB:
                    USERS_DB[username].team_id = team_id
        except Exception as e:
            logger.error(f"Error adding member to team {team_id}: {e}")
            raise

    async def remove_member(self, es, team_id: str, username: str):
        try:
            team = await self.get_team(es, team_id)
            if team and username in team.members:
                team.members.remove(username)
                await self.update_team(es, team_id, {"members": team.members})
                if username in USERS_DB and USERS_DB[username].team_id == team_id:
                    USERS_DB[username].team_id = None
        except Exception as e:
            logger.error(f"Error removing member from team {team_id}: {e}")
            raise

    async def get_team_stats(self, es, team_id: str, since_days: int = 7) -> dict:
        since_time = (datetime.utcnow() - __import__("datetime").timedelta(days=since_days)).isoformat() + "Z"
        
        try:
            # Query for alerts assigned to this team or closed by users of this team
            # Simplified version: get all alerts and filter in memory, or do a targeted aggregation.
            team = await self.get_team(es, team_id)
            if not team:
                return {}
                
            resp = await es.search(index="soc-alerts", body={
                "query": {
                    "bool": {
                        "must": [
                            {"range": {"timestamp": {"gte": since_time}}}
                        ],
                        "should": [
                            {"match": {"assigned_team": team_id}},
                            {"terms": {"user_name": team.members}}
                        ],
                        "minimum_should_match": 1
                    }
                },
                "size": 1000
            }, ignore_unavailable=True)
            
            alerts = [hit["_source"] for hit in resp.get("hits", {}).get("hits", [])]
            
            triaged = [a for a in alerts if a.get("status") in ["resolved", "closed", "true_positive", "false_positive"]]
            fps = [a for a in alerts if a.get("status") == "false_positive"]
            
            fp_rate = (len(fps) / len(triaged) * 100) if triaged else 0
            
            top_analysts = {}
            for a in triaged:
                user = a.get("user_name")
                if user in team.members:
                    top_analysts[user] = top_analysts.get(user, 0) + 1
                    
            analysts_list = [{"username": k, "triaged": v} for k, v in sorted(top_analysts.items(), key=lambda x: x[1], reverse=True)]
            
            return {
                "alerts_triaged": len(triaged),
                "avg_response_time": 25.5, # Mock value
                "fp_rate": round(fp_rate, 1),
                "top_analysts": analysts_list,
                "active_alerts": len([a for a in alerts if a.get("status") not in ["resolved", "closed", "true_positive", "false_positive"]])
            }
        except Exception as e:
            logger.error(f"Error fetching team stats for {team_id}: {e}")
            return {}

team_manager_instance = TeamManager()
