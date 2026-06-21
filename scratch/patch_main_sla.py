with open("backend/app/main.py", "r") as f:
    content = f.read()

import_stmt = "from app.api.routes import sla\n"
if "import sla" not in content:
    content = content.replace("from app.api.routes import admin", import_stmt + "from app.api.routes import admin")

router_stmt = "app.include_router(sla.router, prefix=\"/api/sla\", tags=[\"SLA\"])\n"
if "prefix=\"/api/sla\"" not in content:
    # insert before error handlers or after other routers
    if "app.include_router(admin.router" in content:
        content = content.replace("app.include_router(admin.router", router_stmt + "app.include_router(admin.router")

with open("backend/app/main.py", "w") as f:
    f.write(content)
