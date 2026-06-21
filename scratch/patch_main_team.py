import os

with open("backend/app/main.py", "r") as f:
    content = f.read()

init_stmt = """    # Initialize Team Manager mappings
    from app.auth.team_manager import team_manager_instance
    try:
        es = await get_es_client()
        await team_manager_instance.initialize(es)
    except Exception as e:
        logger.warning(f"Failed to initialize team manager: {e}")
"""

if "team_manager_instance.initialize" not in content:
    content = content.replace("    # Initialize Log Viewer mappings", init_stmt + "\n    # Initialize Log Viewer mappings")

with open("backend/app/main.py", "w") as f:
    f.write(content)
