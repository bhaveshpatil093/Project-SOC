"""Add entity risk profile"""
import logging
from app.ingestion.es_client import INDEX_NAMES

logger = logging.getLogger(__name__)

async def up(es):
    baselines_index = INDEX_NAMES.get("baselines", "soc-entity-baselines")
    logger.info(f"Running v003 up: Adding risk_profile_vector to {baselines_index}")
    
    mapping = {
        "properties": {
            "risk_profile_vector": {"type": "dense_vector", "dims": 20}
        }
    }
    await es.indices.put_mapping(index=baselines_index, body=mapping, ignore_unavailable=True)

async def down(es):
    logger.warning("Running v003 down: cannot rollback field additions in ES")
