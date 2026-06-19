from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.exceptions import SOCBaseException, AlertNotFoundError
import uuid
import datetime
from app.logging_config import get_logger

logger = get_logger(__name__)

async def soc_exception_handler(request: Request, exc: SOCBaseException):
    correlation_id = str(uuid.uuid4())
    logger.error("soc_exception", code=exc.code, message=exc.message, details=exc.details, correlation_id=correlation_id)
    
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, AlertNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code in ["INVALID_FEEDBACK", "RATE_LIMIT_EXCEEDED"]:
        status_code = status.HTTP_400_BAD_REQUEST if exc.code == "INVALID_FEEDBACK" else status.HTTP_429_TOO_MANY_REQUESTS
    elif exc.code in ["ES_CONNECTION_ERROR", "MODEL_NOT_LOADED", "SLM_NOT_READY"]:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
            "correlation_id": correlation_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    correlation_id = str(uuid.uuid4())
    logger.warning("validation_error", errors=exc.errors(), correlation_id=correlation_id)
    
    fields = {}
    for err in exc.errors():
        field_name = ".".join(str(loc) for loc in err["loc"]) if err["loc"] else "unknown"
        fields[field_name] = err["msg"]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Input validation failed",
            "fields": fields,
            "correlation_id": correlation_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    )

async def generic_exception_handler(request: Request, exc: Exception):
    correlation_id = str(uuid.uuid4())
    logger.error("unhandled_exception", error=str(exc), correlation_id=correlation_id, exc_info=exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "correlation_id": correlation_id,
            "support": "Contact ISTRAC SOC admin",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    )
