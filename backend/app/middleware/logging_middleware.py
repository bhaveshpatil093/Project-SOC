import time
import traceback
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import CORRELATION_ID_CTX, get_logger

logger = get_logger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        corr_id = request.headers.get("X-Correlation-ID")
        if not corr_id:
            corr_id = str(uuid.uuid4())

        token = CORRELATION_ID_CTX.set(corr_id)

        start_time = time.time()

        logger.info("request_started",
                    method=request.method,
                    path=request.url.path,
                    client_ip=request.client.host if request.client else "unknown",
                    user_agent=request.headers.get("user-agent", "unknown"))

        try:
            response = await call_next(request)
            process_time_ms = (time.time() - start_time) * 1000.0

            response.headers["X-Correlation-ID"] = corr_id

            logger.info("request_completed",
                        method=request.method,
                        path=request.url.path,
                        status_code=response.status_code,
                        response_time_ms=process_time_ms)
            return response

        except Exception as e:
            process_time_ms = (time.time() - start_time) * 1000.0
            logger.error("request_failed",
                         method=request.method,
                         path=request.url.path,
                         error=str(e),
                         traceback=traceback.format_exc(),
                         response_time_ms=process_time_ms)
            raise
        finally:
            CORRELATION_ID_CTX.reset(token)
