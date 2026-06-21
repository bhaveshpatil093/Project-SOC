"""Add temporal baseline"""
import logging
from app.ingestion.es_client import INDEX_NAMES

logger = logging.getLogger(__name__)

async def up(es):
    baselines_index = INDEX_NAMES.get("baselines", "soc-entity-baselines")
    logger.info(f"Running v005 up: Adding active_hours, typical_days to {baselines_index}")
    
    mapping = {
        "properties": {
            "active_hours": {"type": "integer"},
            "typical_days": {"type": "keyword"}
        }
    }
    await es.indices.put_mapping(index=baselines_index, body=mapping, ignore_unavailable=True)

async def down(es):
    logger.warning("Running v005 down: cannot rollback field additions in ES")
