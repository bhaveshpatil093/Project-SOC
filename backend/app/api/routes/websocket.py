from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
from datetime import datetime
import logging
from app.ingestion.es_client import get_es_client

router = APIRouter()
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)

    async def broadcast(self, message: dict):
        msg_str = json.dumps(message, default=str)
        # Convert to list to avoid modifying during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_text(msg_str)
            except Exception as e:
                logger.error(f"Failed to broadcast to a client: {e}")
                self.disconnect(connection)

    async def send_personal(self, message: dict, ws: WebSocket):
        msg_str = json.dumps(message, default=str)
        try:
            await ws.send_text(msg_str)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(ws)

manager = ConnectionManager()

@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        es = await get_es_client()
        query = {
            "query": {"term": {"status": "open"}},
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": 10
        }
        try:
            res = await es.search(index="soc-processed-alerts", body=query, ignore_unavailable=True)
            hits = res.get("hits", {}).get("hits", [])
            initial_alerts = [{"id": h["_id"], **h["_source"]} for h in hits]
            
            await manager.send_personal({
                "type": "initial_alerts",
                "data": initial_alerts,
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        except Exception as e:
            logger.warning(f"Could not fetch initial alerts for WS: {e}")
            await manager.send_personal({
                "type": "ping",
                "data": {"status": "connected", "message": "Initial fetch failed"},
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        
        while True:
            # Keep connection alive natively
            data = await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
