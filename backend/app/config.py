
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Elasticsearch
    ES_HOST: str = "localhost"
    ES_PORT: int = 9200
    ES_USERNAME: str = "elastic"
    ES_PASSWORD: str = ""
    ES_VERIFY_CERTS: bool = False
    ES_TIMEOUT: int = 30
    ES_MAX_RETRIES: int = 3

    # App
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    JWT_SECRET_KEY: str = "1234567890-super-secret-isro-istrac-dev-key"

    # Pipeline
    WINDOW_MINUTES: int = 5
    THREAT_SCORE_THRESHOLD: float = 0.3
    INGESTION_INTERVAL_MINUTES: int = 5
    MAX_LOGS_PER_FETCH: int = 1000

    # Models
    MODEL_DIR: str = "backend/models/saved"
    RETRAIN_DAY: str = "sun"
    RETRAIN_HOUR: int = 2

    # SLM
    SLM_MODEL_NAME: str = "auto"
    SLM_MAX_NEW_TOKENS: int = 512
    SLM_TEMPERATURE: float = 0.3
    SLM_LOAD_IN_4BIT: bool = False
    SLM_CACHE_TTL_SECONDS: int = 3600
    SLM_CACHE_SEMANTIC_THRESHOLD: float = 0.92

    # RAG
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    RAG_N_RESULTS: int = 5
    RAG_AUTO_REINDEX_THRESHOLD: int = 10

    # Conversation
    MAX_CONVERSATIONS: int = 100
    CONVERSATION_TTL_HOURS: int = 24

    # MLflow
    MLFLOW_TRACKING_URI: str = "sqlite:///./data/mlflow.db"
    MLFLOW_EXPERIMENT_NAME: str = "soc-anomaly-detection"

    model_config = SettingsConfigDict(extra="ignore")

import os

ENVIRONMENT = os.getenv("SOC_ENVIRONMENT", "development")

def load_settings() -> Settings:
    env_file = f".env.{ENVIRONMENT}"
    if not os.path.exists(env_file):
        env_file = ".env"
    return Settings(_env_file=env_file)

settings = load_settings()
