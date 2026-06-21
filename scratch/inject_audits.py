import os

def insert_audit(filepath, func_name, action_str, resource_type, resource_id="None", details="{}"):
    with open(filepath, "r") as f:
        lines = f.readlines()
    
    # ensure import
    import_stmt = "from app.monitoring.audit_logger import audit_action\n"
    if import_stmt not in lines:
        for i, line in enumerate(lines):
            if line.startswith("from fastapi "):
                lines.insert(i, import_stmt)
                break
    
    in_func = False
    brace_level = 0
    for i, line in enumerate(lines):
        if line.startswith("async def " + func_name + "(") or line.startswith("def " + func_name + "("):
            in_func = True
        
        if in_func:
            if "return " in line:
                indent = len(line) - len(line.lstrip())
                spaces = " " * indent
                audit_call = f"{spaces}await audit_action('{action_str}', '{resource_type}', {resource_id}, {details})\n"
                lines.insert(i, audit_call)
                break
    
    with open(filepath, "w") as f:
        f.writelines(lines)

insert_audit("backend/app/api/routes/alerts.py", "update_status", "alert.status_change", "alert", "alert_id", "{'new_status': update.status}")
insert_audit("backend/app/api/routes/feedback.py", "submit_feedback", "feedback.submit", "feedback", "feedback.alert_id")
insert_audit("backend/app/api/routes/slm.py", "explain_alert", "slm.explain_alert", "alert", "alert_id")
insert_audit("backend/app/api/routes/incidents.py", "escalate_incident", "incident.escalate", "incident", "incident_id")
insert_audit("backend/app/api/routes/admin.py", "create_snapshot", "admin.backup_create", "system")
insert_audit("backend/app/api/routes/admin.py", "restore_snapshot", "admin.backup_restore", "system", "snapshot_name")
insert_audit("backend/app/api/routes/training.py", "start_training", "training.start", "model")
insert_audit("backend/app/api/routes/entities.py", "add_watchlist", "entity.watchlist_add", "entity", "body.entity_key", "{'reason': body.reason}")
insert_audit("backend/app/api/routes/entities.py", "remove_watchlist", "entity.watchlist_remove", "entity", "entity_key")

insert_audit("backend/app/auth/routes.py", "login_for_access_token", "auth.login", "system")
