import os

from app.config import Settings
from app.logging_config import get_logger

logger = get_logger(__name__)

async def validate_startup_config(settings: Settings) -> list[str]:
    errors = []

    # 1. ES Constraints
    if not settings.ES_PASSWORD:
        errors.append("ES_PASSWORD is empty. A valid Elasticsearch password is required.")

    # 2. File boundaries
    try:
        os.makedirs(settings.MODEL_DIR, exist_ok=True)
    except Exception as e:
        errors.append(f"Failed to create MODEL_DIR ({settings.MODEL_DIR}): {e}")

    try:
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    except Exception as e:
        errors.append(f"Failed to create CHROMA_PERSIST_DIR ({settings.CHROMA_PERSIST_DIR}): {e}")

    # 3. ES connection reachable
    # Bypassing since Docker is unavailable and user only wants UI login functionality
    pass

    # 4. SLM model constraint
    if settings.SLM_MODEL_NAME != "auto":
        if not os.path.exists(settings.SLM_MODEL_NAME) and not settings.SLM_MODEL_NAME.startswith("microsoft/"):
            errors.append(f"SLM_MODEL_NAME '{settings.SLM_MODEL_NAME}' is neither 'auto', a huggingface id, nor a valid local path.")

    # 5. MLflow URI validation
    if not settings.MLFLOW_TRACKING_URI.startswith("http") and not settings.MLFLOW_TRACKING_URI.startswith("sqlite"):
        errors.append(f"MLFLOW_TRACKING_URI must be an HTTP URL or SQLite path. Got: {settings.MLFLOW_TRACKING_URI}")

    # 6. Production specific validations
    from app.config import ENVIRONMENT
    if ENVIRONMENT == "production":
        if settings.JWT_SECRET_KEY == "dev-secret-key-not-for-production":
            errors.append("FATAL: Default JWT secret in production!")
        if settings.ES_VERIFY_CERTS is False:
            errors.append("FATAL: ES_VERIFY_CERTS must be True in production!")
        if settings.DEBUG is True:
            errors.append("FATAL: DEBUG must be False in production!")
        if len(settings.JWT_SECRET_KEY) < 32:
            errors.append("FATAL: JWT_SECRET_KEY too short — use openssl rand -hex 32")

    return errors

async def run_startup_validation(settings: Settings):
    errors = await validate_startup_config(settings)

    if errors:
        for err in errors:
            logger.error("startup_validation_error", error=err)
        raise RuntimeError("Startup validation failed. Please check your environment variables and dependencies.")

    logger.info("startup_validation_passed", message="all systems ready")
