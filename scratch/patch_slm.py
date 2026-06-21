import re

with open("backend/app/api/routes/slm.py", "r") as f:
    content = f.read()

import_stmt = "from app.monitoring.slm_analytics import slm_analytics_instance, ResponseMetrics\n"
if "slm_analytics_instance" not in content:
    content = content.replace("from app.auth.jwt import require_role", import_stmt + "from app.auth.jwt import require_role")

analytics_endpoint = """
@router.get("/analytics", dependencies=[Depends(require_role("admin", "analyst"))])
async def get_slm_analytics(since_days: int = 30):
    es = await get_es_client()
    trends = await slm_analytics_instance.get_usage_trends(es, since_days)
    top_questions = await slm_analytics_instance.get_top_questions(es, since_days)
    knowledge_gaps = await slm_analytics_instance.get_knowledge_gaps(es)
    investigated = await slm_analytics_instance.get_most_investigated_entities(es, since_days)
    return {
        "trends": trends,
        "top_questions": top_questions,
        "knowledge_gaps": knowledge_gaps,
        "most_investigated": investigated
    }
"""

if "@router.get(\"/analytics\"" not in content:
    content += "\n" + analytics_endpoint

with open("backend/app/api/routes/slm.py", "w") as f:
    f.write(content)
