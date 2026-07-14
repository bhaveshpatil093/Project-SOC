"""Add incident fields"""
from app.ingestion.es_client_protocol import supports_index_management
from app.logging_config import get_logger

logger = get_logger(__name__)

_ALERTS_INDEX = "soc-processed-alerts"


async def up(es) -> None:
    """v002 up: Adds occurrence_count, last_seen, fingerprint fields to the alerts index."""
    if not supports_index_management(es):
        logger.info("v002_up_skipped", reason="KibanaProxyClient does not support index management")
        return

    logger.info("v002_up_running", index=_ALERTS_INDEX)
    mapping = {
        "properties": {
            "occurrence_count": {"type": "integer", "null_value": 1},
            "last_seen": {"type": "date"},
            "fingerprint": {"type": "keyword"},
        }
    }
    await es.indices.put_mapping(index=_ALERTS_INDEX, body=mapping, ignore_unavailable=True)


async def down(es) -> None:
    """v002 down: Field additions cannot be rolled back in Elasticsearch."""
    logger.warning("v002_down_noop", reason="Field additions cannot be rolled back in Elasticsearch")
