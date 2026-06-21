import os

with open("backend/app/api/routes/admin.py", "r") as f:
    content = f.read()

import_stmt = """from app.auth.team_manager import team_manager_instance, Team
"""

if "from app.auth.team_manager" not in content:
    content = content.replace("from app.monitoring.log_viewer", import_stmt + "from app.monitoring.log_viewer")

routes = """
@router.get("/teams", dependencies=[Depends(require_role("admin"))])
async def list_teams():
    try:
        es = await get_es_client()
        teams = await team_manager_instance.list_teams(es)
        return {"teams": teams}
    except Exception as e:
        logger.error(f"Error listing teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to list teams")

@router.post("/teams", dependencies=[Depends(require_role("admin"))])
async def create_team(team: Team):
    try:
        es = await get_es_client()
        created = await team_manager_instance.create_team(es, team)
        return {"team": created}
    except Exception as e:
        logger.error(f"Error creating team: {e}")
        raise HTTPException(status_code=500, detail="Failed to create team")

@router.put("/teams/{team_id}", dependencies=[Depends(require_role("admin"))])
async def update_team(team_id: str, updates: dict):
    try:
        es = await get_es_client()
        updated = await team_manager_instance.update_team(es, team_id, updates)
        return {"team": updated}
    except Exception as e:
        logger.error(f"Error updating team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update team")

@router.post("/teams/{team_id}/members", dependencies=[Depends(require_role("admin"))])
async def add_team_member(team_id: str, payload: dict):
    try:
        es = await get_es_client()
        username = payload.get("username")
        if not username:
            raise HTTPException(status_code=400, detail="Username required")
        await team_manager_instance.add_member(es, team_id, username)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error adding member: {e}")
        raise HTTPException(status_code=500, detail="Failed to add member")

@router.get("/teams/{team_id}/stats", dependencies=[Depends(require_role("admin"))])
async def get_team_stats(team_id: str, since_days: int = Query(7, ge=1)):
    try:
        es = await get_es_client()
        stats = await team_manager_instance.get_team_stats(es, team_id, since_days)
        return {"stats": stats}
    except Exception as e:
        logger.error(f"Error fetching team stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch team stats")
"""

content += "\n" + routes

with open("backend/app/api/routes/admin.py", "w") as f:
    f.write(content)
