from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
import asyncio
from app.config import settings
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize ES connection
    await get_es_client()
    
    # Initialize ML Model orchestrator dynamically onto lifespan wrapper
    await get_model_manager().initialize()
    
    # Initialize Central Threat Engine
    await init_threat_engine()

    # Evaluate ML Artifact Bounds initializing auto-training pipelines natively cleanly
    if_path = os.path.join(settings.MODEL_DIR, "isolation_forest.pkl")
    ae_path = os.path.join(settings.MODEL_DIR, "autoencoder.pt")
    
    if not os.path.exists(if_path) or not os.path.exists(ae_path):
        from app.models.trainer import run_initial_training
        es = await get_es_client()
        mm = get_model_manager()
        asyncio.create_task(run_initial_training(es, mm))

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

def create_app() -> FastAPI:
    app = FastAPI(
        title="ISRO SOC Security Analytics Platform",
        description="Backend API for Security Operations Center",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ingestion_router, prefix="/api/ingestion", tags=["Ingestion"])
    app.include_router(features_router, prefix="/api/features", tags=["Features"])
    app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])
    app.include_router(feedback_router, prefix="/api/feedback", tags=["Feedback"])
    app.include_router(training_router, prefix="/api/training", tags=["Training"])

    @app.get("/health")
    def health_check():
        return {"status": "ok", "version": "1.0.0"}

    return app

app = create_app()
