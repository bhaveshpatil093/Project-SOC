"""Add entity risk profile"""
from app.ingestion.es_client_protocol import supports_index_management
from app.logging_config import get_logger

logger = get_logger(__name__)

_BASELINES_INDEX = "soc-entity-baselines"


async def up(es) -> None:
    """v003 up: Adds risk_profile_vector dense_vector field to the baselines index."""
    if not supports_index_management(es):
        logger.info("v003_up_skipped", reason="KibanaProxyClient does not support index management")
        return

    logger.info("v003_up_running", index=_BASELINES_INDEX)
    mapping = {
        "properties": {
            "risk_profile_vector": {"type": "dense_vector", "dims": 20},
        }
    }
    await es.indices.put_mapping(index=_BASELINES_INDEX, body=mapping, ignore_unavailable=True)


async def down(es) -> None:
    """v003 down: Field additions cannot be rolled back in Elasticsearch."""
    logger.warning("v003_down_noop", reason="Field additions cannot be rolled back in Elasticsearch")
