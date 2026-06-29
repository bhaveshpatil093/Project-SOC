import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api.middleware import AuditMiddleware
from app.middleware.logging_middleware import RequestLoggingMiddleware

from app.api.routes.alerts import router as alerts_router
from app.api.routes.cache import router as cache_router
from app.api.routes.features import router as features_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.health import router as health_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.slm import router as slm_router
from app.api.routes.training import router as training_router
from app.api.routes.hunting import router as hunting_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.reports import router as reports_router
from app.api.routes.websocket import router as websocket_router
from app.auth.routes import router as auth_router
from app.config import settings
from app.ingestion.kibana_client import KibanaProxyClient
from app.ingestion.scheduler import start_scheduler, stop_scheduler
from app.logging_config import configure_logging, get_logger
from app.middleware.rate_limiter import limiter
from app.middleware.validation_middleware import RequestSizeMiddleware
from app.models.model_manager import get_model_manager
from app.scoring.threat_engine import init_threat_engine
from app.slm.model_loader import _slm_engine

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure structured logging globally
    configure_logging(log_level=settings.LOG_LEVEL, json_output=not settings.DEBUG)

    # Validate environment configurations explicitly BEFORE booting engines natively
    from app.startup_validator import run_startup_validation
    await run_startup_validation(settings)

    # Initialize SQLite database
    from app.storage.local_db import init_db
    import os
    os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
    await init_db(settings.DB_PATH)

    # Initialize Kibana Proxy connection
    KibanaProxyClient()
    
    # Initialize Webhook Manager
    from app.integrations.webhook_manager import webhook_manager
    try:
        es = KibanaProxyClient()
        await webhook_manager.initialize(es)
    except Exception as e:
        logger.warning(f"Failed to initialize webhook manager: {e}")

    # Initialize Report Scheduler
    from app.reports.report_scheduler import report_scheduler
    try:
        es = KibanaProxyClient()
        await report_scheduler.initialize(es)
    except Exception as e:
        logger.warning(f"Failed to initialize report scheduler: {e}")

    # Initialize Team Manager mappings
    from app.auth.team_manager import team_manager_instance
    try:
        es = KibanaProxyClient()
        await team_manager_instance.initialize(es)
    except Exception as e:
        logger.warning(f"Failed to initialize team manager: {e}")

    # Initialize Log Viewer mappings
    from app.monitoring.log_viewer import log_viewer_instance
    try:
        es = KibanaProxyClient()
        await log_viewer_instance.initialize(es)
    except Exception as e:
        logger.warning(f"Failed to initialize log viewer index: {e}")


    # Initialize ML Model orchestrator dynamically onto lifespan wrapper
    asyncio.create_task(get_model_manager().initialize())

    # Initialize Central Threat Engine
    await init_threat_engine()

    # Load SLM Chat Engine asynchronously without blocking event loops
    try:
        asyncio.create_task(_slm_engine.load())
    except Exception as e:
        logger.warning("slm_engine_load_failed", error=str(e))

    # Load and bind the standalone RAG Pipeline mapping memory vectors locally
    try:
        from app.slm.rag_pipeline import _rag_pipeline
        asyncio.create_task(_rag_pipeline.initialize())
    except Exception as e:
        logger.warning("rag_initialization_failed", error=str(e))

    # Evaluate ML Artifact Bounds initializing auto-training pipelines natively cleanly
    if_path = os.path.join(settings.MODEL_DIR, "isolation_forest.pkl")
    ae_path = os.path.join(settings.MODEL_DIR, "autoencoder.pt")

    if not os.path.exists(if_path) or not os.path.exists(ae_path):
        try:
            from app.models.trainer import run_initial_training
            kibana_client = KibanaProxyClient()
            mm = get_model_manager()
            asyncio.create_task(run_initial_training(kibana_client, mm, settings.DB_PATH))
        except Exception as es_e:
            logger.warning("kibana_connection_for_trainer_failed", error=str(es_e))

    # Startup: Initialize ES connection and verify indices
    client = KibanaProxyClient()
    is_connected = await client.check_connection()
    if is_connected:
        es = client
        
        # Apply pending Elasticsearch migrations
        from app.migrations.migration_runner import MigrationRunner
        runner = MigrationRunner()
        migration_results = await runner.apply_pending(es)
        if migration_results.get("applied"):
            logger.info("migrations_applied", versions=migration_results["applied"])
        if migration_results.get("errors"):
            logger.error("migration_errors", errors=migration_results["errors"])

        await start_scheduler(es)

    # API Documentation generation
    try:
        import json
        os.makedirs("docs", exist_ok=True)
        with open("docs/openapi.json", "w") as f:
            json.dump(app.openapi(), f, indent=2)
        logger.info("openapi_schema_generated", path="docs/openapi.json")
    except Exception as e:
        logger.warning("openapi_generation_failed", error=str(e))

    yield
    # Shutdown: Clean up client
    await stop_scheduler()
    await KibanaProxyClient().close()
    scheduler.shutdown()

from fastapi.exceptions import RequestValidationError

from app.exceptions import SOCBaseException
from app.middleware.exception_handlers import (
    generic_exception_handler,
    soc_exception_handler,
    validation_exception_handler,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="ISRO ISTRAC SOC AI Platform",
        description="""
        AI-Driven Security Analytics Platform for ISRO ISTRAC Bengaluru.

        ## Architecture
        This platform ingests security logs from Elasticsearch, detects anomalies
        using ML models (Isolation Forest, Autoencoder, LSTM), scores threats,
        and provides natural language investigation via an SLM assistant.

        ## Authentication
        All endpoints require Bearer token authentication (see /api/auth/login).

        ## Rate Limits
        - /api/slm/chat: 60 requests/minute
        - /api/alerts: 300 requests/minute
        """,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    app.add_middleware(AuditMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RequestLoggingMiddleware)

    from prometheus_client import make_asgi_app
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    from app.api.routes.health import router as health_router
    from app.api.routes.diagnostics import router as diagnostics_router
    from app.api.routes.admin import router as admin_router
    from app.api.routes.admin_audit_log import router as admin_audit_log_router

    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(ingestion_router, prefix="/api/ingestion", tags=["Ingestion"])
    app.include_router(features_router, prefix="/api/features", tags=["Features"])
    app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])
    app.include_router(feedback_router, prefix="/api/feedback", tags=["Feedback"])
    app.include_router(training_router, prefix="/api/training", tags=["Training"])
    app.include_router(hunting_router, prefix="/api/hunting", tags=["Hunting"])
    app.include_router(webhooks_router, prefix="/api/webhooks", tags=["Webhooks"])
    app.include_router(reports_router, prefix="/api/reports", tags=["Reports"])
    app.include_router(slm_router, prefix="/api/slm", tags=["SLM"])
    app.include_router(incidents_router, prefix="/api/incidents", tags=["Incidents"])
    app.include_router(cache_router, prefix="/api/cache", tags=["Cache"])
    app.include_router(diagnostics_router, prefix="/api/diagnostics", tags=["Diagnostics"])
    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_exception_handler(SOCBaseException, soc_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.add_middleware(RequestSizeMiddleware, max_upload_size=1048576) # 1MB limit
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.isro.gov.in"]
    )
    app.include_router(websocket_router, tags=["WebSocket"])

    return app

app = create_app()
