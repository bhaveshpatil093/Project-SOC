import os

with open("backend/app/scoring/threat_engine.py", "r") as f:
    content = f.read()

import_stmt = "from app.auth.team_manager import team_manager_instance\n"
content = content.replace("from app.logging_config import get_logger", "from app.logging_config import get_logger\n" + import_stmt)

assignment_fn = """
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
"""

if "assign_alert_to_team" not in content:
    content = content.replace("class ThreatEngine:", "class ThreatEngine:\n" + assignment_fn)

assignment_call = """
            # Assign team
            await self.assign_alert_to_team(es, alert)
            
            await es.index(index=self.alerts_index, id=alert_id, body=alert)
"""
if "# Assign team" not in content:
    content = content.replace("await es.index(index=self.alerts_index, id=alert_id, body=alert)", assignment_call)

with open("backend/app/scoring/threat_engine.py", "w") as f:
    f.write(content)
