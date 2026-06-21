import os
import glob

# 1. Update main.py
main_file = "backend/app/main.py"
with open(main_file, "r") as f:
    main_code = f.read()

if "admin_audit_log_router" not in main_code:
    main_code = main_code.replace(
        'from app.api.routes.admin import router as admin_router',
        'from app.api.routes.admin import router as admin_router\n    from app.api.routes.admin_audit_log import router as admin_audit_log_router'
    )
    main_code = main_code.replace(
        'app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])',
        'app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])\n    app.include_router(admin_audit_log_router)'
    )
    with open(main_file, "w") as f:
        f.write(main_code)

print("Updated main.py")
