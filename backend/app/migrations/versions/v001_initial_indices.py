"""Initial SOC indices creation"""
import logging
from app.ingestion.es_client import create_soc_indices

logger = logging.getLogger(__name__)

async def up(es):
    logger.info("Running v001 up: Creating initial indices")
    await create_soc_indices(es)

async def down(es):
    logger.warning("Running v001 down: Deleting all soc-* indices")
    await es.indices.delete(index="soc-*", ignore_unavailable=True)
