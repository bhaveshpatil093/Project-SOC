"""Add score history"""
from app.ingestion.es_client_protocol import supports_index_management
from app.logging_config import get_logger

logger = get_logger(__name__)

_ALERTS_INDEX = "soc-processed-alerts"


async def up(es) -> None:
    """v004 up: Adds score_history nested field to the alerts index."""
    if not supports_index_management(es):
        logger.info("v004_up_skipped", reason="KibanaProxyClient does not support index management")
        return

    logger.info("v004_up_running", index=_ALERTS_INDEX)
    mapping = {
        "properties": {
            "score_history": {
                "type": "nested",
                "properties": {
                    "timestamp": {"type": "date"},
                    "threat_score": {"type": "float"},
                },
            }
        }
    }
    await es.indices.put_mapping(index=_ALERTS_INDEX, body=mapping, ignore_unavailable=True)


async def down(es) -> None:
    """v004 down: Field additions cannot be rolled back in Elasticsearch."""
    logger.warning("v004_down_noop", reason="Field additions cannot be rolled back in Elasticsearch")
