"""Add score history"""
import logging
from app.ingestion.es_client import INDEX_NAMES

logger = logging.getLogger(__name__)

async def up(es):
    alerts_index = INDEX_NAMES.get("alerts_processed", "soc-processed-alerts")
    logger.info(f"Running v004 up: Adding score_history to {alerts_index}")
    
    mapping = {
        "properties": {
            "score_history": {
                "type": "nested",
                "properties": {
                    "timestamp": {"type": "date"},
                    "threat_score": {"type": "float"}
                }
            }
        }
    }
    await es.indices.put_mapping(index=alerts_index, body=mapping, ignore_unavailable=True)

async def down(es):
    logger.warning("Running v004 down: cannot rollback field additions in ES")
