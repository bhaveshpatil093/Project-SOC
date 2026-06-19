from typing import Dict, Any, Optional

class SOCBaseException(Exception):
    def __init__(self, message: str, code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

class ESConnectionError(SOCBaseException):
    def __init__(self, message: str = "Failed to connect to Elasticsearch", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "ES_CONNECTION_ERROR", details)

class ModelNotLoadedError(SOCBaseException):
    def __init__(self, message: str = "Required ML model is not loaded", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "MODEL_NOT_LOADED", details)

class SLMNotReadyError(SOCBaseException):
    def __init__(self, message: str = "SLM engine is not ready", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "SLM_NOT_READY", details)

class AlertNotFoundError(SOCBaseException):
    def __init__(self, alert_id: str):
        super().__init__(f"Alert {alert_id} not found", "ALERT_NOT_FOUND", {"alert_id": alert_id})

class InvalidFeedbackError(SOCBaseException):
    def __init__(self, message: str = "Invalid feedback provided", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "INVALID_FEEDBACK", details)

class RateLimitError(SOCBaseException):
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RATE_LIMIT_EXCEEDED", details)

class InferenceTooSlowError(SOCBaseException):
    def __init__(self, message: str = "Inference took too long", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "INFERENCE_TOO_SLOW", details)
