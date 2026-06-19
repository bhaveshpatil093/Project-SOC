from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncio
import os

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.middleware.rate_limiter import limiter
from app.middleware.validation_middleware import RequestSizeMiddleware
from app.config import settings
from app.ingestion.es_client import (
    get_es_client,
    check_connection,
    create_soc_indices,
    close_es_client
)
from app.ingestion.scheduler import start_scheduler, stop_scheduler
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.features import router as features_router
from app.models.model_manager import get_model_manager
from app.scoring.threat_engine import init_threat_engine
from app.api.routes.alerts import router as alerts_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.training import router as training_router
from app.api.routes.websocket import router as websocket_router
from app.api.routes.slm import router as slm_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.health import router as health_router
from app.auth.routes import router as auth_router
from app.slm.model_loader import _slm_engine
from app.logging_config import configure_logging, get_logger
import asyncio
from app.config import settings
import os

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure structured logging globally
    configure_logging(log_level=settings.LOG_LEVEL, json_output=not settings.DEBUG)
    
    # Validate environment configurations explicitly BEFORE booting engines natively
    from app.startup_validator import run_startup_validation
    await run_startup_validation(settings)

    # Initialize ES connection
    await get_es_client()
    
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
        
        try:
            es = await get_es_client()
            stats = await _rag_pipeline.get_index_stats()
            n_docs = stats.get("total_indexed", 0)
            
            if n_docs < 10:
                logger.info("rag_auto_reindex_triggered", docs_found=n_docs)
                asyncio.create_task(_rag_pipeline.reindex_from_elasticsearch(es))
        except Exception as es_e:
            logger.warning("es_connection_for_rag_failed", error=str(es_e))
    except Exception as e:
        logger.warning("rag_initialization_failed", error=str(e))

    # Evaluate ML Artifact Bounds initializing auto-training pipelines natively cleanly
    if_path = os.path.join(settings.MODEL_DIR, "isolation_forest.pkl")
    ae_path = os.path.join(settings.MODEL_DIR, "autoencoder.pt")
    
    if not os.path.exists(if_path) or not os.path.exists(ae_path):
        try:
            from app.models.trainer import run_initial_training
            es = await get_es_client()
            mm = get_model_manager()
            asyncio.create_task(run_initial_training(es, mm))
        except Exception as es_e:
            logger.warning("es_connection_for_trainer_failed", error=str(es_e))

    # Startup: Initialize ES connection and verify indices
    is_connected = await check_connection()
    if is_connected:
        es = await get_es_client()
        await create_soc_indices(es)
        await start_scheduler(es)
    yield
    # Shutdown: Clean up client
    await stop_scheduler()
    await close_es_client()

from app.exceptions import SOCBaseException
from app.middleware.exception_handlers import (
    soc_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from fastapi.exceptions import RequestValidationError

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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    from app.middleware import RequestLoggingMiddleware
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(ingestion_router, prefix="/api/ingestion", tags=["Ingestion"])
    app.include_router(features_router, prefix="/api/features", tags=["Features"])
    app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])
    app.include_router(feedback_router, prefix="/api/feedback", tags=["Feedback"])
    app.include_router(training_router, prefix="/api/training", tags=["Training"])
    app.include_router(slm_router, prefix="/api/slm", tags=["SLM"])
    app.include_router(incidents_router, prefix="/api/incidents", tags=["Incidents"])
    app.include_router(health_router, prefix="/health", tags=["Health"])

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
