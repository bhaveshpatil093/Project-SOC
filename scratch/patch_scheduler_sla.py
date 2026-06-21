with open("backend/app/ingestion/scheduler.py", "r") as f:
    content = f.read()

import_stmt = """
    from app.monitoring.sla_tracker import sla_tracker_instance
    from app.api.routes.admin import ws_manager

    async def check_sla_breaches_job():
        try:
            approaching = await sla_tracker_instance.get_alerts_approaching_sla(es, warning_minutes=10)
            if approaching:
                await ws_manager.broadcast({
                    "type": "sla_warning",
                    "data": approaching
                })
        except Exception as e:
            logger.error(f"Error in check_sla_breaches_job: {e}")

    _scheduler.add_job(
        check_sla_breaches_job,
        trigger=IntervalTrigger(minutes=5),
        id="check_sla_breaches",
        replace_existing=True
    )
"""

if "check_sla_breaches_job" not in content:
    content = content.replace("scheduler_state[\"status\"] = \"running\"", import_stmt + "\n    scheduler_state[\"status\"] = \"running\"")

with open("backend/app/ingestion/scheduler.py", "w") as f:
    f.write(content)
