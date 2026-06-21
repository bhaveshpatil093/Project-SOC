with open("backend/app/api/routes/slm.py", "r") as f:
    lines = f.readlines()

in_explain = False
for i, line in enumerate(lines):
    if line.startswith("async def explain_alert("):
        in_explain = True
    
    if in_explain and "return {" in line:
        indent = len(line) - len(line.lstrip())
        spaces = " " * indent
        track_call = f"""{spaces}es = await get_es_client()
{spaces}metrics = ResponseMetrics(
{spaces}    generation_time_ms=int(resp_time),
{spaces}    prompt_tokens=res.get("prompt_tokens", 0),
{spaces}    completion_tokens=res.get("completion_tokens", 0),
{spaces}    quality_score=res.get("quality_score", 1.0)
{spaces})
{spaces}await slm_analytics_instance.track_query(es, "explain_"+alert_id, "Explain this alert", "explanation", alert_id, metrics)
"""
        lines.insert(i, track_call)
        break

with open("backend/app/api/routes/slm.py", "w") as f:
    f.writelines(lines)
