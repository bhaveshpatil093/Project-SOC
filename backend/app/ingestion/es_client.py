import logging
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ConnectionError
from app.config import settings

logger = logging.getLogger(__name__)

# Singleton instance
_es_client: AsyncElasticsearch | None = None

INDEX_NAMES = {
    "syslog":           "logs-system.syslog-*",
    "process":          "logs-endpoint.events.process-*",
    "security":         "logs-windows.powershell_operational-*",
    "alerts_processed": "soc-processed-alerts",
    "features":         "soc-feature-vectors",
    "feedback":         "soc-analyst-feedback"
}

async def get_es_client() -> AsyncElasticsearch:
    """Returns the Elasticsearch singleton client, initializing it on first call."""
    global _es_client
    if _es_client is None:
        scheme = "https" if settings.ES_VERIFY_CERTS else "http"
        # Since docker-compose sets xpack.security.http.ssl.enabled=false, we use HTTP
        _es_client = AsyncElasticsearch(
            [f"http://{settings.ES_HOST}:{settings.ES_PORT}"],
            basic_auth=(settings.ES_USERNAME, settings.ES_PASSWORD),
            verify_certs=settings.ES_VERIFY_CERTS,
        )
    return _es_client

async def check_connection() -> bool:
    """Pings the Elasticsearch cluster and logs the result."""
    try:
        es = await get_es_client()
        is_connected = await es.ping()
        if is_connected:
            logger.info("Successfully connected to Elasticsearch.")
        else:
            logger.error("Failed to connect to Elasticsearch. Ping returned False.")
        return is_connected
    except ConnectionError as e:
        logger.error(f"Elasticsearch connection error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error connecting to Elasticsearch: {e}")
        return False

async def create_soc_indices(es: AsyncElasticsearch):
    """Creates the necessary custom indices for the SOC platform with their mappings."""
    
    # 1. soc-processed-alerts
    alerts_index = INDEX_NAMES["alerts_processed"]
    if not await es.indices.exists(index=alerts_index):
        await es.indices.create(
            index=alerts_index,
            body={
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "host_id": {"type": "keyword"},
                        "user_name": {"type": "keyword"},
                        "log_type": {"type": "keyword"},
                        "threat_score": {"type": "float"},
                        "anomaly_scores": {"type": "object"},
                        "shap_features": {"type": "object"},
                        "mitre_tactic": {"type": "keyword"},
                        "mitre_technique": {"type": "keyword"},
                        "alert_status": {"type": "keyword", "null_value": "open"},
                        "created_at": {"type": "date"}
                    }
                }
            }
        )
        logger.info(f"Created index {alerts_index}")

    # 2. soc-feature-vectors
    features_index = INDEX_NAMES["features"]
    if not await es.indices.exists(index=features_index):
        await es.indices.create(
            index=features_index,
            body={
                "mappings": {
                    "properties": {
                        "entity_id": {"type": "keyword"},
                        "entity_type": {"type": "keyword"},
                        "feature_vector": {
                            "type": "dense_vector",
                            "dims": 50
                        },
                        "window_bucket": {"type": "date"}
                    }
                }
            }
        )
        logger.info(f"Created index {features_index}")

    # 3. soc-analyst-feedback
    feedback_index = INDEX_NAMES["feedback"]
    if not await es.indices.exists(index=feedback_index):
        await es.indices.create(
            index=feedback_index,
            body={
                "mappings": {
                    "properties": {
                        "alert_id": {"type": "keyword"},
                        "analyst_name": {"type": "keyword"},
                        "label": {"type": "keyword"},  # TP/FP/Benign
                        "notes": {"type": "text"},
                        "created_at": {"type": "date"}
                    }
                }
            }
        )
        logger.info(f"Created index {feedback_index}")

async def close_es_client():
    """Closes the Elasticsearch singleton client."""
    global _es_client
    if _es_client is not None:
        await _es_client.close()
        _es_client = None
        logger.info("Closed Elasticsearch client connection.")
