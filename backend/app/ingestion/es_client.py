import logging
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ConnectionError
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# Singleton instance
_es_client: AsyncElasticsearch | None = None

INDEX_NAMES = {
    "syslog":           "logs-system.syslog-*",
    "process":          "logs-endpoint.events.process-*",
    "security":         "logs-windows.powershell_operational-*",
    "alerts_processed": "soc-processed-alerts",
    "features":         "soc-feature-vectors",
    "feedback":         "soc-analyst-feedback",
    "incidents":        "soc-incidents",
    "baselines":        "soc-entity-baselines"
}

async def get_es_client() -> AsyncElasticsearch:
    """Returns the Elasticsearch singleton client, initializing it on first call."""
    global _es_client
    if _es_client is None:
        scheme = "https" if settings.ES_VERIFY_CERTS else "http"
        _es_client = AsyncElasticsearch(
            hosts=[{"host": settings.ES_HOST, "port": settings.ES_PORT, "scheme": scheme}],
            basic_auth=(settings.ES_USERNAME, settings.ES_PASSWORD),
            verify_certs=settings.ES_VERIFY_CERTS,
            connections_per_node=10,        # Connection pool size
            http_compress=True,             # Gzip compression
            retry_on_timeout=True,
            max_retries=3,
            sniff_on_start=False
        )
    return _es_client

async def check_connection() -> bool:
    """Pings the Elasticsearch cluster and logs the result."""
    try:
        es = await get_es_client()
        is_connected = await es.ping()
        if is_connected:
            logger.info("es_connection_success", host=settings.ES_HOST, port=settings.ES_PORT)
        else:
            logger.error("es_connection_failed", host=settings.ES_HOST, port=settings.ES_PORT)
        return is_connected
    except ConnectionError as e:
        logger.error("es_connection_error", error=str(e), type="ConnectionError")
        return False
    except Exception as e:
        logger.error("es_connection_error_unexpected", error=str(e))
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
                        "threat_intel": {"type": "object"},
                        "alert_status": {"type": "keyword", "null_value": "open"},
                        "created_at": {"type": "date"}
                    }
                }
            }
        )
        logger.info("es_index_created", index=alerts_index)

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
        logger.info("es_index_created", index=features_index)

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
        logger.info("es_index_created", index=feedback_index)

    # 4. soc-incidents
    incidents_index = INDEX_NAMES["incidents"]
    if not await es.indices.exists(index=incidents_index):
        await es.indices.create(
            index=incidents_index,
            body={
                "mappings": {
                    "properties": {
                        "incident_id": {"type": "keyword"},
                        "entity_key": {"type": "keyword"},
                        "host_id": {"type": "keyword"},
                        "user_name": {"type": "keyword"},
                        "started_at": {"type": "date"},
                        "last_seen": {"type": "date"},
                        "duration_seconds": {"type": "float"},
                        "alert_ids": {"type": "keyword"},
                        "alert_count": {"type": "integer"},
                        "log_types_involved": {"type": "keyword"},
                        "max_threat_score": {"type": "float"},
                        "mean_threat_score": {"type": "float"},
                        "incident_threat_score": {"type": "float"},
                        "threat_level": {"type": "keyword"},
                        "mitre_tactics": {"type": "keyword"},
                        "mitre_techniques": {"type": "keyword"},
                        "attack_stage": {"type": "keyword"},
                        "is_multi_stage": {"type": "boolean"},
                        "status": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "matched_patterns": {"type": "object"}
                    }
                }
            }
        )
        logger.info("es_index_created", index=incidents_index)

    # 5. soc-entity-baselines
    baselines_index = INDEX_NAMES["baselines"]
    if not await es.indices.exists(index=baselines_index):
        await es.indices.create(
            index=baselines_index,
            body={
                "mappings": {
                    "properties": {
                        "entity_key": {"type": "keyword"},
                        "last_updated": {"type": "date"},
                        "observation_count": {"type": "integer"},
                        "avg_conn_per_minute": {"type": "float"},
                        "std_conn_per_minute": {"type": "float"},
                        "avg_unique_dst_ports": {"type": "float"},
                        "std_unique_dst_ports": {"type": "float"},
                        "typical_protocols": {"type": "keyword"},
                        "typical_dst_ports": {"type": "integer"},
                        "avg_process_spawn_count": {"type": "float"},
                        "std_process_spawn_count": {"type": "float"},
                        "known_process_names": {"type": "keyword"},
                        "avg_args_count": {"type": "float"},
                        "avg_alert_count": {"type": "float"},
                        "std_alert_count": {"type": "float"},
                        "avg_risk_score": {"type": "float"}
                    }
                }
            }
        )
        logger.info("es_index_created", index=baselines_index)

async def close_es_client():
    """Closes the Elasticsearch singleton client."""
    global _es_client
    if _es_client is not None:
        await _es_client.close()
        _es_client = None
        logger.info("es_client_closed")
