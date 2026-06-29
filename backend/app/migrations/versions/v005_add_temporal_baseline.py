"""Add temporal baseline"""
from app.ingestion.kibana_client import KibanaProxyClient

from app.logging_config import get_logger
logger = get_logger(__name__)

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
