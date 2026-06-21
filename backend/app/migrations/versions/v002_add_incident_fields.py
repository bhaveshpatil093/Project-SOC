"""Add incident fields"""
import logging
from app.ingestion.es_client import INDEX_NAMES

logger = logging.getLogger(__name__)

async def up(es):
    alerts_index = INDEX_NAMES.get("alerts_processed", "soc-processed-alerts")
    logger.info(f"Running v002 up: Adding occurrence_count, last_seen, fingerprint to {alerts_index}")
    
    mapping = {
        "properties": {
            "occurrence_count": {"type": "integer", "null_value": 1},
            "last_seen": {"type": "date"},
            "fingerprint": {"type": "keyword"}
        }
    }
    await es.indices.put_mapping(index=alerts_index, body=mapping, ignore_unavailable=True)

async def down(es):
    logger.warning("Running v002 down: cannot rollback field additions in ES")
