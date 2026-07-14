"""Add temporal baseline"""
from app.ingestion.es_client_protocol import supports_index_management
from app.logging_config import get_logger

logger = get_logger(__name__)

_BASELINES_INDEX = "soc-entity-baselines"


async def up(es) -> None:
    """v005 up: Adds active_hours and typical_days fields to the baselines index."""
    if not supports_index_management(es):
        logger.info("v005_up_skipped", reason="KibanaProxyClient does not support index management")
        return

    logger.info("v005_up_running", index=_BASELINES_INDEX)
    mapping = {
        "properties": {
            "active_hours": {"type": "integer"},
            "typical_days": {"type": "keyword"},
        }
    }
    await es.indices.put_mapping(index=_BASELINES_INDEX, body=mapping, ignore_unavailable=True)


async def down(es) -> None:
    """v005 down: Field additions cannot be rolled back in Elasticsearch."""
    logger.warning("v005_down_noop", reason="Field additions cannot be rolled back in Elasticsearch")
