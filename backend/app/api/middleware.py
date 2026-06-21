import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.monitoring.audit_logger import (
    audit_context_user,
    audit_context_role,
    audit_context_ip,
    audit_context_ua,
    audit_context_corr
)

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Set correlation ID
        corr_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        audit_context_corr.set(corr_id)
        
        # Set IP
        ip = request.client.host if request.client else "127.0.0.1"
        if request.headers.get("X-Forwarded-For"):
            ip = request.headers.get("X-Forwarded-For").split(",")[0].strip()
        audit_context_ip.set(ip)
        
        # Set User Agent
        ua = request.headers.get("user-agent", "unknown")
        audit_context_ua.set(ua)

        # Set User info (will be overwritten if authenticated)
        audit_context_user.set("anonymous")
        audit_context_role.set("none")

        response = await call_next(request)
        return response
