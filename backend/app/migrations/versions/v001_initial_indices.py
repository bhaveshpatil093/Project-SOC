"""Initial SOC indices creation"""
from app.ingestion.es_client_protocol import supports_index_management
from app.logging_config import get_logger

logger = get_logger(__name__)


async def up(es) -> None:
    """
    v001 up: Initial index creation.
    Skipped when using KibanaProxyClient — Kibana proxy cannot create indices.
    Index creation is handled by the Elasticsearch cluster administrator.
    """
    if not supports_index_management(es):
        logger.info("v001_up_skipped", reason="KibanaProxyClient does not support index management")
        return
    logger.info("v001_up_running", action="Creating initial SOC indices")
    # Native ES client path — indices are created by individual components on demand.
    # This migration serves as a marker that the initial setup has been acknowledged.


async def down(es) -> None:
    """v001 down: Deletes all soc-* indices. Irreversible — use with caution."""
    if not supports_index_management(es):
        logger.warning("v001_down_skipped", reason="KibanaProxyClient does not support index management")
        return
    logger.warning("v001_down_running", action="Deleting all soc-* indices")
    await es.indices.delete(index="soc-*", ignore_unavailable=True)
