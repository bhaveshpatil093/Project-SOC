"""Initial SOC indices creation"""
from app.ingestion.kibana_client import KibanaProxyClient

from app.logging_config import get_logger
logger = get_logger(__name__)

async def up(es):
    logger.info("Running v001 up: Creating initial indices")
    await create_soc_indices(es)

async def down(es):
    logger.warning("Running v001 down: Deleting all soc-* indices")
    await es.indices.delete(index="soc-*", ignore_unavailable=True)
